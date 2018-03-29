"""Add build state to build unit

Revision ID: 60a3f9fdb580
Revises: c45328521706
Create Date: 2018-03-29 05:27:19.148064+00:00

"""
from alembic import op
import sqlalchemy as sa
import bcpc_build.db.migration_types


# revision identifiers, used by Alembic.
revision = '60a3f9fdb580'
down_revision = 'c45328521706'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('build_unit', schema=None) as batch_op:
        batch_op.add_column(sa.Column('build_state', sa.Enum(
            'provisioned', 'provisioning',
            'configuring', 'configured',
            'building', 'done', 'failed',
            'failed_provision', 'failed_build',
            name='buildstateenum'), nullable=True))


def downgrade():
    with op.batch_alter_table('build_unit', schema=None) as batch_op:
        batch_op.drop_column('build_state')
