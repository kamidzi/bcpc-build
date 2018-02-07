"""Create build_unit table

Revision ID: 80d8b75adb7e
Revises:
Create Date: 2018-02-07 17:23:07.788198+00:00

"""
from alembic import op
import sqlalchemy as sa
from bcpc_build.db.types import GUID


# revision identifiers, used by Alembic.
revision = '80d8b75adb7e'
down_revision = None
branch_labels = None
depends_on = None


TABLE_NAME = 'build_unit'
def upgrade():
    op.create_table(
        TABLE_NAME,
        sa.Column('id', GUID, primary_key=True),
        sa.Column('build_dir', sa.Unicode(200), nullable=False),
        sa.Column('build_user', sa.Unicode(64), nullable=False),
        sa.Column('description', sa.Unicode(200)),
        sa.Column('name', sa.Unicode(128), nullable=False),
        sa.Column('source_url', sa.Unicode(200), nullable=False)
    )

def downgrade():
    op.drop_table(TABLE_NAME)
