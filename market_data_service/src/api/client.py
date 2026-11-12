import asyncio
import json
import logging
import time
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
import httpx
from src.api.endpoints import ENDPOINTS, validate_params
from src.config.settings import Settings


class UpstreamError(Exception):
    def __init__(self, kind: str, status: int | None = None):
        self.kind, self.status = kind, status
        super().__init__(f'BrsApi {kind}' + (f' (HTTP {status})' if status else ''))


class BrsClient:
    def __init__(self, settings: Settings, transport=None, sleep=asyncio.sleep):
        self.settings = settings
        self.http = httpx.AsyncClient(base_url='https://Api.BrsApi.ir/', timeout=settings.request_timeout,
             transport=transport, follow_redirects=False,
             headers={'User-Agent': 'Mozilla/5.0 (compatible; MarketData/1.0)', 'Accept': 'application/json'})
        self.sleep = sleep
        self.lock = asyncio.Lock()
        self.last_request = 0.0
        self.cooldown_until = 0.0
        self.account_blocked = False

    async def close(self):
        await self.http.aclose()

    async def get(self, endpoint: str, **params: Any) -> Any:
        if self.account_blocked:
            raise UpstreamError('account_blocked', 403)
        clean = validate_params(endpoint, dict(params))
        key = self.settings.brs_api_key.get_secret_value()
        if not key:
            raise UpstreamError('missing_key')
        # Shared lock serializes all calls and retries in this worker.
        async with self.lock:
            if time.monotonic() < self.cooldown_until:
                raise UpstreamError('rate_limit_cooldown', 429)
            for attempt in range(self.settings.max_retries + 1):
                await self.sleep(max(0, self.last_request + self.settings.request_interval - time.monotonic()))
                self.last_request = time.monotonic()
                started = time.monotonic()
                try:
                    r = await self.http.get(ENDPOINTS[endpoint].path, params={'key': key, **clean})
                except (httpx.TransportError, httpx.TimeoutException):
                    if attempt == self.settings.max_retries:
                        raise UpstreamError('network') from None
                    await self.sleep(min(2 ** attempt, self.settings.max_retry_wait))
                    continue
                logging.getLogger('market').info(json.dumps({'endpoint': endpoint, 'status': r.status_code,
                    'elapsed_ms': round((time.monotonic() - started) * 1000), 'attempt': attempt + 1}))
                if r.status_code == 403 and ('بیش از ظرفیت' in r.text or 'کلید وب' in r.text and 'مسدود' in r.text):
                    self.account_blocked = True
                    raise UpstreamError('account_blocked', 403)
                if r.status_code in (401, 403):
                    raise UpstreamError('authentication_or_plan', r.status_code)
                if r.status_code == 429 or r.status_code >= 500:
                    wait = self.retry_after(r.headers.get('Retry-After'), 2 ** attempt)
                    if r.status_code == 429:
                        self.cooldown_until = time.monotonic() + wait
                    if attempt == self.settings.max_retries or wait > self.settings.max_retry_wait:
                        raise UpstreamError('rate_limit' if r.status_code == 429 else 'server', r.status_code)
                    await self.sleep(wait)
                    self.cooldown_until = 0
                    continue
                if r.status_code >= 300:
                    raise UpstreamError('http', r.status_code)
                try:
                    payload = json.loads(r.text, parse_float=Decimal)
                except (ValueError, TypeError):
                    raise UpstreamError('invalid_json') from None
                if isinstance(payload, dict):
                    if payload.get('successful') is False or payload.get('success') is False or payload.get('status') in ('error', 'failed') or payload.get('error'):
                        # Upstream text may echo credentials; only a safe category is exposed.
                        raise UpstreamError('api_error')
                    code = payload.get('code_http')
                    if code is not None and str(code) != '200':
                        raise UpstreamError('api_error')
                return payload
        raise UpstreamError('unreachable')

    @staticmethod
    def retry_after(value: str | None, fallback: float) -> float:
        if value:
            try:
                return max(0, float(value))
            except ValueError:
                try:
                    return max(0, (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds())
                except (ValueError, TypeError):
                    pass
        return fallback
