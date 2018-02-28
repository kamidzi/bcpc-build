from pathlib import Path

USER_CONF_DIRNAME = '.bcpc-build'
USER_CONF_FILENAME = 'config.py'

def get_user_conf_dir():
   return Path.home().joinpath(USER_CONF_DIRNAME).as_posix()

def get_user_conf_file():
   return Path.home().joinpath(get_user_conf_dir(),
                               USER_CONF_FILENAME).as_posix()


userdir = get_user_conf_dir()
db = lambda: None
db.url = 'sqlite:///%s' % Path(userdir).joinpath('master.db').as_posix()

# This file is included as a module, so...
del userdir
