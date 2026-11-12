"""Persistent collection jobs and tasks."""
from alembic import op
from migrations.schema_v3 import collection_jobs, collection_tasks
revision='0003'
down_revision='0002'
branch_labels=None
depends_on=None


def upgrade():
    collection_jobs.create(op.get_bind())
    collection_tasks.create(op.get_bind())


def downgrade():
    collection_tasks.drop(op.get_bind())
    collection_jobs.drop(op.get_bind())
