import io
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend_proxy import forward


class Request:
    def __init__(self,method='GET',path='/backend/user/calendar',**headers):
        self.command=method;self.path=path;self.server=SimpleNamespace(server_port=8770)
        self.headers={'Host':'127.0.0.1:8770',**headers};self.rfile=io.BytesIO(b'{}');self.wfile=io.BytesIO();self.response_headers={};self.status=None
    def send_data(self,data,content_type,head,status):self.status=status
    def send_response(self,status):self.status=status
    def send_header(self,name,value):self.response_headers[name]=value
    def end_headers(self):pass


class Connection:
    requests=[]
    def __init__(self,*args,**kwargs):pass
    def request(self,method,path,**kwargs):self.requests.append((method,path,kwargs))
    def getresponse(self):return SimpleNamespace(status=200,read=lambda size:b'[]',getheaders=lambda:[('Set-Cookie','session=example; Domain=api.olympguide.ru; Secure; HttpOnly; Path=/')])
    def close(self):pass


class PersonalProxyTests(unittest.TestCase):
    def test_csrf_rebinding_and_arbitrary_paths_blocked_before_network(self):
        requests=[(Request('POST'),403),(Request(Host='evil.example:8770'),403),(Request(path='/backend/admin/users'),404),(Request(path='/backend/https://evil.example'),404),
            (Request('POST',Origin='https://evil.example',**{'Content-Type':'application/json'}),403)]
        with patch('backend_proxy.http.client.HTTPSConnection',side_effect=AssertionError('must not send')):
            for req,status in requests:forward(req,'https://api.olympguide.ru/api/v1');self.assertEqual(req.status,status)

    def test_session_is_browser_specific_and_http_only(self):
        Connection.requests=[]
        with patch('backend_proxy.http.client.HTTPSConnection',Connection):
            for cookie in ['session=userA; other=not-forwarded','session=userB','']:
                req=Request(Cookie=cookie);forward(req,'https://api.olympguide.ru/api/v1')
                self.assertEqual(req.status,200)
                value=req.response_headers['Set-Cookie'];self.assertIn('HttpOnly',value);self.assertIn('SameSite=Strict',value);self.assertIn('Path=/backend',value);self.assertNotIn('Domain=',value)
        headers=[r[2]['headers'] for r in Connection.requests]
        self.assertEqual(headers[0]['Cookie'],'session=userA');self.assertEqual(headers[1]['Cookie'],'session=userB');self.assertNotIn('Cookie',headers[2])

    def test_local_json_write_and_size_limit(self):
        with patch('backend_proxy.http.client.HTTPSConnection',Connection):
            req=Request('PUT',path='/backend/user/calendar/1',Origin='http://127.0.0.1:8770',**{'Content-Type':'application/json','Content-Length':'2'})
            forward(req,'https://api.olympguide.ru/api/v1');self.assertEqual(req.status,200)
            req.headers['Content-Length']='65537';forward(req,'https://api.olympguide.ru/api/v1');self.assertEqual(req.status,413)


if __name__=='__main__':unittest.main()
