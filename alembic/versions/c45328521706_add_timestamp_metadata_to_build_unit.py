"""Add timestamp metadata to build unit.

Revision ID: c45328521706
Revises: 028688a5e692
Create Date: 2018-03-14 21:01:10.174786+00:00

"""
from alembic import op
from datetime import datetime
import sqlalchemy as sa
import bcpc_build.db.migration_types


utcnow = datetime.utcnow
# revision identifiers, used by Alembic.
revision = 'c45328521706'
down_revision = '028688a5e692'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('build_unit', sa.Column('created_at',
        sa.TIMESTAMP(timezone=True), nullable=True, default=utcnow))
    op.add_column('build_unit', sa.Column('updated_at',
        sa.TIMESTAMP(timezone=True), nullable=True, default=utcnow,
        onupdate=utcnow))

def downgrade():
    with op.batch_alter_table('build_unit') as batch_op:
        batch_op.drop_column('updated_at')
        batch_op.drop_column('created_at')
