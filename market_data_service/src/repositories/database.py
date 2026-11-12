import json
from decimal import Decimal
from sqlalchemy import create_engine, select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sq_insert
from src.repositories.models import metadata


def json_default(value):
    if isinstance(value, Decimal):
        return str(value)  # preserve precision in raw archive
    raise TypeError(type(value).__name__)


def engine_for(url: str):
    kwargs = {'json_serializer': lambda o: json.dumps(o, ensure_ascii=False, default=json_default), 'pool_pre_ping': True}
    if url.startswith('sqlite'):
        kwargs['connect_args'] = {'check_same_thread': False}
        if ':memory:' in url:
            from sqlalchemy.pool import StaticPool
            kwargs['poolclass'] = StaticPool
    engine = create_engine(url, **kwargs)
    if url.startswith('sqlite'):
        from sqlalchemy import event
        @event.listens_for(engine, 'connect')
        def foreign_keys(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
    return engine


def upsert(conn, table, values: dict, keys: list[str]) -> int:
    insert = pg_insert if conn.dialect.name == 'postgresql' else sq_insert
    stmt = insert(table).values(**values)
    updates = {k: getattr(stmt.excluded, k) for k in values if k not in keys and k not in ('id', 'created_at')}
    stmt = stmt.on_conflict_do_update(index_elements=keys, set_=updates)
    return conn.execute(stmt.returning(table.c.id)).scalar_one()


def page(conn, table, conditions=(), limit=100, offset=0):
    query = select(table).where(*conditions)
    total = conn.execute(select(func.count()).select_from(table).where(*conditions)).scalar_one()
    order = [table.c.id.desc()]
    if 'date_shamsi' in table.c:
        order = [table.c.date_shamsi.desc().nullslast(), table.c.time_shamsi.desc(), table.c.id.desc()]
    rows = conn.execute(query.order_by(*order).limit(limit).offset(offset)).mappings().all()
    return {'total': total, 'limit': limit, 'offset': offset, 'items': [dict(r) for r in rows]}
