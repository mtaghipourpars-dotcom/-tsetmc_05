"""Run on a dedicated empty PostgreSQL database only. Never a production URL."""
import os
from decimal import Decimal
import pytest
from sqlalchemy import text, select
from src.repositories.database import engine_for, upsert
from src.repositories.models import symbols, metadata


@pytest.mark.skipif(not os.getenv('TEST_POSTGRES_URL'), reason='No dedicated PostgreSQL test service available')
def test_postgres_jsonb_upsert_and_advisory_lock():
    engine=engine_for(os.environ['TEST_POSTGRES_URL'])
    # Isolate all tables in a transaction-local temporary schema; roll back at end.
    with engine.connect() as conn:
        tx=conn.begin()
        conn.execute(text('CREATE SCHEMA test_brs_isolated'))
        conn.execute(text('SET LOCAL search_path TO test_brs_isolated'))
        metadata.create_all(conn)
        first=upsert(conn,symbols,{'symbol_l18':'تست','raw':{'amount':Decimal('123456789012345.123456')}},['symbol_l18'])
        second=upsert(conn,symbols,{'symbol_l18':'تست','raw':{'amount':Decimal('123456789012345.123456')}},['symbol_l18'])
        assert first==second
        assert conn.execute(select(symbols.c.raw)).scalar_one()['amount']=='123456789012345.123456'
        assert conn.execute(text('SELECT pg_try_advisory_xact_lock(719304899)')).scalar_one()
        tx.rollback()
    engine.dispose()
