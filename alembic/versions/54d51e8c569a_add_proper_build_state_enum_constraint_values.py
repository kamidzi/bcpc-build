"""Updates the constraints to reflect proper BuildStateEnum values

Revision ID: 54d51e8c569a
Revises: 60a3f9fdb580
Create Date: 2019-07-18 22:59:35.285374+00:00

"""
from alembic import op
import sqlalchemy as sa
import bcpc_build.db.migration_types


# revision identifiers, used by Alembic.
revision = '54d51e8c569a'
down_revision = '60a3f9fdb580'
branch_labels = None
depends_on = None


# Not written as *bcpc_build.db.migration_types.BuildStateEnum.names(),
# in case something funny has happened with enum names/values
OLD_TYPE = sa.Enum(
    'provisioned', 'provisioning',
    'configuring', 'configured',
    'building', 'done', 'failed',
    'failed_provision', 'failed_build',
    name='buildstateenum'
)

NEW_TYPE = sa.Enum(
    *bcpc_build.db.migration_types.BuildStateEnum.values(),
    validate_strings=True, name='buildstateenum'
)


def upgrade():
    with op.batch_alter_table('build_unit', schema=None) as batch_op:
        batch_op.alter_column(
            'build_state',
            existing_type=OLD_TYPE, type_=NEW_TYPE,
            existing_server_default=True, existing_nullable=True
        )


def downgrade():
    with op.batch_alter_table('build_unit', schema=None) as batch_op:
        batch_op.alter_column(
            'build_state',
            existing_type=NEW_TYPE, type_=OLD_TYPE,
            existing_server_default=True, existing_nullable=True
        )
