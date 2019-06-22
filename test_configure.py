from bcpc_build.build_unit import V8BuildUnitAllocator

if __name__ == '__main__':
    from bcpc_build.build_unit import BuildUnit
    from bcpc_build.db import utils
    from pprint import pprint
    import sqlalchemy as sa
    import sys

    session = utils.Session()
    try:
        id_ = sys.argv[1]
    except IndexError:
        id_ = 'a6fa8c50-2bc3-4282-bd8b-9426b3bb06bb'

    try:
        # This will not have `logger` attribute
        bunit = session.query(BuildUnit).get(id_)
        import logging
        logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)
        bunit.logger = logging.getLogger(__name__)
    except sa.exc.SQLAlchemyError as e:
        sys.exit(e)

    allocator = V8BuildUnitAllocator(session=session)
    # actually ConfigHandler
    #allocator.get_build_config(bunit)
    allocator.configure(bunit)

    #config_handler = V8ConfigHandler(bunit)
    #pprint(dict(config_handler.enumerate_nets()))
