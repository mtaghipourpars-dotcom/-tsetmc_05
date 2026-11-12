"""Direct provider archives, observations and provenance."""
from alembic import op
import sqlalchemy as sa
from migrations.schema_v2 import provider_requests, market_observations
revision='0002'
down_revision='0001'
branch_labels=None
depends_on=None
DATASETS=('price_history','client_type_history','candlesticks','transactions','shareholders','symbol_snapshots',
 'etf_nav','index_values','tse_options','codal_announcements','ime_futures','ime_options','ime_certificates',
 'ime_funds','ime_physical','commodities')


def upgrade():
    for name in (*DATASETS,'raw_responses'):
        op.add_column(name,sa.Column('source',sa.String(40),nullable=False,server_default='brsapi'))
    provider_requests.create(op.get_bind())
    market_observations.create(op.get_bind())


def downgrade():
    market_observations.drop(op.get_bind())
    provider_requests.drop(op.get_bind())
    for name in (*DATASETS,'raw_responses'):
        op.drop_column(name,'source')
