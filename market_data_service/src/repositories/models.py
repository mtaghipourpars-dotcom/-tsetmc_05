"""SQLAlchemy Core schema. JSONB on PostgreSQL, JSON in isolated SQLite tests."""
from datetime import datetime, timezone
from sqlalchemy import (MetaData, Table, Column, Integer, BigInteger, Numeric, String, Text,
                        Boolean, DateTime, ForeignKey, UniqueConstraint, Index, JSON)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()
JSON_TYPE = JSON().with_variant(JSONB, 'postgresql')
BIG = BigInteger().with_variant(Integer, 'sqlite')
MONEY = Numeric(30, 6)


def now():
    return datetime.now(timezone.utc)


symbols = Table('symbols', metadata,
    Column('id', Integer, primary_key=True),
    Column('symbol_l18', String(100), nullable=False, unique=True),
    Column('ins_code', String(40), index=True), Column('isin', String(40)),
    Column('symbol_name', String(500)), Column('market', String(100)), Column('sector', String(500)),
    Column('is_active', Boolean, nullable=False, default=True),
    Column('raw', JSON_TYPE, nullable=False),
    Column('created_at', DateTime(timezone=True), default=now, nullable=False),
    Column('updated_at', DateTime(timezone=True), default=now, nullable=False))
indices = Table('indices', metadata, Column('id', Integer, primary_key=True),
    Column('index_type', Integer, nullable=False), Column('name', String(200), nullable=False),
    Column('state', String(100)), UniqueConstraint('index_type', 'name'))
raw_responses = Table('raw_responses', metadata,
    Column('id', BIG, primary_key=True), Column('endpoint', String(40), nullable=False, index=True),
    Column('params', JSON_TYPE, nullable=False), Column('payload', JSON_TYPE, nullable=False),
    Column('source', String(40), nullable=False, default='brsapi', server_default='brsapi'),
    Column('fetched_at', DateTime(timezone=True), default=now, nullable=False))
sync_runs = Table('sync_runs', metadata, Column('id', BIG, primary_key=True),
    Column('endpoint', String(40)), Column('params', JSON_TYPE), Column('status', String(30), nullable=False),
    Column('accepted', Integer, default=0), Column('rejected', Integer, default=0),
    Column('error_kind', String(100)), Column('started_at', DateTime(timezone=True), default=now),
    Column('finished_at', DateTime(timezone=True)))
sync_errors = Table('sync_errors', metadata, Column('id', BIG, primary_key=True),
    Column('run_id', BIG, ForeignKey('sync_runs.id')), Column('raw_id', BIG, ForeignKey('raw_responses.id')),
    Column('endpoint', String(40)), Column('error_kind', Text, nullable=False), Column('raw', JSON_TYPE),
    Column('recorded_at', DateTime(timezone=True), default=now))


def dataset(name: str, extras: list[Column]) -> Table:
    t = Table(name, metadata, Column('id', BIG, primary_key=True),
        Column('natural_key', String(64), nullable=False, unique=True),
        Column('symbol_id', Integer, ForeignKey('symbols.id'), index=True),
        Column('date_shamsi', String(10)), Column('date_basis', String(20), nullable=False),
        Column('time_shamsi', String(8), nullable=False, default=''),
        Column('raw_id', BIG, ForeignKey('raw_responses.id'), nullable=False),
        Column('source', String(40), nullable=False, default='brsapi', server_default='brsapi'),
        Column('raw', JSON_TYPE, nullable=False),
        Column('recorded_at', DateTime(timezone=True), default=now, nullable=False), *extras)
    Index(f'ix_{name}_symbol_date', t.c.symbol_id, t.c.date_shamsi)
    return t


def nums(*names):
    return [Column(n, MONEY) for n in names]


def counts(*names):
    return [Column(n, BigInteger) for n in names]


TABLES = {}
TABLES['price_history'] = dataset('price_history', counts('trade_count', 'volume') + nums('value',
    'price_min', 'price_max', 'price_yesterday', 'price_first', 'price_last', 'price_last_change',
    'price_last_change_pct', 'price_close', 'price_close_change', 'price_close_change_pct'))
TABLES['client_type_history'] = dataset('client_type_history', [
    col for side in ('buy', 'sell') for group in ('real', 'legal')
    for col in counts(f'{side}_{group}_count', f'{side}_{group}_volume') + nums(f'{side}_{group}_value')])
TABLES['candlesticks'] = dataset('candlesticks', [Column('candle_type', Integer, nullable=False)] + nums('open', 'high', 'low', 'close') + counts('volume'))
TABLES['transactions'] = dataset('transactions', [Column('row_num', BigInteger, nullable=False),
    Column('canceled', Boolean, nullable=False)] + nums('price') + counts('volume'))
