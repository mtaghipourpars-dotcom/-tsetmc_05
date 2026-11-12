"""Public, read-only TSETMC transport. No BrsApi credential is ever sent here."""
import asyncio
import base64
import json
import re
import time
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote, urlsplit, parse_qsl
import httpx
from src.api.client import BrsClient, UpstreamError

CATALOG = {r['id']: r for r in json.loads(Path(__file__).with_name('tsetmc_registry.json').read_text(encoding='utf-8'))}
WATCH_QUERY = {'market': 0, 'paperTypes[0]': 1, 'paperTypes[1]': 2, 'paperTypes[2]': 8,
               'showTraded': 'true', 'withBestLimits': 'true', 'hEven': 0, 'RefID': 0}


@dataclass
class TseResponse:
    endpoint: str
    origin: str
    path: str
    payload: object
    format: str
    content: bytes
    status: int


class TseClient:
    def __init__(self, settings, transport=None, sleep=asyncio.sleep):
        self.settings = settings
        proxy = settings.tsetmc_proxy_url.get_secret_value() or None
        self.http = httpx.AsyncClient(timeout=settings.request_timeout, transport=transport,
            proxy=proxy, follow_redirects=False, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36',
                'Accept': 'application/json,text/plain,text/csv,*/*', 'Referer': 'https://www.tsetmc.com/'})
        self.lock = asyncio.Lock()
        self.last_request = 0.0
        self.cooldown_until = 0.0
        self.origin_cooldown = {}
        self.sleep = sleep

    async def close(self):
        await self.http.aclose()

    @staticmethod
    def request(endpoint, path_params=None, query=None):
        if endpoint not in CATALOG:
            raise ValueError('Unknown TSETMC endpoint')
        entry = CATALOG[endpoint]
        supplied = dict(path_params or {})
        if set(supplied) != set(entry['parameters']):
            raise ValueError('Supply exactly the catalog parameters: ' + ','.join(entry['parameters']))
        for name, value in supplied.items():
            value = str(value)
            if len(value) > 500 or any(t in value for t in ('/', '\\', '..', '?', '#')):
                raise ValueError('Invalid path parameter')
            if name.lower() in ('inscode','deven','top','flow') and not value.isdigit():
                raise ValueError('Invalid numeric path parameter')
        # Percent encode every segment; never accept an operator-controlled URL from callers.
        safe = {k: quote(str(v), safe='') for k, v in supplied.items()}
        path = entry['path'].format_map(safe)
        template_query = {k: v.format_map({n: str(x) for n,x in supplied.items()}) for k,v in parse_qsl(entry['query_template'])}
        q = dict(WATCH_QUERY) if endpoint == 'market_watch' else {}
        q.update(template_query)
        q.update(query or {})
        if any(str(k).lower() in ('key','api_key','token','url','host') for k in q):
            raise ValueError('Credentials and target URLs are not TSETMC query parameters')
        return entry, path, q

    async def get(self, endpoint, path_params=None, query=None):
        entry, path, query = self.request(endpoint, path_params, query)
        if entry['origin'] == 'cdn.tsetmc.com':
            origins = [u.strip().rstrip('/') for u in self.settings.tsetmc_base_urls.split(',') if u.strip()]
        else:
            origins = ['https://' + entry['origin']]
        if not origins:
            raise ValueError('No TSETMC origin configured')
        async with self.lock:
            if time.monotonic() < self.cooldown_until:
                raise UpstreamError('tsetmc_cooldown', 429)
            last_kind, last_status = 'network', None
            for origin in origins:
                if self.origin_cooldown.get(origin, 0) > time.monotonic():
                    last_kind = 'circuit_open'
                    continue
                u = urlsplit(origin)
                if u.scheme != 'https' or u.username or u.password or u.path not in ('', '/') or not (u.hostname.endswith('.tsetmc.com') or u.hostname == 'webgw.tse.ir'):
                    raise ValueError('Only official HTTPS TSETMC/TSE origins are accepted; use TSETMC_PROXY_URL for your own proxy')
                for attempt in range(self.settings.max_retries + 1):
                    await self.sleep(max(0,self.last_request+self.settings.request_interval-time.monotonic()))
                    self.last_request = time.monotonic()
                    try:
                        response = await self.http.get(origin + path, params=query)
                    except httpx.TransportError:
                        last_kind, last_status = 'network', None
                        if attempt < self.settings.max_retries:
                            await self.sleep(min(2**attempt,self.settings.max_retry_wait))
                            continue
                        break
                    last_status = response.status_code
                    if response.status_code == 429:
                        wait = BrsClient.retry_after(response.headers.get('Retry-After'),60)
                        self.cooldown_until = time.monotonic()+wait
                        # Never evade a quota by hopping mirrors.
                        raise UpstreamError('tsetmc_rate_limit',429)
                    if response.status_code >= 500:
                        last_kind='server'
                        if attempt < self.settings.max_retries:
                            await self.sleep(min(2**attempt,self.settings.max_retry_wait));continue
                        break
                    if response.status_code >= 300:
                        last_kind='access' if response.status_code in (401,403) else 'http'
                        break
                    if response.status_code == 204:
                        return TseResponse(endpoint,origin,path,None,'empty',b'',204)
                    body=response.content
                    if entry['format']=='binary':
                        if 'text/html' in response.headers.get('content-type',''):
                            raise UpstreamError('unexpected_html')
                        return TseResponse(endpoint,origin,path,{'base64':base64.b64encode(body).decode()},'binary',body,200)
                    try:
                        payload=json.loads(response.text,parse_float=Decimal)
                        return TseResponse(endpoint,origin,path,payload,'json',body,200)
                    except ValueError:
                        if entry['format']=='text' and not response.text.lstrip().lower().startswith(('<!doctype','<html')):
                            return TseResponse(endpoint,origin,path,response.text,'text',body,200)
                        last_kind='invalid_json';break
                if last_kind in ('network','server'):
                    self.origin_cooldown[origin] = time.monotonic() + 60
            raise UpstreamError('tsetmc_'+last_kind,last_status)
