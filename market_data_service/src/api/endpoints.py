from dataclasses import dataclass
from typing import Any
import jdatetime


@dataclass(frozen=True)
class Endpoint:
    path: str
    required: tuple[str, ...] = ()
    optional: tuple[str, ...] = ()
    types: tuple[int, ...] = ()


ENDPOINTS = {
    'symbols': Endpoint('Tsetmc/AllSymbols.php', optional=('type',), types=(1, 2, 3, 4, 5)),
    'indices': Endpoint('Tsetmc/Index.php', ('type',), types=(1, 2, 3)),
    'symbol': Endpoint('Tsetmc/Symbol.php', ('l18',)),
    'nav': Endpoint('Tsetmc/Nav.php', ('l18',)),
    'options': Endpoint('Tsetmc/Option.php'),
    'transactions': Endpoint('Tsetmc/Transaction.php', ('l18',), ('date',)),
    'history': Endpoint('Tsetmc/History.php', ('type', 'l18'), types=(0, 1)),
    'candles': Endpoint('Tsetmc/Candlestick.php', ('type', 'l18'), types=(1, 2, 3)),
    'shareholders': Endpoint('Tsetmc/Shareholder.php', ('l18',), ('date',)),
    'codal': Endpoint('Codal/Announcement.php', optional=('l18', 'category', 'period', 'audited',
                        'unaudited', 'only_main_company', 'only_subsidiaries', 'date_start', 'date_end', 'page')),
    'ime_futures': Endpoint('IME/Futures.php'),
    'ime_options': Endpoint('IME/Option.php'),
    'ime_certificates': Endpoint('IME/Certificate.php'),
    'ime_funds': Endpoint('IME/Fund.php'),
    'ime_physical': Endpoint('IME/Physical.php', optional=('date_start', 'date_end')),
    'commodities': Endpoint('Market/Commodity.php'),
}


def validate_params(name: str, params: dict[str, Any]) -> dict[str, Any]:
    if name not in ENDPOINTS:
        raise ValueError('Unknown endpoint')
    spec = ENDPOINTS[name]
    if set(params) - set(spec.required + spec.optional):
        raise ValueError('Unsupported upstream parameter')
    if any(params.get(k) in (None, '') for k in spec.required):
        raise ValueError('Missing required upstream parameter')
    if 'type' in params and (isinstance(params['type'], bool) or params['type'] not in spec.types):
        raise ValueError('Invalid type')
    from src.services.normalization import jalali_date
    for k in ('date', 'date_start', 'date_end'):
        if k in params:
            params[k] = jalali_date(params[k])
    if params.get('date_start', '') > params.get('date_end', '9999'):
        raise ValueError('date_start must precede date_end')
    for k, low, high in [('category', 1, 11), ('period', 1, 12), ('page', 1, 1_000_000)]:
        if k in params and (type(params[k]) is not int or not low <= params[k] <= high):
            raise ValueError(f'Invalid {k}')
    for k in ('audited', 'unaudited', 'only_main_company', 'only_subsidiaries'):
        if k in params and not isinstance(params[k], bool):
            raise ValueError(f'{k} must be boolean')
    return {k: str(v).lower() if isinstance(v, bool) else v for k, v in params.items()}
