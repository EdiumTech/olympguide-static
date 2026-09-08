"""Narrow same-origin bridge to the existing Go session API.

Only the configured upstream is contacted. Cookies stay in each browser's
HttpOnly cookie jar; there is no global logged-in session in this process.
"""
import http.client
from http.cookies import SimpleCookie
import json
import re
from urllib.parse import urlsplit

ALLOWED = re.compile(r'^/(?:auth/(?:login|logout|check-session)|calendar/events|scholarships|'
    r'user/(?:calendar(?:/custom|/\d+)?|diplomas/?|diploma(?:/\d+(?:/details)?)?/?|admission-profile|recommendations)|'
    r'olympiads|olympiad/\d+/?|program/\d+/?|personal/catalog)$')


def forward(handler, upstream, *, head=False):
    origin=urlsplit(upstream)
    if origin.scheme not in ('https','http') or not origin.hostname or origin.username:
        raise ValueError('Invalid API upstream')
    if origin.scheme=='http' and origin.hostname not in ('localhost','127.0.0.1','::1'):
        raise ValueError('HTTP API is allowed only on loopback')
    host=handler.headers.get('Host','')
    allowed_hosts={f'127.0.0.1:{handler.server.server_port}', f'localhost:{handler.server.server_port}',f'[::1]:{handler.server.server_port}'}
    # The personal viewer is intentionally local. Block DNS rebinding and CSRF.
    if host not in allowed_hosts:
        return handler.send_data(b'{"message":"Invalid local host"}','application/json',head,403)
    if handler.command not in ('GET','HEAD'):
        if handler.headers.get('Origin')!=f'http://{host}' or handler.headers.get('Content-Type','').split(';')[0]!='application/json':
            return handler.send_data(b'{"message":"Invalid request origin"}','application/json',head,403)
    suffix=handler.path.removeprefix('/backend')
    parsed=urlsplit(suffix)
    if not ALLOWED.fullmatch(parsed.path):return handler.send_data(b'{}','application/json',head,404)
    try:
        size=int(handler.headers.get('Content-Length','0'))
        if not 0<=size<=65536:raise ValueError()
    except ValueError:return handler.send_data(b'{}','application/json',head,413)
    body=handler.rfile.read(size) if size else None
    headers={'Accept':'application/json','Content-Type':'application/json'}
    cookie=SimpleCookie()
    try:cookie.load(handler.headers.get('Cookie',''))
    except Exception:cookie=SimpleCookie()
    if 'session' in cookie:headers['Cookie']='session='+cookie['session'].coded_value
    conn_class=http.client.HTTPSConnection if origin.scheme=='https' else http.client.HTTPConnection
    conn=conn_class(origin.hostname,origin.port,timeout=20)
    try:
        conn.request(handler.command,origin.path.rstrip('/')+suffix,body=body,headers=headers)
        response=conn.getresponse();data=response.read(8*1024*1024)
        handler.send_response(response.status)
        handler.send_header('Content-Type','application/json; charset=utf-8')
        handler.send_header('Content-Length',str(len(data)))
        handler.send_header('Cache-Control','no-store')
        handler.send_header('X-Content-Type-Options','nosniff')
        for name,value in response.getheaders():
            if name.lower()!='set-cookie':continue
            cookies=SimpleCookie();cookies.load(value)
            if 'session' not in cookies:continue
            item=cookies['session'];item['domain']='';item['path']='/backend';item['secure']='';item['httponly']=True;item['samesite']='Strict'
            handler.send_header('Set-Cookie',item.OutputString())
        handler.end_headers()
        if not head:handler.wfile.write(data)
    except (OSError,http.client.HTTPException):
        handler.send_data(json.dumps({'message':'API недоступен. Личный план не изменён.'},ensure_ascii=False).encode(),'application/json',head,502)
    finally:conn.close()
