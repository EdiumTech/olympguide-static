"""Reviewed calendar entries. Identity excludes dates and revision timestamps."""
import hashlib
import json
from datetime import date, datetime
from zoneinfo import ZoneInfo


def validate_event(e):
    if e['kind'] not in ('registration_open','registration_close','qualifying','final','results','appeal','documents_open','documents_close','admission','custom'):
        raise ValueError('Unknown calendar kind')
    zone=ZoneInfo(e['timezone'])
    kind=e['time_kind']
    fields={k for k in ('start_date','end_date','starts_at','ends_at') if e.get(k)}
    if kind=='undated':
        if fields:raise ValueError('Undated events cannot have placeholder dates')
    elif kind in ('all_day','date_range'):
        expected={'start_date','end_date'} if kind=='date_range' else {'start_date'}
        if fields!=expected:raise ValueError('Date precision mismatch')
        start=date.fromisoformat(e['start_date'])
        if kind=='date_range' and date.fromisoformat(e['end_date'])<start:raise ValueError('Reversed date range')
    elif kind=='timed':
        if fields not in ({'starts_at'},{'starts_at','ends_at'}):raise ValueError('Time precision mismatch')
        times=[datetime.fromisoformat(e[k]) for k in ('starts_at','ends_at') if e.get(k)]
        if any(t.utcoffset() is None or t.astimezone(zone).utcoffset()!=t.utcoffset() for t in times):raise ValueError('Timezone offset mismatch')
        if len(times)==2 and times[1]<=times[0]:raise ValueError('Reversed timed range')
    else:raise ValueError('Unknown calendar time kind')
    if not e['source_url'].startswith('https://') or not e['checked_on']:raise ValueError('Missing calendar source')


def build(sources,catalog):
    from catalog import normalized, identity
    name='Всероссийская олимпиада школьников «Высшая проба»'
    rules=[r for r in catalog.rules if normalized(r['values']['olympiad_name'])==normalized(name)]
    # The source explicitly excludes these profiles from the common schedule.
    profiles=[r for r in rules if normalized(r['values']['olympiad_profile']) not in ('анализ данных','промышленное программирование')]
    keys=sorted({identity(r['category'],normalized(r['values']['olympiad_name']),normalized(r['values']['olympiad_profile'])) for r in profiles})
    web_ids=sorted({r['olympiad_id'] for r in profiles})
    common=dict(collection_key='hse-vp-2026-2027',season='2026/2027',admission_year=None,timezone='Europe/Moscow',
        source_url=sources['hse-calendar']['url'],checked_on='2026-09-08',olympiad_keys=keys,web_olympiad_ids=web_ids,
        program_keys=[],description='Общий график «Высшей пробы». Анализ данных и промышленное программирование имеют отдельные графики. Даты по профилям уточняются; правила приёма 2027 здесь не подтверждаются.')
    specs=[
        ('registration-open','Начало регистрации','registration_open','all_day',dict(start_date='2026-08-20')),
        ('registration-close','Окончание регистрации','registration_close','timed',dict(starts_at='2026-09-21T14:00:00+03:00')),
        ('qualifying-1','Первый тур отборочного этапа','qualifying','date_range',dict(start_date='2026-09-25',end_date='2026-10-11')),
        ('qualifying-2','Второй тур отборочного этапа','qualifying','date_range',dict(start_date='2026-11-13',end_date='2026-11-22')),
        ('final','Заключительный этап','final','date_range',dict(start_date='2027-02-05',end_date='2027-02-15')),
        ('results','Публикация результатов · срок не подтверждён','results','undated',{}),
        ('appeal','Апелляции · срок не подтверждён','appeal','undated',{}),
    ]
    rows=[dict(common,id='hse-vp-2026-2027-'+key,title='Высшая проба · '+title,kind=kind,time_kind=precision,**dates)
          for key,title,kind,precision,dates in specs]
    rows.append(dict(collection_key='itmo-admission-2026',id='itmo-admission-2026-documents-close',title='ИТМО · окончание подачи документов на бюджет',
        kind='documents_close',season='',admission_year=2026,time_kind='all_day',start_date='2026-07-25',
        timezone='Europe/Moscow',university_key='itmo',program_keys=[],olympiad_keys=[],web_olympiad_ids=[],
        source_url=sources['itmo-family']['url'],checked_on='2026-09-08',
        description='Дата окончания подачи документов в бакалавриат на бюджет из официальной публикации ИТМО. Точное время в этой публикации не указано. Кампания 2026.'))
    for e in rows:
        validate_event(e)
        # checked_on changes alone should not invalidate personal acknowledgements.
        e['revision']=hashlib.sha256(json.dumps({k:v for k,v in e.items() if k!='checked_on'},ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    return rows
