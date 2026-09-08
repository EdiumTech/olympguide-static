"""Opt-in PostgreSQL tests. Uses only uniquely named disposable fixtures."""
import json
import os
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path
from data_loader.admissions.personal import export_sql, literal


@unittest.skipUnless(os.environ.get('OLYMPGUIDE_TEST_DSN') and os.environ.get('PSQL'), 'Set OLYMPGUIDE_TEST_DSN and PSQL for a migrated disposable database')
class PersonalImportTest(unittest.TestCase):
    def sql(self,text):
        with tempfile.TemporaryDirectory(prefix='olympguide-import-test-') as folder:
            file=Path(folder)/'test.sql';file.write_text(text,encoding='utf-8')
            result=subprocess.run([os.environ['PSQL'],'-X','-q','-A','-t','-v','ON_ERROR_STOP=1','-d',os.environ['OLYMPGUIDE_TEST_DSN'],'-f',str(file)],capture_output=True,encoding='utf-8')
        if result.returncode:self.fail(result.stderr)
        return result.stdout.strip()

    def test_repeat_date_update_withdrawal_preserve_owned_plan(self):
        key='import-test-'+uuid.uuid4().hex
        user=int(self.sql('INSERT INTO olympguide."user"(email,password_hash) VALUES('+literal(key+'@test.invalid')+",'test') RETURNING user_id;"))
        event=dict(id=key,collection_key=key,title='Тест импорта',kind='registration_close',season='2026/2027',admission_year=None,
            time_kind='all_day',start_date='2026-09-20',timezone='Europe/Moscow',source_url='https://official.example/',checked_on='2026-09-08',revision='r1',olympiad_keys=[],program_keys=[])
        data=dict(schema_version=1,admission_year=2026,scholarships=[],events=[event],event_collections=[key])
        try:
            self.sql(export_sql(data))
            plan=int(self.sql(f"INSERT INTO olympguide.calendar_plan(user_id,event_id,status,note,seen_revision) VALUES({user},{literal(key)},'registered','keep marks','r1') RETURNING plan_id;"))
            self.sql(export_sql(data));event.update(start_date='2026-09-21',revision='r2');self.sql(export_sql(data))
            raw=self.sql(f"SELECT json_build_object('id',p.plan_id,'status',p.status,'note',p.note,'seen',p.seen_revision,'date',e.payload->>'start_date','count',(SELECT count(*) FROM olympguide.calendar_plan WHERE user_id={user})) FROM olympguide.calendar_plan p JOIN olympguide.calendar_event e ON e.id=p.event_id WHERE p.user_id={user};")
            self.assertEqual(json.loads(raw),dict(id=plan,status='registered',note='keep marks',seen='r1',date='2026-09-21',count=1))
            data['events']=[];self.sql(export_sql(data))
            self.assertEqual(self.sql(f"SELECT active FROM olympguide.calendar_event WHERE id={literal(key)};"),'f')
            self.assertEqual(self.sql(f"SELECT count(*) FROM olympguide.calendar_plan WHERE user_id={user};"),'1')
        finally:
            self.sql(f'DELETE FROM olympguide."user" WHERE user_id={user}; DELETE FROM olympguide.calendar_event WHERE id={literal(key)};')


if __name__=='__main__':unittest.main()
