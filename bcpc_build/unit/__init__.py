from abc import ABC
from abc import abstractmethod
from configparser import ConfigParser
from configparser import Error as ConfigParserError
from shutil import copy2
import contextlib
import json
import os.path
import yaml
import warnings


class ConfigurationError(Exception):
    pass


class UnknownConfigFileFormat(Exception):
    pass


class DecodeError(ValueError):
    pass


def ConfigFile(name, filename):
    """Factory for <Type>ConfigFile objects."""
    def _reorder(key):
        key, cls = key

        ext = os.path.splitext(filename)[-1]

        def ext_to_key():
            return ext[1:] if ext.startswith('.') else ext

        if ext_to_key() == key:
            return 0
        return 1

    order = sorted(AVAILABLE_FORMATS, key=_reorder)
    for fmt, cls in order:
        open_fn = cls.get_loader()
        try:
            with open(filename) as f:
                return cls(name, filename, contents=open_fn(f))
        except DecodeError:
            continue

    raise UnknownConfigFileFormat(filename)


def ini_load(fp):
    """Thin wrapper around read_file() for INI files."""
    try:
        parser = ConfigParser()
        parser.read_file(fp)

        def _enum_items(obj):
            for k in obj:
                yield (k, obj[k])

        def to_dict():
            return {
                section: dict(_enum_items(items))
                for section, items in parser.items()
            }

        return to_dict()
    except ConfigParserError as e:
        raise DecodeError(fp) from e


def json_load(fp):
    """Thin wrapper around json.load()."""
    try:
        return json.load(fp)
    except json.decoder.JSONDecodeError as e:
        raise DecodeError(fp) from e


def yaml_load(fp):
    """Thin wrapper around yaml.load()."""
    try:
        obj = yaml.load(fp)
        if obj is None:
            raise DecodeError(fp)
        return obj
    except yaml.parser.ParserError as e:
        raise DecodeError(fp) from e


class _ConfigFile(ABC):
    def __init__(self, name, filename, contents=None):
        self.name = name
        self.filename = filename
        self.refresh(contents)

    @staticmethod
    @abstractmethod
    def get_loader():
        raise NotImplementedError()

    @property
    def contents(self):
        return self._contents

    def refresh(self, contents=None):
        if contents is None:
            # TODO(kmidzi): is copy necessary?
            self._contents = contents.copy()
            return

        try:
            with open(self.filename, 'r') as f:
                loader = self.get_loader()
                self._contents = loader(f)
        except Exception as e:
            raise Exception('Could not initialize contents.') from e

    @contextlib.contextmanager
    def edit(self, backup=False):
        if backup:
            self._backup()
        with self.flush():
            yield self.contents

    def _backup(self, dest=None):
        if dest is None:
            # TODO(kamidzi): naive
            dest = self.filename + '.bak'
        try:
            copy2(self.filename, dest)
        except IOError:
            warnings.warn(
                'Configuration file backup failed - {}.'.format(dest)
            )

    def transform(self, *funcs, flush=False, delayed_flush=True, **kwargs):
        try:
            yield self.contents
            for fn in funcs:
                self._contents = fn(self._contents)
                yield self.contents
                if flush and not delayed_flush:
                    self.flush()
        finally:
            if flush and delayed_flush:
                self.flush()

    @abstractmethod
    def _dump(self, f):
        raise NotImplementedError()

    def _flush(self):
        with open(self.filename, 'w') as f:
            self._dump(f)
            f.flush()

    @contextlib.contextmanager
    def flush(self):
        try:
            yield
        finally:
            self._flush()


class YAMLConfigFile(_ConfigFile):
    @staticmethod
    def get_loader():
        return yaml_load

    def _dump(self, f):
        # This is to ensure proper type conversion when
        # loaded by different language bindings; e.g., ruby
        yaml.dump(self._contents, f, default_style="'")


class JSONConfigFile(_ConfigFile):
    DEFAULT_SPACES = 2

    @staticmethod
    def get_loader():
        return json_load

    def _dump(self, f):
        json.dump(self._contents, f, indent=self.DEFAULT_SPACES)


class INIConfigFile(_ConfigFile):
    @staticmethod
    def get_loader():
        return ini_load

    def _flush(self):
        raise NotImplementedError

    def _dump(self, f):
        raise NotImplementedError


AVAILABLE_FORMATS = [
    ('json', JSONConfigFile),
    ('yaml', YAMLConfigFile),
    ('ini', INIConfigFile),
]


