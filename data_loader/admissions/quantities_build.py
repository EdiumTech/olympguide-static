"""Rebuild the 2026 tuition/places supplement from saved official sources.

Counts describe intake plans (including quotas), never remaining vacancies.
Shared competition groups retain a stable identity and must not be summed per profile.
"""
import hashlib
import json
from pathlib import Path
import re
import sys

import json5

from .quantities import ROOT, clean, page, read
from .mipt_programs import expand

CODE = r"\d{2}\.\d{2}\.\d{2}"
# Manual interpretations are valid only for these reviewed document revisions.
REVIEWED = {'msal_cost': 'b6173a2c251c34e7dce157a750fc0f3fd11a276705e9b3232463b235dcdb9501', 'msal_places': '7eaee2601ae8daa02ee908a8e4b2219fc92394e34743f056fb8937bb63c35abe', 'mipt_cost': '9112ecde6690c503dfc439aa993ff0e597c3e88d13d7bc4dae7381888a603e67', 'hse_compsocsci': '429581814eb67ef22838dcc1948f8455e5254e78003668cf19a5164e14b08e32', 'mephi_order_jun': '6814bd1630d70af6dc2e8fe91d84af2357057ff484b94234037a45887e263757', 'mephi_order_jul': '09b4b0c70625a60404fd6817ac104492469ed52159cad18d6305a8c931fb6493', 'mephi_order_aug': 'b20ad200c7335972cce3c65a6961acf3541771c16f1da268c924fad781a074d2'}



def number(value):
    if value is None or clean(value) in ("", "—", "–", "-"):
        return None
    text = clean(value).replace(" ", "").removesuffix(",00")
    if not re.fullmatch(r"\d+", text):
        raise ValueError(f"Not an integer: {value!r}")
    return int(text)


def tables(key):
    result = []
    for table in page(key).xpath("//table"):
        rows = [[dict(text=clean(c), rowspan=int(c.get("rowspan", 1)),
                      colspan=int(c.get("colspan", 1))) for c in row.xpath("./th|./td")]
                for row in table.xpath(".//tr")]
        result.append(expand(rows))
    return result


def next_data(key):
    scripts = page(key).xpath('//script[@id="__NEXT_DATA__"]/text()')
    return json.loads(scripts[0]) if scripts else None


def visible(key):
    document = page(key)
    for node in document.xpath("//script|//style"):
        node.getparent().remove(node)
    return clean(document)


def identity(*values):
    return hashlib.sha256("|".join(values).encode()).hexdigest()[:20]


