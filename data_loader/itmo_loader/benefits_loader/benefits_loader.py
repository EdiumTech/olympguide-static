import pdfplumber
import requests
import pandas as pd
import re
import json
import numpy as np
from clients.get_client import get_full_olympiads, get_programs_by_fields, get_olympiads, get_subjects
from clients.post_client import upload_benefit
from PyPDF2 import PdfReader
from Entities.Benefit import Benefit

def load_benefits():
    url = "https://abit.itmo.ru/file_storage/file/pages/82/rsosh_bvi_2026.pdf"
    pdf_filename = "rsosh_bvi_2026.pdf"
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    with open(pdf_filename, "wb") as f:
        f.write(response.content)
    print("PDF успешно скачан!")

def extract_complex_table(pdf_path, page_number):
    data = []
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_number]

        # Извлечение линий таблицы
        table_lines = page.edges
        rows = page.extract_tables()

        # Если таблицы извлечены как список
        for table in rows:
            for row in table:
                data.append(row)

    return data

def process_fields(table):
    programs = get_programs_by_fields(4)
    cur_fields = []
    for i in range(len(table)):
        text = table[i][0]
        pattern = r'\b\d{2}\.\d{2}\.\d{2}\b'
        matches = re.findall(pattern, text)
        if len(matches) != 0:
            for k in range(i + 1, len(table)):
                if table[k][0] != '':
                    if table[k][1] == '':
                        matches.extend(re.findall(pattern, table[k][0]))
                        table[k][0] = ''
                    break
        else:
            table[i][0] = ','.join(cur_fields)
            continue
        result = []
        for field in matches:
            if field in programs:
                result.append(str(programs[field]))
            else:
                print(f'Нет программы с кодом {field}')
        cur_fields = result
        table[i][0] = ','.join(result)

    return table

def process_diploma_level(table):
    for i in range(len(table)):
        diploma_level = table[i][5]
        if 'или' in diploma_level:
            diploma_level = 3
        else:
            diploma_level = 1
        table[i][5] = diploma_level
    return table

def process_subject(table):
    subjects = get_subjects()
    for i in range(len(table)):
        subject = (table[i][3].
                   replace(' ие', 'ие').
                   replace(' ию', 'ие'))
        subject_id = subjects[subject]
        table[i][3] = subject_id

    return table

def process_level(table):
    for i in range(len(table)):
        level = table[i][4]
        matches = re.findall(r'\b[1-9]\d*\b', level)
        table[i][4] = ','.join(matches)
    return table

def process_olympiads_names(table):
    extensions = {
        'гранит науки': 'олимпиада школьников «гранит науки»',
        'объединенная межвузовская математическая олимпиада школьников': 'объединенная межвузовская олимпиада школьников',
        'межрегиональная олимпиада школьников «архитектура и искусство» по комплексу предметов (рисунок, композиция)': 'xvii южно-российская межрегиональная олимпиада школьников «архитектура и искусство» по комплексу предметов (рисунок, живопись, композиция, черчение)'
    }
    olympiads = get_olympiads()
    full_olympiads = get_full_olympiads()
    current_olymp_name = ''
    programs = get_programs_by_fields(4)
    i = 0
    while i < len(table):
        olymp_name = (table[i][1].lower().replace('ё', 'е').
                replace(' / ', '/').
                replace(' - ', ' -  ').
                replace('- ', '-').
                replace('им.', 'имени'))
        if olymp_name in extensions:
            olymp_name = extensions[olymp_name]
        if olymp_name != '':
            current_olymp_name = olymp_name
        else:
            table[i][1] = current_olymp_name
            olymp_name = current_olymp_name

        if olymp_name in olympiads:
            profile = (table[i][2].lower().
                       replace(' е', 'е').
                       replace('программирование', 'информатика').
                       replace('информатика/информатика', 'информатика')
                       )
            if profile not in olympiads[olymp_name]:
                print(f'{olymp_name} + {profile}')
                table = np.delete(table, i, axis=0)
            else:
                olymp_id = olympiads[olymp_name][profile]
                table[i][1] = olymp_id
                i += 1

        elif olymp_name == 'все из перечня олимпиад школьников':
            cur_olympiads = []
            profile = table[i][2].lower().replace(' е', 'е')
            pattern = r'\b\d{2}\.\d{2}\.\d{2}\b'
            only_ind = []
            only = re.findall(pattern, profile)
            if only:
                for field in only:
                    if field in programs:
                        only_ind.append(programs[field])
                print(only_ind)
                profile = re.sub(r'\s*\((только|учитывается только)[^)]*\)', '', profile)
            for olympiad, profiles in olympiads.items():
                if profile in profiles:
                    if full_olympiads[olympiad][profile] in table[i][4]:
                        cur_olympiads.append(profiles[profile])
            if only_ind:
                table[i][0] = table[i][1] = ','.join(str(x) for x in only_ind)
            table[i][1] = ','.join(str(x) for x in cur_olympiads)
            if len(cur_olympiads) == 0:
                print(f'{olymp_name} + {profile}')
                table = np.delete(table, i, axis=0)
                continue
            i += 1
        else:
            table = np.delete(table, i, axis=0)
    return table

def main():
    current_educations = []
    pdf_path = "rsosh_bvi_2026.pdf"

    reader = PdfReader(pdf_path)
    numbers_of_pages = len(reader.pages)
    all_dataframes = []

    columns = ['Направление подготовки', 'Название олипиады', 'Профиль олимпиады',
               'Предмет подтверждающий результаты (не менее 75 баллов)',
               'Уровень олимпиады','Дипломы']

    for page_number in range(numbers_of_pages):
        raw_data = extract_complex_table(pdf_path, page_number)

        if page_number == 0:
            raw_data.pop(0)

        df = pd.DataFrame(raw_data, columns=columns)
        all_dataframes.append(df)

    combined_df = pd.concat(all_dataframes, ignore_index=True)
    combined_df = combined_df.fillna('').astype(str)
    combined_df = combined_df.applymap(lambda x: x.replace('\n', ' '))
    data = np.array(combined_df, dtype=str)
    data = process_fields(data)
    data = process_diploma_level(data)
    data = process_subject(data)
    data = process_level(data)

    data = process_olympiads_names(data)

    result = []
    count = 0
    for row in data:
        programs = row[0].split(',')
        olympiads = row[1].split(',')
        for program in programs:
            for olympiad in olympiads:
                subject = {
                    'subject_id': int(row[3]),
                    'score': 75
                }
                benefit = Benefit(
                    olympiad_id=int(olympiad),
                    program_id=int(program),
                    is_bvi=True,
                    min_diploma_level=int(row[5]),
                    min_class=10,
                    confirmation_subjects=[subject],
                    full_score_subjects=[int(row[3])])
                upload_benefit(benefit)
                print(benefit)
                count += 1
                print(count)

    print(count)


if __name__ == "__main__":
    main()
