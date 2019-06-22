from itertools import chain
import logging
import sys

from furl import furl
from pprint import pprint
import sqlalchemy as sa

from bcpc_build.build_unit import V8BuildUnitAllocator
from bcpc_build.build_unit import BuildUnit
from bcpc_build.db import utils


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
logger = logging.getLogger(__name__)

bunit = lambda _: None
bunit.build_user = 'build_user'


if __name__ == '__main__':
    session = utils.Session()
    id_ = '48d00e2d-8832-40c7-8c13-acfba3b6e671'
    id_ = '40b638b7-5a0a-47c6-99c4-732d296bb34f'
    try:
        # This will not have `logger` attribute
        bunit = session.query(BuildUnit).get(id_)
        import logging
        bunit.logger = logging.getLogger(__name__)
    except sa.exc.SQLAlchemyError as e:
        sys.exit(e)

    allocator = V8BuildUnitAllocator(session=session)
    allocator.provision(bunit)
