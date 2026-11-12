from contextlib import contextmanager
from threading import Lock
from sqlalchemy import text

_local = Lock()
LOCK_ID = 719304821


class BusyError(Exception):
    pass


@contextmanager
def operation_lock(engine):
    """One outbound pipeline at a time, including CLI and manual sync."""
    if engine.dialect.name == 'postgresql':
        with engine.connect() as conn:
            locked = conn.execute(text('SELECT pg_try_advisory_lock(:id)'), {'id': LOCK_ID}).scalar()
            conn.commit()
            if not locked:
                raise BusyError('Another sync is running')
            try:
                yield
            finally:
                conn.execute(text('SELECT pg_advisory_unlock(:id)'), {'id': LOCK_ID})
                conn.commit()
    else:
        if not _local.acquire(blocking=False):
            raise BusyError('Another sync is running')
        try:
            yield
        finally:
            _local.release()
