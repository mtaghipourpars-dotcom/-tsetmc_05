from typing import Any
from src.repositories.database import upsert
from src.repositories.models import symbols, indices, TABLES, now
from src.services.normalization import symbol, jalali_date, clock, number, digest, today

def provider_key(source, *parts):
    # Preserve v1 BrsApi keys across upgrade; other sources have their own namespace.
    return digest(*parts) if source == 'brsapi' else digest(source, *parts)

PRICE = {'trade_count': 'tno', 'volume': 'tvol', 'value': 'tval', 'price_min': 'pmin',
    'price_max': 'pmax', 'price_yesterday': 'py', 'price_first': 'pf', 'price_last': 'pl',
    'price_last_change': 'plc', 'price_last_change_pct': 'plp', 'price_close': 'pc',
    'price_close_change': 'pcc', 'price_close_change_pct': 'pcp'}


def require(r, *keys):
    if any(r.get(k) in (None, '') for k in keys):
        raise ValueError('missing_' + '_'.join(keys))


def ensure_symbol(conn, name, row=None):
    r = row or {}
    name = symbol(name)
    if not name:
        raise ValueError('missing_symbol')
    values = {'symbol_l18': name, 'raw': r, 'updated_at': now()}
    for source, dest in [('id', 'ins_code'), ('isin', 'isin'), ('l30', 'symbol_name'), ('m', 'market'), ('cs', 'sector')]:
        if r.get(source) is not None:
            values[dest] = str(r[source])
    if not row:
        # A sparse history row must never overwrite reference data.
        from sqlalchemy import select
        found = conn.execute(select(symbols.c.id).where(symbols.c.symbol_l18 == name)).scalar_one_or_none()
        if found is not None:
            return found
    return upsert(conn, symbols, values, ['symbol_l18'])


