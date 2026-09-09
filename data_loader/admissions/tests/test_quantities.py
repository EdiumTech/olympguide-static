import copy
import unittest
from admissions.quantity_catalog import load, validate


class QuantityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load()

    def program(self, university, name, code=None):
        return next(p for p in self.data['programs'] if p['university_id'] == university and
                    p['name'] == name and (code is None or p['field_id'] == code))

    def test_no_scholarships_or_default_zero_prices(self):
        ai = self.program('itmo', 'AI360: ML Native')
        self.assertEqual((ai['budget_places'], ai['paid_places'], ai['cost']), (36, 0, None))
        self.assertEqual(sum(q['cost'] is not None for q in self.data['programs']), 367)
        self.assertTrue(all(q['cost'] is None or 0 < q['cost'] <= 2000000 for q in self.data['programs']))

    def test_pdf_quotas_exclude_superscript_footnotes(self):
        for name, places in [('Государственно-правовая', 81), ('Речеведческие экспертизы', 12), ('Прокурорская деятельность', 175)]:
            p = self.program('msal', name)
            self.assertEqual(p['budget_places'], places)
            self.assertEqual(sum(p['quantity_evidence']['budget_places']['breakdown'].values()), places)

    def test_semester_and_institute_specific_tariff(self):
        finance = self.program('mephi', 'Информационно-аналитические системы финансового мониторинга')
        computer = self.program('mephi', 'Безопасность компьютерных систем (инновационные технологии компьютерной безопасности)')
        self.assertEqual((finance['cost'], computer['cost']), (245000, 265000))
        self.assertEqual(finance['cost_period'], 'semester')
        mipt = self.program('mipt', 'Фундаментальная математика')
        self.assertEqual((mipt['budget_places'], mipt['paid_places'], mipt['cost'], mipt['cost_period']), (15, 3, 1014000, 'year'))

    def test_hse_joint_and_internal_selection(self):
        items = [q for q in self.data['programs'] if q['university_id'] == 'hse' and q['name'] == 'Экономика и анализ данных']
        self.assertTrue(all((p['budget_places'], p['paid_places'], p['cost']) == (60, 110, 1000000) for p in items))
        internal = self.program('hse', 'Вычислительные социальные науки', '01.03.02')
        self.assertEqual(internal['quantity_evidence']['budget_places']['scope'], 'internal_selection')
        self.assertIsNone(internal['cost'])

    def test_reject_mismatched_provenance_and_coverage(self):
        for mutation in ('source', 'price', 'coverage'):
            data = copy.deepcopy(self.data)
            p = next(q for q in data['programs'] if q['cost'] is not None)
            if mutation == 'source': p['quantity_evidence']['cost']['source_url'] = 'https://example.org/'
            elif mutation == 'price': p['cost'] = 999999999
            else: data['coverage'][p['university_id']]['cost'] += 1
            with self.assertRaises(ValueError): validate(data)


if __name__ == '__main__':
    unittest.main()
