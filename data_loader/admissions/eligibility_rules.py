"""Conservative, source-specific compilation, with explicit manual fallbacks.

Only complete, reviewed grammars below may emit complete=True. Unrecognized
clauses remain visible; scope is never inferred from faculty membership alone.
"""
from copy import deepcopy
import re

SUBJECTS={re.sub(r'\s','',s):s for s in ['математика','информатика','физика','химия','биология','русский язык','литература','история','обществознание','география','иностранный язык']}
SUBJECTS.update({'информатикеиИКТ'.lower():'информатика','информатике':'информатика','физике':'физика','математике':'математика','химии':'химия','биологии':'биология','русскомуязыку':'русский язык'})

# These are the reviewed footnotes, not a list learned from the current import.
# A new or edited footnote must invalidate automatic assessment until reviewed.
REVIEWED_CONDITIONS = {
    'hse': ('Профиль должен входить в перечень в год проведения олимпиады.', 'Для категории лиц, указанной в сноске ** документа, порог подтверждения составляет 65 баллов.'),
    'itmo': ('Ограничения в скобках в профиле олимпиады относятся к области действия этой строки.',),
    'bmstu': ('Степень диплома: winner — победитель (I); prize_winner — призер (II–III). «Не предоставляется» означает отсутствие права.', 'При нескольких предметах выбирается один и подтверждается ЕГЭ по нему (приложение 5, пункт 3).', 'Для категории лиц из пункта 8 приложения 5 порог ЕГЭ — 65 баллов.', 'Обладателям БВИ доступно особое преимущество 100 баллов на остальных направлениях (пункт 7 приложения 5).', 'Названия и номера сопоставляются только внутри одного года перечня; полный текст и исходные ячейки сохранены в источнике.'),
    'mipt': ('Результат олимпиады не ранее 2022 года. Для РСОШ — задания за 11 класс.', 'Победителям «Физтеха» доступны особые права также за 10 класс (пункт 5).', 'Победителям Всероссийской олимпиады по искусственному интеллекту за 10 класс — для программ ВШПИ (пункт 6).', 'Точный порог ЕГЭ/ВИ, степень диплома и конкурсная группа указаны в поле benefit; условия каждой альтернативы применяются совместно.'),
    'mephi': ('Несколько предметов подтверждаются по одному из них по выбору; 100 баллов засчитываются по этому предмету.', 'Разделенные косой чертой наборы направлений и предметов сопоставляются по порядку, не как декартово произведение.', 'Срок — четыре года после года проведения; для участников СВО продлевается на срок участия.', 'Имеющий БВИ может использовать 100 баллов по предмету олимпиады в основном конкурсе.'),
    'msal': ('Для зачисления действуют общие условия особых прав на странице 1; срок — четыре года после года проведения.',),
}

# Explicitly reviewed name/profile families. The legacy PDF extraction contains
# carry-forward names on some continuation rows (e.g. Formula Edinstva + NTO
# space systems). Such pairs must not acquire automatic rights just because the
# remaining cells parse. Extend this list only after reviewing original rows.
REVIEWED_PAIRS = {
    'Всероссийская олимпиада школьников «Высшая проба»': {'математика','физика','информатика','химия','биология','история','право','обществознание','экономика','русский язык','литература','география'},
    'Кутафинская олимпиада школьников по праву': {'право'},
    'Олимпиада школьников «Ломоносов»': {'математика','физика','информатика','химия','биология','история','право','обществознание','русский язык','литература','география'},
    'Олимпиада школьников «Физтех»': {'математика','физика','биология'},
    'Всесибирская открытая олимпиада школьников': {'математика','физика','информатика','химия','биология'},
    'Московская олимпиада школьников': {'математика','физика','информатика','химия','биология','право','история','обществознание'},
    'Объединенная межвузовская математическая олимпиада школьников': {'математика'},
    'Олимпиада школьников Санкт-Петербургского государственного университета': {'математика','физика','информатика','химия','биология','право','история','обществознание'},
    'Инженерная олимпиада школьников': {'физика'},
    'Олимпиада школьников «Надежда энергетики»': {'математика','физика'},
    'Отраслевая физико-математическая олимпиада школьников «Росатом»': {'математика','физика'},
    'Межрегиональная олимпиада по праву «ФЕМИДА»': {'право'},
}


