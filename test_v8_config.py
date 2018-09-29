import os
import sys
import tempfile

from bcpc_build.build_unit import BuildUnit
from bcpc_build.db import utils
from bcpc_build.unit import V8ConfigHandler
from pprint import pprint
import sqlalchemy as sa


if __name__ == '__main__':
    # Test enumeration
    session = utils.Session()
    id_ = '48d00e2d-8832-40c7-8c13-acfba3b6e671'
    id_ = '40b638b7-5a0a-47c6-99c4-732d296bb34f'
    try:
        bunit = session.query(BuildUnit).get(id_)
    except sa.exc.SQLAlchemyError as e:
        sys.exit(e)

    config_handler = V8ConfigHandler(bunit)
    for comp in config_handler.configs:
        print(comp)
        component_conf = config_handler.configs[comp]
        #pprint(component_conf.configs)
        print(list(config_handler.configs[comp].enumerate_nets()))
