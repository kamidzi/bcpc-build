from __future__ import with_statement
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
from bcpc_build.db.migration_types import UUIDType
from bcpc_build.db.models.build_unit import BuildUnitBase
target_metadata = [BuildUnitBase.metadata]

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# FIXME(kamidzi): rendering NOT working as expected
# https://github.com/kvesteri/sqlalchemy-utils/issues/129#issuecomment-322734082
def render_item(type_, obj, autogen_context):
    """Apply custom rendering for selected items."""

    if type_ == 'type' and isinstance(obj, UUIDType):
        # add import for this type
        autogen_context.imports.add("import uuid")
        return "UUIDType(), default=uuid.uuid4"

    # default rendering for other objects
    return False


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool)

    context_opts = dict(
        target_metadata=target_metadata,
        user_module_prefix='bcpc_build.db.migration_types.',
    )
    if connectable.name == 'sqlite':
        context_opts.update(dict(render_as_batch=True))

    with connectable.connect() as connection:
        context_opts.update(dict(connection=connection))
        context.configure(**context_opts)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
