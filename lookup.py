from bcpc_build.db import utils
from bcpc_build.build_unit import BuildUnit


id = 'i'
session = utils.Session()
x = session.query(BuildUnit).get(id)
print(x)