TABLES['shareholders'] = dataset('shareholders', [Column('shareholder_name', Text, nullable=False)] + nums('percentage', 'change') + counts('volume'))
TABLES['symbol_snapshots'] = dataset('symbol_snapshots', nums('price_last', 'price_close', 'value') + counts('volume'))
TABLES['etf_nav'] = dataset('etf_nav', nums('nav_issue', 'nav_value'))
TABLES['index_values'] = dataset('index_values', [Column('index_id', Integer, ForeignKey('indices.id'), nullable=False)] + nums('value', 'change_value', 'change_percent', 'min_value', 'max_value', 'equal_weight', 'equal_weight_change'))
TABLES['tse_options'] = dataset('tse_options', [Column('contract_name', Text), Column('underlying', String(100)), Column('option_type', String(10)), Column('expiry_date', String(10))] + nums('strike_price', 'last_price') + counts('volume', 'open_interest'))
TABLES['codal_announcements'] = dataset('codal_announcements', [Column('title', Text, nullable=False), Column('url', Text, nullable=False), Column('summary', Text)])
for name in ('ime_futures', 'ime_options', 'ime_certificates', 'ime_funds', 'ime_physical'):
    TABLES[name] = dataset(name, [Column('contract_code', String(200)), Column('contract_name', Text),
        Column('underlying', Text), Column('option_type', String(10)), Column('expiry_date', String(10)),
        Column('offer_code', String(100)), Column('currency', String(40)), Column('unit', String(100)),
        Column('value_unit', String(100))] + nums('strike_price', 'last_price', 'nav', 'volume', 'value') + counts('open_interest'))
TABLES['commodities'] = dataset('commodities', [Column('commodity_symbol', String(60), nullable=False),
    Column('commodity_name', String(200)), Column('unit', String(100))] + nums('price', 'change_value', 'change_percent'))

# Version 2: direct-provider acquisition and provenance.
provider_requests = Table('provider_requests', metadata,
    Column('id', BIG, primary_key=True), Column('source', String(40), nullable=False),
    Column('endpoint', String(200), nullable=False, index=True), Column('params', JSON_TYPE, nullable=False),
    Column('status', String(40), nullable=False), Column('http_status', Integer),
    Column('origin', String(255)), Column('format', String(20)), Column('source_hash', String(64)),
    Column('payload', JSON_TYPE), Column('error_kind', String(100)),
    Column('accepted', Integer, default=0), Column('rejected', Integer, default=0),
    Column('fetched_at', DateTime(timezone=True), default=now, nullable=False))
market_observations = Table('market_observations', metadata,
    Column('id', BIG, primary_key=True), Column('natural_key', String(64), nullable=False, unique=True),
    Column('request_id', BIG, ForeignKey('provider_requests.id'), nullable=False),
    Column('source', String(40), nullable=False), Column('endpoint', String(200), nullable=False),
    Column('instrument_code', String(40), index=True), Column('symbol', String(100)),
    Column('date_shamsi', String(10), index=True), Column('time_shamsi', String(8), nullable=False, default=''),
    Column('data_class', String(20), nullable=False), Column('quality', JSON_TYPE, nullable=False),
    Column('raw', JSON_TYPE, nullable=False), Column('recorded_at', DateTime(timezone=True),default=now))

collection_jobs = Table('collection_jobs', metadata,
    Column('id', BIG, primary_key=True), Column('source', String(40), nullable=False),
    Column('scope', String(20), nullable=False), Column('symbols', JSON_TYPE, nullable=False),
    Column('options', JSON_TYPE, nullable=False), Column('status', String(30), nullable=False, index=True),
    Column('last_error', String(150)), Column('created_at', DateTime(timezone=True), default=now, nullable=False),
    Column('updated_at', DateTime(timezone=True), default=now, nullable=False))
collection_tasks = Table('collection_tasks', metadata,
    Column('id', BIG, primary_key=True), Column('job_id', BIG, ForeignKey('collection_jobs.id'), nullable=False,index=True),
    Column('task_key', String(64), nullable=False), Column('kind', String(30), nullable=False),
    Column('endpoint', String(200), nullable=False), Column('symbol', String(100)),
    Column('params', JSON_TYPE, nullable=False), Column('status', String(30), nullable=False,index=True),
    Column('result', JSON_TYPE), Column('error_kind', String(150)), Column('attempts', Integer, nullable=False,default=0),
    Column('updated_at', DateTime(timezone=True), default=now, nullable=False),
    UniqueConstraint('job_id','task_key'))