class Builder:
    def __init__(self, catalog):
        self.catalog = catalog
        self.programs = {p['id']: p for p in catalog.programs.values()
                         if p['kind'] != 'group' and not p.get('aggregate')}
        self.result = {p['id']: dict(id=p['id'], university_id=p['university_id'],
                                    field_id=p['field_id'], name=p['name'],
                                    admission_year=2026, study_form='очная',
                                    budget_places=None, paid_places=None, cost=None,
                                    cost_period=None, quantity_evidence={}, quantity_notes=[])
                       for p in self.programs.values()}

    def selected(self, university):
        return [p for p in self.programs.values() if p['university_id'] == university]

    def put(self, p, metric, value, source, locator, *, scope='program', group=None,
            group_name=None, note=None, period=None, **extra):
        if value is None:
            return
        if type(value) is not int or value < 0 or (metric == 'cost' and value == 0):
            raise ValueError(f'Invalid {metric}: {value}')
        q = self.result[p['id']]
        if q[metric] is not None and q[metric] != value:
            raise ValueError(f'Conflicting values for {p["name"]}: {metric}')
        q[metric] = value
        q['quantity_evidence'][metric] = dict(value=value, source_id=source, locator=locator,
            scope=scope, group_id=group, group_name=group_name, note=note, **extra)
        if metric == 'cost':
            assert period in ('year', 'semester')
            q['cost_period'] = period
            q['quantity_evidence'][metric].update(period=period, currency='RUB')

    def hse(self):
        script = page('hse_programs').xpath('//script[contains(text(),"window.__INITIAL_STATE__ =")]/text()')[0]
        items = json5.loads(script.split('=', 1)[1].split(';window.__URQL_DATA__', 1)[0])['bachelorPrograms']['items']
        for p in self.selected('hse'):
            if p['name'] == 'Экономика и анализ данных':
                text = visible('hse_eda').split('Количество мест в 2026 году', 1)[1].split('Другие бакалаврские программы', 1)[0]
                for metric, pattern in [('budget_places', r'(\d+) бюджетных мест'), ('paid_places', r'(\d+) платных мест')]:
                    self.put(p, metric, int(re.search(pattern, text)[1]), 'hse_eda', 'Количество мест в 2026 году',
                             scope='admission_group', group='hse-eda', group_name='Экономика и анализ данных, 38.03.01 / 01.03.02')
                cost = re.search(r'([\d ]+) руб\. в год', text)[1]
                self.put(p, 'cost', number(cost), 'hse_eda', 'Стоимость обучения на платных местах в 2026 году', period='year')
                continue
            if p['name'] == 'Вычислительные социальные науки':
                text = visible('hse_compsocsci')
                assert 'первые 30 мест из рейтинга студентов с бюджетными местами и первые 10 мест' in text
                for metric, value in [('budget_places', 30), ('paid_places', 10)]:
                    self.put(p, metric, value, 'hse_compsocsci', 'Внутренний конкурс после зачисления на родовую программу',
                             scope='internal_selection', group='hse-compsocsci', group_name='Вычислительные социальные науки',
                             note='Это внутренний отбор после зачисления на базовую программу, не отдельный набор абитуриентов.')
                self.result[p['id']]['quantity_notes'].append('Внутренний отбор после поступления: 30 бюджетных и 10 платных мест на все направления вместе. Стоимость и скидка зависят от базовой программы.')
                continue
            matches = [x for x in items if x['url'].rstrip('/') == p['program_url'].rstrip('/')
                       and x['direction']['directionNumber'] == p['field_id']]
            assert len(matches) == 1, (p['name'], len(matches))
            x = matches[0]
            locator = f'bachelorPrograms.items id={x["id"]}; direction={p["field_id"]}'
            # The directory uses zero defaults for programs with no published intake.
            if not x.get('cost') and not x.get('budjetPositions') and not x.get('paidPositions'):
                self.result[p['id']]['quantity_notes'].append('В каталоге ВШЭ не опубликованы стоимость и план набора этой программы на 2026 год.')
                continue
            for metric, field in [('budget_places', 'budjetPositions'), ('paid_places', 'paidPositions')]:
                self.put(p, metric, number(x.get(field)), 'hse_programs', locator,
                         group='hse-' + str(x['id']), note=x.get('positionsComment') or None)
            assert x.get('currencyLabel') == 'руб.' and x.get('costPeriodLabel') == 'в год'
            self.put(p, 'cost', number(x.get('cost')), 'hse_programs', locator, period='year')
            self.result[p['id']]['study_form'] = x['learningFormLabel'].lower()

    def bmstu(self):
        costs = {}
        for row in tables('bmstu_cost')[0]:
            for code in re.findall(CODE, row[0]):
                costs[code] = number(row[-1])
        for p in self.selected('bmstu'):
            key = 'bmstu_' + p['field_id'].replace('.', '')
            x = next_data(key)['props']['initialState']['bachelorMajorsDetails']['data']
            codes = re.findall(CODE, x['additional']['code'])
            assert p['field_id'] in codes
            loc = 'bachelorMajorsDetails.data; code=' + p['field_id']
            for row in x['places']:
                metric = {'Бюджетных': 'budget_places', 'Платных': 'paid_places'}[row['title']]
                self.put(p, metric, number(row['count']), key, loc, scope='field',
                         group='bmstu-' + '+'.join(codes), group_name=x['additional']['code'] + ' ' + x['additional']['name'])
            self.put(p, 'cost', costs.get(p['field_id']), 'bmstu_cost', 'table=1; code=' + p['field_id'],
                     period='year', scope='field')

    def mipt(self):
        grid = tables('mipt_places')[0]
        for p in self.selected('mipt'):
            rows = [grid[i - 1] for i in p['source_rows']]
            assert all(row[:3] == [p['school'], p['name'], p['competition_group']] for row in rows)
            assert len({(r[3], r[9]) for r in rows}) == 1
            loc = 'table=1; rows=' + ','.join(map(str, p['source_rows']))
            group = identity('mipt', p['field_id'], p['school'], p['competition_group'])
            title = p['school'] + ': ' + p['competition_group']
            for metric, column in [('budget_places', 3), ('paid_places', 9)]:
                value = number(rows[0][column])
                # A dash in this exhaustive intake table denotes no seats.
                if rows[0][column] == '-': value = 0
                self.put(p, metric, value, 'mipt_places', loc, scope='admission_group',
                         group=group, group_name=title)
            if 'for foreign citizens' in p['competition_group']:
                price = 1083000
                language = 'Образовательные программы на иностранных языках'
            elif p['school'] == 'ВШПИ':
                price, language = 1187000, 'ВШПИ, все направления'
            elif p['school'] == 'ФБВТ':
                price, language = 2000000, 'ФБВТ, все направления'
            elif p['field_id'] in ('14.03.02', '16.03.01'):
                price, language = 1181000, 'На русском языке, ' + p['field_id']
            else:
                price, language = 1014000, 'На русском языке, ' + p['field_id']
            # Guard the manually interpreted rowspan/school tariff against source drift.
            assert f'{price:,}'.replace(',', ' ') + ',00' in clean(page('mipt_cost'))
            self.put(p, 'cost', price, 'mipt_cost', 'table=1; ' + language, period='year')

    def itmo(self):
        for p in self.selected('itmo'):
            key = 'itmo_' + p['program_url'].rstrip('/').rsplit('/', 1)[-1]
            state = next_data(key)
            if state:
                x = state['props']['pageProps']['apiProgram']
                ds = [d for d in x['directions'] if d['code'] == p['field_id']]
                assert len(ds) == 1
                d = ds[0]
                assert d['competitive_group']['year'] == 2026
                for metric, field in [('budget_places', 'budget'), ('paid_places', 'contract')]:
                    self.put(p, metric, d['admission_quotas'][field], key,
                             'apiProgram.directions code=' + p['field_id'] + '.admission_quotas.' + field,
                             scope='admission_group', group='itmo-' + str(d['competitive_group']['id']),
                             group_name=d['competitive_group']['title'])
                cost = x['educationCost']
                assert cost['year'] == 2026
                self.put(p, 'cost', cost['russian'], key, 'apiProgram.educationCost.russian; year=2026', period='year')
            else:
                # The three FITiP pages are Tilda documents, with explicit program allocations.
                text = visible(key)
                match = re.search(r'Направления подготовки бюджетных ' + re.escape(p['field_id']) +
                                  r'.*? (\d+) (\d+) (\d+) (\d+) (\d+) контрактных', text)
                assert match, key
                for metric, i in [('budget_places', 1), ('paid_places', 2)]:
                    self.put(p, metric, int(match[i]), key, 'Направления подготовки; ' + p['field_id'],
                             group=key, note='Распределение мест программы внутри конкурсной группы ФИТиП.')
                prices = re.findall(r'(?<!\d)(\d{3} \d{3}) ₽', text.split('Направления подготовки', 1)[0])
                if key == 'itmo_ai':
                    self.result[p['id']]['quantity_notes'].append('AI360: платный набор отсутствует; стоимость обучения не устанавливается.')
                elif prices:
                    self.put(p, 'cost', number(prices[0]), key, 'Стоимость контрактного обучения (год), граждане РФ', period='year')
                else:
                    raise ValueError('No tuition price in the program header: ' + key)

    def mai(self):
        budget, paid, costs = {}, {}, {}
        for row in tables('mai_budget')[0]:
            codes = re.findall(CODE, row[1])
            for code in codes:
                budget[code] = (number(row[2]), codes, row[0])
        for index in (0, 1):
            for row in tables('mai_paid')[index]:
                codes = re.findall(CODE, row[1])
                for code in codes:
                    paid[code] = (number(row[2]), codes, row[0])
        for row in tables('mai_cost')[0]:
            if re.fullmatch(CODE, row[0]) and row[-2].lower() == 'очная':
                # First price is the standard tariff, followed by a conditional EGE discount.
                price = number(re.match(r'^\d{3} \d{3}', row[-1])[0])
                assert row[0] not in costs or costs[row[0]] == price
                costs[row[0]] = price
        for p in self.selected('mai'):
            for metric, mapping, source in [('budget_places', budget, 'mai_budget'), ('paid_places', paid, 'mai_paid')]:
                if p['field_id'] in mapping:
                    value, codes, title = mapping[p['field_id']]
                    self.put(p, metric, value, source, 'Москва; очная форма; ' + ', '.join(codes),
                             scope='admission_group', group='mai-' + source + '-' + '+'.join(codes), group_name=title)
            if p['field_id'] not in budget:
                key = 'mai_program_' + p['id']
                section = visible(key).split('Основа обучения', 1)[1].split('О программе', 1)[0]
                assert 'Платная' in section and 'Бюджетная' not in section
                self.put(p, 'budget_places', 0, key, 'Основа обучения: только платная; отсутствует в полном бюджетном плане Москвы',
                         scope='field', group='mai-budget-' + p['field_id'], group_name=p['field_id'])
            self.put(p, 'cost', costs.get(p['field_id']), 'mai_cost', 'Москва; 1 курс; очная; ' + p['field_id'],
                     period='year', scope='field')

    def mephi(self):
        # Retain origins of merged intake cells: identical values alone do not imply a shared group.
        source_table = page('mephi_moscow').xpath('//table')[0]
        origin, remaining = None, 0
        budget = {}
        for i, row in enumerate(source_table.xpath('.//tr'), 1):
            cells = row.xpath('./td|./th')
            codes = re.findall(CODE, ' '.join(clean(c) for c in cells))
            codes = [c for c in codes if c[3:5] in ('03', '05')]
            if not codes:
                remaining = max(0, remaining - 1)
                continue
            if remaining == 0:
                value = number(clean(cells[-1]))
                origin, remaining = (i, value), int(cells[-1].get('rowspan', 1))
            for code in codes: budget[code] = origin
            remaining -= 1
        paid = {}
        for i, row in enumerate(tables('mephi_moscow')[1], 1):
            codes = re.findall(CODE, row[0])
            for code in codes:
                paid[code] = (number(row[1]), codes, i)
        costs = json5.loads(re.search(r'const moscowData\s*=\s*(\[.*?\]);', read('mephi_paid'), re.S)[1])
        tariff = {}
        institute = ''
        for i, row in enumerate(costs):
            if row.get('group'): institute = row['group']
            if row.get('code'): tariff.setdefault(row['code'], []).append((number(row['cost']), institute, i))
        for p in self.selected('mephi'):
            # These directory entries refer to a branch or merge two campuses.
            if 'Обнинск' in p['name'] or 'Campus Obninsk' in p['name']:
                self.result[p['id']]['quantity_notes'].append('Программа относится к Обнинску или объединяет кампусы; московский тариф и набор к ней не применяются.')
                continue
            code = p['field_id']
            if code in budget:
                row, value = budget[code]
                group_codes = sorted(c for c, v in budget.items() if v[0] == row)
                self.put(p, 'budget_places', value, 'mephi_moscow', f'table=1; row={row}; Оч',
                         scope='admission_group', group='mephi-budget-' + '+'.join(group_codes),
                         group_name=', '.join(group_codes))
            if code in paid:
                value, codes, row = paid[code]
                self.put(p, 'paid_places', value, 'mephi_moscow', f'table=2; row={row}',
                         scope='admission_group', group='mephi-paid-' + '+'.join(codes), group_name=', '.join(codes))
            candidates = tariff.get(code, [])
            if code == '10.03.01':
                is_finance = any('финансовых технологий' in self.catalog.units[u]['name'] for u in p['unit_ids'])
                candidates = [t for t in candidates if ('финансовых технологий' in t[1]) == is_finance]
            if candidates and len({t[0] for t in candidates}) == 1:
                self.put(p, 'cost', candidates[0][0], 'mephi_paid',
                         'moscowData rows=' + ','.join(str(t[2]) for t in candidates) + '; ' + code,
                         period='semester', scope='field', note='Осенний семестр 2026/2027; годовой тариф не вычисляется.')
            elif code in ('38.03.01', '38.03.02', '38.03.05'):
                # These first-year tariffs are present in the signed order but omitted from the HTML summary.
                self.put(p, 'cost', 245000, 'mephi_order_jun',
                         'Приложение 1; страницы 7, 9; ' + code, period='semester', scope='field',
                         note='Первый курс, осенний семестр 2026/2027. Изменения июля относятся к Ташкенту, августа — к старшим курсам.')

    def msal(self):
        # Visually verified pages 1-3 (places), 2 and 5 (tuition), Moscow only.
        # Superscript footnotes 2, 8, 10, 11 are not part of the number of target places.
        for p in self.selected('msal'):
            code, name = p['field_id'], p['name']
            group, title, row = 'main-law', 'Частное / публичное / международное / бизнес-право / правовой консалтинг', 'page=1; row=1.1.1'
            components, paid = [305, 57, 85, 92], 919
            price = {'Международное право': 560000, 'Публичное право': 600000,
                     'Частное право': 560000, 'Бизнес-юрист': 500000, 'Правовой консалтинг': 500000}.get(name)
            if 'на базе высшего образования' in name:
                group, title, row = 'second-degree', 'Частное / публичное право, заочная форма', 'page=1; row=1.1.2'
                components, paid, price = [0, 0, 0, 0], 87, 350000
                self.result[p['id']]['study_form'] = 'заочная'
                self.result[p['id']]['quantity_notes'].append('На базе высшего образования. Для очно-заочной формы опубликован отдельный тариф 400 000 ₽/год.')
            elif name == 'Инновационная юриспруденция':
                group, title, row = 'innovative-law', name, 'page=1; row=1.1.3'
                components, paid, price = [30, 4, 0, 4], 30, 700000
            elif name.startswith('International Business Law'):
                group, title, row = 'ibl', name, 'page=1; row=1.1.4'
                components, paid, price = [0, 0, 0, 0], 15, 700000
            elif code == '40.05.01':
                group, title, row = code, name, 'page=2; row=1.1'
                components, paid, price = [52, 9, 10, 10], 170, 580000
            elif code == '40.05.03':
                group, title, row = code, 'Речеведческие / экономические экспертизы', 'page=2; row=2'
                components, paid, price = [3, 2, 5, 2], 43, 400000
            elif code == '40.05.04':
                group, title, row = code, name, 'page=3; row=3.1'
                components, paid, price = [0, 18, 139, 18], 159, 580000
            assert price is not None, name
            kwargs = dict(scope='admission_group', group='msal-' + group, group_name=title)
            self.put(p, 'budget_places', sum(components), 'msal_places', row, **kwargs,
                     breakdown=dict(zip(('general', 'special', 'target', 'separate'), components)))
            self.put(p, 'paid_places', paid, 'msal_places', row, **kwargs,
                     note='Включая иностранных граждан и поступающих на второе высшее образование, примечание к таблице.')
            self.put(p, 'cost', price, 'msal_cost', ('page=2' if code == '40.03.01' else 'page=5') + '; ' + name,
                     period='year', note='Стоимость первого курса, приказ №108 от 08.04.2026.')

    def build(self):
        for key, digest in REVIEWED.items():
            meta = json.loads((ROOT / "sources" / (key + ".meta.json")).read_text(encoding="utf-8"))
            if hashlib.sha256((ROOT / meta["file"]).read_bytes()).hexdigest() != digest:
                raise ValueError("Source changed; review manual interpretation: " + key)
        for university in ('hse', 'bmstu', 'mipt', 'itmo', 'mai', 'mephi', 'msal'):
            getattr(self, university)()
        source_ids = {e['source_id'] for q in self.result.values() for e in q['quantity_evidence'].values()}
        sources = [json.loads((ROOT/'sources'/(s+'.meta.json')).read_text(encoding='utf-8')) for s in sorted(source_ids)]
        by_source = {s['id']: s for s in sources}
        for q in self.result.values():
            for metric, evidence in q['quantity_evidence'].items():
                evidence['source_url'] = by_source[evidence['source_id']]['url']
                if metric != 'cost': evidence['includes_quotas'] = metric == 'budget_places'
            q['places_known'] = q['budget_places'] is not None or q['paid_places'] is not None
            q['cost_known'] = q['cost'] is not None
            shared = [e for k,e in q['quantity_evidence'].items() if k != 'cost' and e['scope'] in ('field', 'admission_group', 'internal_selection')]
            groups = list(dict.fromkeys(e['group_name'] for e in shared if e['group_name']))
            q['places_note'] = 'Места на общий набор: ' + '; '.join(groups) + '. Числа не суммируются по профилям.' if groups else None
            if q['university_id'] == 'mephi' and q['paid_places'] is None and q['budget_places'] is not None:
                q['quantity_notes'].append('Число платных мест для этого направления отсутствует в опубликованной таблице приёма МИФИ на 2026 год; старые значения со страниц программ не используются.')
            if any(q[k] is None for k in ('budget_places', 'paid_places', 'cost')) and not q['quantity_notes']:
                q['quantity_notes'].append('Для части показателей нет подтверждённого значения в плане приёма 2026 года; отсутствие не заменено нулём.')
        coverage = {}
        for university in ('hse', 'itmo', 'bmstu', 'mipt', 'mephi', 'mai', 'msal'):
            records = [q for q in self.result.values() if q['university_id'] == university]
            coverage[university] = dict(programs=len(records), **{k: sum(q[k] is not None for q in records)
                for k in ('budget_places', 'paid_places', 'cost')})
        result = dict(schema_version=1, admission_year=2026, sources=sources,
                      programs=sorted(self.result.values(), key=lambda x: x['id']), coverage=coverage)
        (ROOT/'catalog.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        return result


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'web'))
    from catalog import Catalog
    data = Builder(Catalog(quantities=False)).build()
    print(json.dumps(data['coverage'], ensure_ascii=False, indent=2))
