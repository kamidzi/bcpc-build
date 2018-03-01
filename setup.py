from setuptools import setup, find_packages
# from setuptools.config import read_configuration
# process setup.cfg - for uses like `pip install .`
# Assumes python3
try:
    import configparser
except ImportError:
    import ConfigParser as configparser

setup_args = {}
try:
    config = configparser.ConfigParser()
    config.read('setup.cfg')
    # Need setuptools >=30.3.0 ?
    # config = read_configuration('setup.cfg')
    setup_args = dict(config['metadata'])
except Exception as e:
    import sys
    print('Error reading setup.cfg: %s' % e, file=sys.stderr)

setup_args.update(dict(
    packages=find_packages(),
    # TODO(kmidzi): offload
    entry_points='''
        [console_scripts]
        bcpc-build=bcpc_build.cmd.main:cli
        bcpc-build-unit=bcpc_build.cmd.unit:cli
        bcpc-build-db=bcpc_build.cmd.db:cli
    '''
))


def format_setup_args(conf):
    try:
        conf = conf.copy()
        section = conf['classifiers']
        new_vals = list(filter(None, section.split('\n')))
        conf['classifiers'] = new_vals
    except KeyError:
        pass
    return conf


setup_args = format_setup_args(setup_args)
setup(**setup_args)
