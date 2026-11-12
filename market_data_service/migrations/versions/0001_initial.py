"""Initial immutable schema snapshot."""
from alembic import op
from migrations.schema_v1 import metadata
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    metadata.create_all(op.get_bind(), checkfirst=False)


def downgrade():
    metadata.drop_all(op.get_bind(), checkfirst=False)
