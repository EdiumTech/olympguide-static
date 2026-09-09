import copy
import unittest
from data_loader.admissions.eligibility_rules import compile_rule, REVIEWED_CONDITIONS
from data_loader.admissions.calendar_events import validate_event
from data_loader.admissions.personal import export_sql


class FixtureCatalog:
    programs={
        'a':dict(university_id='mipt',kind='program',school='ФПМИ',competition_group='Математика и информатика'),
        'b':dict(university_id='mipt',kind='program',school='ФПМИ',competition_group='Инженерия'),
    }
    def public_rule(self,r):return dict(r,source={'url':'https://pk.mipt.ru/bachelor/2026_olympiads/'})


def fixture():
    return dict(id='rule',admission_year=2026,university_id='mipt',category='rsosh',benefit_types=['bvi'],
        program_ids=[],related_program_ids=['a','b'],conditions=list(REVIEWED_CONDITIONS['mipt']),values=dict(
            olympiad_name='Всероссийская олимпиада школьников «Высшая проба»',olympiad_profile='математика',program_scope='ФПМИ',
            benefit='"Математика и информатика" Победителям при наличии результата ЕГЭ или ВИ по математике 80 баллов и выше; "Инженерия" Победителям и призерам при наличии результата ЕГЭ или ВИ по математике 85 баллов и выше'))


class CompilationTest(unittest.TestCase):
    def test_joint_alternatives_and_explicit_groups(self):
        rows=compile_rule(fixture(),FixtureCatalog());self.assertEqual(len(rows),2)
        a,b=rows
        self.assertEqual(a['program_keys'],['a']);self.assertEqual(b['program_keys'],['b'])
        self.assertEqual(a['requirement']['all'][-1]['min'],80)
        self.assertEqual(b['requirement']['all'][-1]['min'],85)
        self.assertEqual(a['requirement']['all'][-2]['values'],['winner'])
        self.assertEqual(b['requirement']['all'][-2]['values'],['winner','prize_winner'])

    def test_unparsed_new_condition_cannot_pass_or_refuse(self):
        for change in ('footnote','benefit','year','profile'):
            r=fixture()
            if change=='footnote':r['conditions'].append('Требуется дополнительное испытание')
            if change=='benefit':r['values']['benefit']+=' при дополнительных условиях'
            if change=='year':r['admission_year']=2027
            if change=='profile':r['values']['olympiad_profile']='математика (кроме отдельных треков)'
            self.assertTrue(all(not x['complete'] for x in compile_rule(r,FixtureCatalog())),change)

    def test_faculty_membership_alone_is_manual(self):
        r=fixture();r['values']['benefit']=r['values']['benefit'].split(';')[0]
        rows=compile_rule(r,FixtureCatalog())
        self.assertEqual([(x['program_keys'],x['complete']) for x in rows],[(['a'],True),(['b'],False)])

    def test_grade_and_full_score_are_separate(self):
        c=FixtureCatalog();c.programs={'law':dict(university_id='msal',kind='program')}
        r=fixture();r.update(university_id='msal',conditions=list(REVIEWED_CONDITIONS['msal']),program_ids=['law'],related_program_ids=[],benefit_types=['100_points'])
        r['values'].update(olympiad_profile='право',program_scope='40.03.01',grades='10',diplomas='Победители и призеры',confirmation_subjects='обществознание',confirmation_score='75',benefit='Победители и призеры – право на 100 баллов')
        rule=compile_rule(r,c)[0];self.assertTrue(rule['complete']);self.assertEqual(rule['benefit'],'100_points')
        self.assertEqual(next(x for x in rule['requirement']['all'] if x.get('field')=='class')['values'],['10'])

    def test_empty_collection_withdraws_all_without_deleting_plans(self):
        sql=export_sql(dict(schema_version=1,admission_year=2026,scholarships=[],events=[],evaluations=[],event_collections=['season']))
        self.assertIn("WHERE collection_key='season';",sql)
        self.assertNotIn('NOT IN (NULL)',sql)
        self.assertNotIn('DELETE FROM olympguide.calendar',sql)
        self.assertIn('DELETE FROM olympguide.admission_evaluation',sql)

    def test_unreviewed_name_profile_pair_is_manual(self):
        r=fixture();r['values'].update(olympiad_name='«Формула Единства» / «Третье тысячелетие»',olympiad_profile='космические системы')
        self.assertTrue(all(not e['complete'] for e in compile_rule(r,FixtureCatalog())))

    def test_previous_education_is_not_inferred_from_a_diploma(self):
        from data_loader.admissions.eligibility_rules import build
        c=FixtureCatalog();c.rules=[fixture()];c.programs=copy.deepcopy(c.programs)
        c.programs['a']['name']='Математика на базе высшего образования';c.programs['b']['name']='Инженерия'
        result=build(c)
        self.assertTrue(all(not e['complete'] for e in result if 'a' in e['program_keys']))
        self.assertTrue(any(e['complete'] for e in result if 'b' in e['program_keys']))


class CalendarValidationTest(unittest.TestCase):
    def event(self):return dict(kind='final',time_kind='timed',timezone='Europe/Berlin',starts_at='2026-03-29T03:30:00+02:00',source_url='https://official.example/',checked_on='2026-09-08')
    def test_offset_and_calendar_validation(self):
        validate_event(self.event())
        bad=self.event();bad['starts_at']='2026-03-29T02:30:00+01:00'
        with self.assertRaises(ValueError):validate_event(bad)
        for update in [dict(time_kind='undated'),dict(time_kind='all_day',start_date='2026-02-29'),dict(ends_at='2026-03-29T03:00:00+02:00')]:
            e=self.event();e.update(update)
            with self.assertRaises(ValueError):validate_event(e)


if __name__=='__main__':unittest.main()
