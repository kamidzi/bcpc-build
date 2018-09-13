from bcpc_build.db.migration_types import BuildStateEnum
import re

def failure_state(estate):
    print(estate.value)
    m = re.match('^failed(:[^ ]+)$', estate.value)
    return m

failed_states = filter(failure_state,
                        BuildStateEnum.__members__.values())
print(list(failed_states))
