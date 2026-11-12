import httpx
import pytest
from src.api.client import BrsClient, UpstreamError
from src.api.endpoints import ENDPOINTS


async def test_retries_429_then_500_then_success(settings):
    calls, waits = [], []
    async def handler(r):
        calls.append(r)
        status = [429, 500, 200][len(calls)-1]
        return httpx.Response(status, headers={'Retry-After': '2'}, json=[])
    async def sleep(s):
        waits.append(s)
    c = BrsClient(settings, transport=httpx.MockTransport(handler), sleep=sleep)
    assert await c.get('symbols') == []
    assert len(calls) == 3
    assert calls[0].url.params['key'] == 'test-key'
    assert waits.count(2) == 2
    await c.close()


@pytest.mark.parametrize('status', [401, 403, 404])
async def test_no_retry_for_permanent_failure(settings, status):
    calls = []
    async def handler(r):
        calls.append(r)
        return httpx.Response(status, text='sensitive upstream response test-key')
    c = BrsClient(settings, transport=httpx.MockTransport(handler))
    with pytest.raises(UpstreamError) as error:
        await c.get('symbols')
    assert len(calls) == 1
    assert 'test-key' not in str(error.value)
    await c.close()


async def test_long_retry_after_blocks_following_requests(settings):
    calls = []
    async def handler(r):
        calls.append(r)
        return httpx.Response(429, headers={'Retry-After': '86400'})
    c = BrsClient(settings, transport=httpx.MockTransport(handler))
    for _ in range(2):
        with pytest.raises(UpstreamError):
            await c.get('symbols')
    assert len(calls) == 1
    await c.close()


@pytest.mark.parametrize('payload', [{'successful': False, 'message_error': 'test-key'}, {'error': 'quota'}, {'code_http': 403}])
async def test_json_errors_are_not_success(settings, payload):
    c = BrsClient(settings, transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload)))
    with pytest.raises(UpstreamError) as error:
        await c.get('symbols')
    assert 'test-key' not in str(error.value)
    await c.close()


async def test_network_retries_and_invalid_json(settings):
    calls = []
    async def handler(r):
        calls.append(r)
        raise httpx.ConnectError('secret test-key', request=r)
    async def sleep(_): pass
    c = BrsClient(settings, transport=httpx.MockTransport(handler), sleep=sleep)
    with pytest.raises(UpstreamError, match='network'):
        await c.get('symbols')
    assert len(calls) == 3
    await c.close()
    c = BrsClient(settings, transport=httpx.MockTransport(lambda r: httpx.Response(200, text='<html>error</html>')))
    with pytest.raises(UpstreamError, match='invalid_json'):
        await c.get('symbols')
    await c.close()


async def test_parameter_validation_happens_before_http(settings):
    def handler(r):
        pytest.fail('must not send invalid request')
    c = BrsClient(settings, transport=httpx.MockTransport(handler))
    for endpoint, params in [('nav', {}), ('history', {'l18':'فملی','type':3}), ('history', {'l18':'فملی','type':0,'date_start':'1405-01-01'}), ('codal', {'audited':'true'})]:
        with pytest.raises(ValueError):
            await c.get(endpoint, **params)
    await c.close()


async def test_boolean_parameters_and_commodity_path(settings):
    requests = []
    async def handler(r):
        requests.append(r)
        return httpx.Response(200, json=[])
    c = BrsClient(settings, transport=httpx.MockTransport(handler))
    await c.get('codal', audited=False, date_start='۱۴۰۵/۰۱/۰۱')
    await c.get('commodities')
    assert requests[0].url.params['audited'] == 'false'
    assert requests[0].url.params['date_start'] == '1405-01-01'
    assert requests[1].url.path == '/Market/Commodity.php'
    assert len(ENDPOINTS) == 16
    await c.close()