def reviewed_pair(name,profile):
    def normalized(value):return ' '.join(re.sub(r'[^\w]+',' ',value.casefold().replace('ё','е')).split())
    return any(normalized(name)==normalized(n) and normalized(profile) in {normalized(p) for p in profiles}
               for n,profiles in REVIEWED_PAIRS.items())


def subject(s):return SUBJECTS.get(re.sub(r'\s','',s.lower().replace('ё','е')))
def leaf(field,label,**kwargs):return dict(field=field,label=label,**kwargs)
def exam(name,score,manual=False):return leaf('exam','Подтверждение: '+name,subject=name,min=score,manual_on_failure=manual)
def cohort():return [leaf('award_year','Год получения: проверен набор 2026',min=2026,max=2026,manual_on_failure=True),leaf('olympiad_year','Учебный год олимпиады',values=['2025/2026'],manual_on_failure=True)]


def compile_rule(r,c):
    v=r['values'];u=r['university_id'];physical={k:p for k,p in c.programs.items() if p['university_id']==u and p['kind']!='group' and not p.get('aggregate')}
    candidates=sorted(set(r['program_ids']+r['related_program_ids'])&physical.keys())
    if not candidates:candidates=sorted(physical)
    source=deepcopy(c.public_rule(r));source['source'].pop('local_url',None)
    base=dict(admission_year=r['admission_year'],rule_id=r['id'],source_payload=source,scope=v['program_scope'],program_keys=candidates,
              complete=False,manual_reason='Не все условия, исключения или соответствие программе разобраны. Сверьте полную формулировку источника.',requirement={})
    outputs=[]
    for benefit in r['benefit_types']:
        out=dict(base,id=r['id']+':'+benefit,benefit=benefit)
        outputs.append(out)
        if r['admission_year'] != 2026 or tuple(r['conditions']) != REVIEWED_CONDITIONS.get(u):continue
        if r['category']!='rsosh':continue # mixed international/VSOSH scopes require separate review
        if benefit not in ('bvi','100_points'):continue
        profile=v['olympiad_profile']
        if not profile or re.search(r'[()/;]',profile):continue
        if not reviewed_pair(v['olympiad_name'],profile):
            out['manual_reason']='Сочетание названия и профиля требует сверки с оригиналом и перечнем года олимпиады; автоматическая проверка этой пары пока не подтверждена.'
            continue
        common=[leaf('profile','Профиль диплома',values=[profile])]
        if u=='mipt':
            if benefit!='bvi':continue # full-score use also requires entrance-subject correspondence
            branches=[];branch_programs=set();parsed=True
            for clause in v['benefit'].split(';'):
                match=re.fullmatch(r'(.+?)\s+(Победителям(?: и призерам)?) при наличии результата ЕГЭ или ВИ по (.+?) (75|80|85) баллов и выше',clause.strip(),re.I)
                if not match:parsed=False;break
                scope,result,subj,score=match.groups();subj=subject(subj)
                if not subj:parsed=False;break
                if scope.startswith('Все конкурсные группы '):
                    schools=scope.removeprefix('Все конкурсные группы ').split(', ')
                    pkeys=[k for k,p in physical.items() if p.get('school') in schools]
                else:
                    names=re.findall(r'"([^"]+)"',scope)
                    if not names or re.sub(r'"[^"]+"|[\s,]','',scope):parsed=False;break
                    pkeys=[k for k,p in physical.items() if p.get('competition_group') in names]
                if not pkeys:parsed=False;break
                results=['winner','prize_winner'] if 'призер' in result.lower() else ['winner']
                grades=['11']
                if '«Физтех»' in v['olympiad_name'] and results==['winner']:grades.append('10')
                req=dict(all=common+[leaf('award_year','Год диплома: с 2022 по 2026',min=2022,max=2026),
                    leaf('class','Класс выполнения заданий',values=grades,manual_on_failure='искусственному интеллекту' in v['olympiad_name']),leaf('result','Результат диплома',values=results),exam(subj,int(score),True)])
                branch=dict(out,id=out['id']+':'+str(len(branches)),complete=True,manual_reason='',program_keys=sorted(pkeys),scope=scope,requirement=req)
                branches.append(branch);branch_programs.update(pkeys)
            if parsed and branches:
                outputs.remove(out);outputs.extend(branches)
                # Candidates linked only via a school remain manual when the source
                # restricts rights to named competition groups.
                rest=set(candidates)-branch_programs
                if rest:outputs.append(dict(out,program_keys=sorted(rest)))
            continue
        if u not in ('hse','itmo','bmstu','mephi','msal'):continue
        accepted_benefits = {
            'hse': {'Право на прием БВИ','Право на 100 баллов'},
            'itmo': {'БВИ','100 баллов'}, 'bmstu': {'БВИ','100 баллов'},
            'mephi': {'БВИ','100 баллов'},
            'msal': {'Победители и призеры – прием без вступительных испытаний, право на 100 баллов, особое преимущество','Победители и призеры – право на 100 баллов'},
        }
        if v['benefit'] not in accepted_benefits[u]:continue
        if re.search(r'кроме|исключ|/|\bвсе\b',v['program_scope'],re.I):continue
        if not set(r['program_ids']+r['related_program_ids'])&physical.keys():continue
        grades=re.findall(r'\d+',v.get('grades',''))
        if not grades or re.sub(r'\d+|класс|[\s,]','',v.get('grades','')):continue
        diplomas=v.get('diplomas','').lower()
        if u=='bmstu':results=[res for res,key in [('winner','winner'),('prize_winner','prize_winner')] if v.get(key,'').lower()=='предоставляется']
        elif diplomas in ('победителям и призерам','победитель или призер','победители и призеры'):results=['winner','prize_winner']
        elif diplomas in ('победителям','победитель'):results=['winner']
        else:continue
        if not results:continue
        raw=v.get('confirmation_subjects','')
        # Slashes in MEPhI align separate subject/field sets; do not cross join.
        if '/' in raw:continue
        subjects=[subject(s) for s in raw.split(',')]
        if not all(subjects):continue
        score=v.get('confirmation_score','')
        if not re.fullmatch(r'75(?: и более)?',score):continue
        if benefit=='100_points':
            # Explicit full-score subject must be known for this row/program.
            if u not in ('msal','mephi'):continue
            if u=='mephi' and len(subjects)>1:continue
        years=cohort()
        if u=='bmstu':
            season=v.get('olympiad_year','')
            if season not in ('2025/26','2024/25'):continue
            end=2026 if season=='2025/26' else 2025
            years=[leaf('award_year','Год получения диплома',min=end,max=end),leaf('olympiad_year','Учебный год таблицы',values=[f'{end-1}/{end}'])]
        elif u=='msal':years=[leaf('award_year','Четыре года после года олимпиады',min=2022,max=2026)]
        elif u=='mephi':years=[leaf('award_year','Срок действия диплома с возможными исключениями',min=2022,max=2026,manual_on_failure=True)]
        checks=common+years+[leaf('class','Класс выполнения заданий',values=grades),leaf('result','Результат диплома',values=results)]
        checks.append(dict(any=[exam(s,75,u in ('hse','bmstu','msal')) for s in subjects]))
        out.update(complete=True,manual_reason='',requirement=dict(all=checks))
    return outputs


def build(catalog):
    result=[]
    for r in catalog.rules:
        for e in compile_rule(r,catalog):
            special=[k for k in e['program_keys'] if re.search(r'на базе|второе высшее|магистрат',catalog.programs[k]['name'],re.I)] if e['complete'] else []
            if special:
                result.append(dict(e,id=e['id']+':prior-education',program_keys=special,complete=False,
                    manual_reason='У программы есть требования к предыдущему образованию. Сведения о дипломе олимпиады не подтверждают эту область приёма.'))
                e=dict(e,program_keys=[k for k in e['program_keys'] if k not in special])
            if e['program_keys']:result.append(e)
    return result