class ConfigHandler(ABC):
    COMPONENTS = ()

    def __init__(self, bunit):
        self.bunit = bunit
        self._build_configs_map()

    def _build_configs_map(self):
        self._configs = {}
        for c in self.COMPONENTS:
            self._configs[c] = ComponentConfigHandler(parent=self, component=c)

    @abstractmethod
    def enumerate_nets(self):
        raise NotImplementedError()

    @property
    def configs(self):
        return self._configs


class ComponentConfigHandler(ConfigHandler):
    """Handles configuration of build component."""

    def __init__(self, component, parent=None):
        self.parent = parent
        self.component = component
        self._config_files = self._gather_config_files(
            self.component, self.parent
        )

    def _gather_config_files(self, component, parent):
        enumerator = COMPONENT_CONFIG_FILE_PATHS.get(component, lambda _: None)
        return {
            key: ConfigFile(key, filename)
            for key, filename in enumerator(parent)
        }

    def enumerate_nets(self):
        if self.parent is None:
            return set()

        _extract_nets = _get_net_extractor(self.component, self.parent)
        yield from set(_extract_nets())

    @property
    def configs(self):
        return self._config_files


def _get_net_extractor(component, parent):
    """Returns the relevant network configuration extractor."""
    enumerator = COMPONENT_CONFIG_FILE_PATHS.get(component, lambda _: None)
    configs = {
        key: ConfigFile(key, filename)
        for key, filename in enumerator(parent)
    }

    def _extract_bcpc_nets():
        filename = 'topology/topology.yml'
        try:
            config = configs[filename].contents
            nodes = config['nodes']

            def _host_nets(host):
                # only get transit interfaces?
                ifaces = host['host_vars']['interfaces']['transit']
                for iface in ifaces:
                    net = iface.get('neighbor', {}).get('name')
                    if net:
                        yield net

            def _all_nets():
                for host in nodes:
                    yield from _host_nets(host)

            yield from _all_nets()
        except KeyError as e:
            raise ConfigurationError(filename) from e

    def _extract_leafy_spines_nets():
        filename = 'hosts.json'
        try:
            config = configs[filename].contents

            def _all_nets():
                for host in config:
                    yield from host['networks']

            yield from _all_nets()
        except KeyError as e:
            raise ConfigurationError(filename) from e

    _mapping = {
        'leafy-spines': _extract_leafy_spines_nets,
        'chef-bcpc': _extract_bcpc_nets,
    }

    return _mapping.get(component, lambda _: [])


def _enumerate_chef_bcpc_config_paths(parent):
    conf_base_dir = os.path.join(parent.bunit.get_build_path(), 'chef-bcpc')
    tops_conf_dir = os.path.join(conf_base_dir, 'virtual/topology')

    def _enum_configs(dirpath, prefix):
        prefix_ = prefix
        for root, dirs, paths in os.walk(dirpath):
            if '.git' in dirs:
                dirs.remove('.git')
            for filename in paths:
                if callable(prefix):
                    prefix_ = prefix(dirpath, root)
                key = os.path.join(prefix_, filename)
                filepath = os.path.join(root, filename)
                yield (key, filepath)

    yield from _enum_configs(tops_conf_dir, 'topology')
    chef_conf_dir = os.path.join(conf_base_dir, 'chef')

    def chef_env_prefix(topdir, current_dir):
        """Calculates the prefix for chef environment subdirectories."""
        suffix = ''
        if current_dir != topdir and current_dir.startswith(topdir):
            suffix = current_dir[len(topdir):]
        return 'chef/environments' + suffix

    chef_prefix_map = dict(
       environments=chef_env_prefix,
       roles='chef/roles'
    )

    for subdir in chef_prefix_map:
        _conf_dir = os.path.join(chef_conf_dir, subdir)
        yield from _enum_configs(_conf_dir, chef_prefix_map[subdir])


def _enumerate_leafy_spines_config_paths(parent):
    path = os.path.join(
        parent.bunit.get_build_path(), 'leafy-spines', 'hosts.json'
    )
    yield ('hosts.json', path)


COMPONENT_CONFIG_FILE_PATHS = {
    'chef-bcpc':  _enumerate_chef_bcpc_config_paths
}


class V8ConfigHandler(ConfigHandler):
    COMPONENTS = ('chef-bcpc',)

    def __init__(self, bunit, *args, **kwargs):
        super().__init__(bunit)

    def enumerate_nets(self):
        nets_map = {
            c: list(self._configs[c].enumerate_nets()) for c in self._configs
        }
        # TODO(kmidzi): should this yield (component, net) instead?
        for k in nets_map:
            yield (k, nets_map[k])
