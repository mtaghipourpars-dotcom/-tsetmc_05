import hashlib
import json
import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo
import jdatetime
from src.repositories.database import json_default

DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')


def text(value: Any) -> str:
    return str(value).translate(DIGITS).strip()


def symbol(value: Any) -> str:
    return str(value).replace('ي', 'ی').replace('ك', 'ک').strip()


def today() -> str:
    return jdatetime.date.fromgregorian(date=datetime.now(ZoneInfo('Asia/Tehran')).date()).isoformat()


def jalali_date(value: Any) -> str:
    s = text(value).replace('/', '-')
    if re.fullmatch(r'\d{8}', s):
        s = f'{s[:4]}-{s[4:6]}-{s[6:]}'
    if not re.fullmatch(r'\d{4}-\d{1,2}-\d{1,2}', s):
        raise ValueError('invalid_date')
    y, m, d = map(int, s.split('-'))
    if y >= 1700:
        return jdatetime.date.fromgregorian(date=date(y, m, d)).isoformat()
    if not 1200 <= y <= 1699:
        raise ValueError('invalid_date_year')
    return jdatetime.date(y, m, d).isoformat()


def clock(value: Any) -> str:
    if value in (None, ''):
        return ''
    s = text(value)
    if re.fullmatch(r'\d{6}', s):
        s = f'{s[:2]}:{s[2:4]}:{s[4:]}'
    parts = s.split(':')
    if len(parts) == 2:
        parts.append('00')
    if len(parts) != 3:
        raise ValueError('invalid_time')
    h, m, sec = map(int, parts)
    if not (0 <= h < 24 and 0 <= m < 60 and 0 <= sec < 60):
        raise ValueError('invalid_time')
    return f'{h:02d}:{m:02d}:{sec:02d}'


def number(value: Any, integer=False, nonnegative=False):
    if value is None or value == '':
        return None
    if isinstance(value, bool):
        raise ValueError('invalid_number')
    try:
        s = text(value).replace(',', '').replace('٬', '').replace('٫', '.')
        n = Decimal(s)
    except InvalidOperation:
        raise ValueError('invalid_number') from None
    if not n.is_finite() or (nonnegative and n < 0) or (integer and n != n.to_integral_value()):
        raise ValueError('invalid_number')
    if integer:
        if abs(n) > 9223372036854775807:
            raise ValueError('integer_overflow')
        return int(n)
    if abs(n) >= Decimal('1e24') or n.as_tuple().exponent < -6:
        raise ValueError('numeric_precision_exceeded')
    return n


def digest(*parts):
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False, sort_keys=True, default=json_default).encode()).hexdigest()


def records(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ('data', 'announcement', 'candle_intraday', 'candle_daily', 'candle_daily_adjusted', 'candles', 'candlestick', 'items', 'result'):
            if key in payload:
                value = payload[key]
                if isinstance(value, list):
                    return value
                if isinstance(value, dict):
                    return records(value)
                raise ValueError('invalid_envelope')
        if any(k in payload for k in ('l18', 'index', 'predtran', 'row', 'open', 'contract_code', 'symbol')):
            return [payload]
    raise ValueError('unknown_response_shape')