def map_rows(conn, endpoint: str, r: dict[str, Any], params: dict, raw_id: int, source: str = 'brsapi'):
    if not isinstance(r, dict):
        raise ValueError('record_not_object')
    if endpoint == 'symbols':
        require(r, 'l18')
        ensure_symbol(conn, r['l18'], r)
        return 1
    name = r.get('l18') or params.get('l18')
    sid = ensure_symbol(conn, name, r if endpoint in ('symbol', 'options', 'ime_funds') else None) if name else None
    date_source = r.get('date_publish') if endpoint == 'codal' else r.get('date') or r.get('date_trade') or r.get('date_update')
    date_basis = 'provider'
    if not date_source and r.get('_context_date'):
        date_source, date_basis = r['_context_date'], 'provider_context'
    if not date_source:
        if params.get('date'):
            date_source, date_basis = params['date'], 'requested'
        elif endpoint in ('history', 'candles', 'codal', 'transactions'):
            raise ValueError('missing_source_date')
        else:
            date_source, date_basis = today(), 'observed'
    d = jalali_date(date_source)
    tm = clock(r.get('time_publish') if endpoint == 'codal' else r.get('time') or r.get('time_update'))
    base = {'symbol_id': sid, 'date_shamsi': d, 'date_basis': date_basis, 'time_shamsi': tm,
            'raw_id': raw_id, 'raw': r, 'recorded_at': now(), 'source': source}
    identity: list[Any] = [sid, d, tm, date_basis]
    values = {}
    table_name = endpoint
    mapping = {}
    if endpoint in ('history', 'candles', 'symbol', 'nav', 'transactions', 'shareholders', 'options') and sid is None:
        raise ValueError('missing_symbol')
    if endpoint == 'history':
        identity = [sid, d]  # daily history updates the same day; nullable time is not a key
        if params['type'] == 0:
            table_name, mapping = 'price_history', PRICE
            require(r, 'pc')
        else:
            table_name = 'client_type_history'
            mapping = {f'{side}_{group}_{metric}': f'{side.title()}_{suffix}' for side in ('buy', 'sell')
              for group, code in [('real', 'I'), ('legal', 'N')]
              for metric, suffix in [('count', f'Count{code}'), ('volume', f'{code}_Volume'), ('value', f'{code}_Value')]}
            if not any(k in r for k in mapping.values()):
                raise ValueError('missing_client_type_fields')
    elif endpoint == 'candles':
        require(r, 'open', 'high', 'low', 'close')
        if params['type'] == 1 and not tm:
            raise ValueError('missing_intraday_time')
        table_name, mapping = 'candlesticks', {k: k for k in ('open', 'high', 'low', 'close', 'volume')}
        values['candle_type'] = params['type']
        identity = [sid, params['type'], d, tm if params['type'] == 1 else '']
        if params['type'] != 1:
            base['time_shamsi'] = ''
    elif endpoint == 'symbol':
        table_name = 'symbol_snapshots'
        mapping = {'price_last': 'pl', 'price_close': 'pc', 'volume': 'tvol', 'value': 'tval'}
    elif endpoint == 'transactions':
        require(r, 'row', 'price', 'volume')
        if not tm:
            raise ValueError('missing_trade_time')
        values['row_num'] = number(r['row'], integer=True, nonnegative=True)
        canceled = number(r.get('canceled', 0), integer=True)
        if canceled not in (0, 1):
            raise ValueError('invalid_canceled_flag')
        values['canceled'] = bool(canceled)
        mapping = {'price': 'price', 'volume': 'volume'}
        identity = [sid, d, values['row_num']]
    elif endpoint == 'shareholders':
        require(r, 'name')
        values['shareholder_name'] = r['name']
        mapping = {'percentage': 'percent', 'change': 'change', 'volume': 'volume'}
        identity = [sid, d, r['name'], date_basis]
    elif endpoint == 'nav':
        table_name, mapping = 'etf_nav', {'nav_issue': 'psubtran', 'nav_value': 'predtran'}
        require(r, 'predtran')
    elif endpoint == 'indices':
        table_name = 'index_values'
        index_id = upsert(conn, indices, {'index_type': params['type'], 'name': r.get('name') or f"market-{params['type']}", 'state': r.get('state')}, ['index_type', 'name'])
        values['index_id'] = index_id
        require(r, 'index')
        mapping = {'value': 'index', 'change_value': 'index_change', 'change_percent': 'index_change_percent',
          'min_value': 'min', 'max_value': 'max', 'equal_weight': 'index_equalWeight', 'equal_weight_change': 'index_equalWeight_change'}
        identity = [index_id, d, tm]
    elif endpoint == 'options':
        table_name = 'tse_options'
        values.update(contract_name=r.get('l30'), underlying=r.get('base_l18'), option_type=r.get('type'),
                      expiry_date=jalali_date(r['date_end']) if r.get('date_end') else None)
        mapping = {'strike_price': 'price_strike', 'last_price': 'pl', 'volume': 'tvol', 'open_interest': 'interest_open'}
    elif endpoint == 'codal':
        table_name = 'codal_announcements'
        require(r, 'title', 'link')
        values.update(title=r['title'], url=r['link'], summary=r.get('summary'))
        identity = [r['link']]
    elif endpoint == 'commodities':
        require(r, 'symbol', 'price')
        values.update(commodity_symbol=r['symbol'], commodity_name=r.get('name'), unit=r.get('unit'))
        mapping = {k: k for k in ('price', 'change_value', 'change_percent')}
        identity = [r['symbol'], d, tm]
    elif endpoint == 'ime_options':
        count = 0
        # IME represents a call and a put in one row. Store both contracts separately.
        for leg in ('call', 'put'):
            code = r.get(f'{leg}_contract_code')
            if not code:
                continue
            out = dict(base, contract_code=code, contract_name=r.get(f'{leg}_contract_description'),
                underlying=r.get('contract_category_commodity'), option_type=leg,
                expiry_date=jalali_date(r[f'{leg}_date_end']) if r.get(f'{leg}_date_end') else None,
                currency=r.get(f'{leg}_contract_currency'), value_unit=r.get(f'{leg}_tval_unit'))
            for dest, source in [('strike_price', 'price_strike'), ('last_price', f'{leg}_pl'), ('volume', f'{leg}_tvol'), ('value', f'{leg}_tval')]:
                out[dest] = number(r.get(source), nonnegative=True)
            out['open_interest'] = number(r.get(f'{leg}_interest_open'), integer=True, nonnegative=True)
            out['natural_key'] = provider_key(source, endpoint, code, d, tm)
            upsert(conn, TABLES[endpoint], out, ['natural_key'])
            count += 1
        if not count:
            raise ValueError('missing_option_legs')
        return count
    elif endpoint.startswith('ime_'):
        code = r.get('contract_code') or r.get('l18')
        if not code:
            raise ValueError('missing_contract_code')
        values.update(contract_code=code, contract_name=r.get('contract_description') or r.get('l30'),
            underlying=r.get('commodity'), currency=r.get('contract_currency') or r.get('currency'),
            unit=r.get('unit') or r.get('contract_size_unit'), value_unit=r.get('tval_unit'),
            expiry_date=jalali_date(r['date_end']) if r.get('date_end') else None,
            offer_code=str(r['code_offer']) if r.get('code_offer') is not None else None)
        mapping = {'last_price': 'pl', 'volume': 'volume_contract' if endpoint == 'ime_physical' else 'tvol',
                   'value': 'tval', 'open_interest': 'interest_open', 'nav': 'predtran'}
        identity = [code, d, tm]
        if endpoint == 'ime_physical':
            require(r, 'code_offer')
            # Multiple settlement/contract variants can share an offer code.
            identity = [r['code_offer'], d, r.get('type_contract'), r.get('type_settlement'), r.get('market_hall')]
    else:
        raise ValueError('unknown_mapper')
    integer_cols = {'trade_count', 'volume', 'open_interest'} if not endpoint.startswith('ime_') else {'open_interest'}
    for dest, source in mapping.items():
        is_count = dest.endswith('_count') or dest.endswith('_volume') or dest in integer_cols
        nonnegative = is_count or dest in ('open', 'high', 'low', 'close', 'price', 'price_close', 'price_last', 'last_price', 'nav_issue', 'nav_value', 'strike_price')
        values[dest] = number(r.get(source), integer=is_count, nonnegative=nonnegative)
    if endpoint == 'candles':
        if values['high'] < max(values['open'], values['low'], values['close']) or values['low'] > min(values['open'], values['close']):
            raise ValueError('invalid_ohlc')
    out = dict(base, **values, natural_key=provider_key(source, table_name, *identity))
    upsert(conn, TABLES[table_name], out, ['natural_key'])
    return 1
