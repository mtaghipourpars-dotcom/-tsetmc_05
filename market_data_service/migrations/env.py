from alembic import context
from src.config.settings import Settings
from src.repositories.database import engine_for
from src.repositories.models import metadata

if context.is_offline_mode():
    context.configure(url=Settings().database_url, target_metadata=metadata, literal_binds=True, dialect_opts={'paramstyle': 'named'})
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = engine_for(Settings().database_url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=metadata)
        with context.begin_transaction():
            context.run_migrations()
