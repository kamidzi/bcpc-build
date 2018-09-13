from bcpc_build.build_unit import V8BuildUnitAllocator

if __name__ == '__main__':
    from bcpc_build.build_unit import BuildUnit
    from bcpc_build.db import utils
    from pprint import pprint
    import sqlalchemy as sa
    import sys

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
    # actually ConfigHandler
    #allocator.get_build_config(bunit)
    allocator.configure(bunit)

    #config_handler = V8ConfigHandler(bunit)
    #pprint(dict(config_handler.enumerate_nets()))
