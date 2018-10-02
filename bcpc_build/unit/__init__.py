from abc import ABC
from abc import abstractmethod
from abc import abstractstaticmethod
import contextlib
import json
import os.path
import yaml


class ConfigurationError(Exception):
    pass


class UnknownConfigFileFormat(Exception):
    pass


class DecodeError(ValueError):
    pass


def ConfigFile(name, filename):
    """Factory for <Type>ConfigFile objects."""
    for fmt, cls in AVAILABLE_FORMATS:
        open_fn = cls.get_loader()
        try:
            with open(filename) as f:
                open_fn(f)
                return cls(name, filename)
        except DecodeError:
            continue

    raise UnknownConfigFileFormat(filename)


def json_load(fp):
    """Thin wrapper around json.load()."""
    try:
        return json.load(fp)
    except json.decoder.JSONDecodeError as e:
        raise DecodeError(fp) from e


def yaml_load(fp):
    """Thin wrapper around yaml.load()."""
    obj = yaml.load(fp)
    if obj is None:
        raise DecodeError(fp)
    return obj


class _ConfigFile(ABC):
    def __init__(self, name, filename):
        self.name = name
        self.filename = filename
        self.refresh()

    @staticmethod
    @abstractmethod
    def get_loader():
        raise NotImplementedError()

    @property
    def contents(self):
        return self._contents

    def refresh(self):
        try:
            with open(self.filename, 'r') as f:
                loader = self.get_loader()
                self._contents = loader(f)
        except Exception as e:
            raise Exception('Could not initialize contents.') from e

    @contextlib.contextmanager
    @abstractmethod
    def edit(self):
        with self.flush():
            yield self.contents

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
    def _flush(self):
        raise NotImplementedError()

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

    @contextlib.contextmanager
    def edit(self):
        with super().edit() as value:
            yield value

    def _flush(self):
        with open(self.filename, 'w') as f:
            yaml.dump(self._contents, f)
            f.flush()


class JSONConfigFile(_ConfigFile):
    DEFAULT_SPACES = 2

    @staticmethod
    def get_loader():
        return json_load

    @contextlib.contextmanager
    def edit(self):
        with super().edit() as value:
            yield value

    def _flush(self):
        with open(self.filename, 'w') as f:
            json.dump(self._contents, f, indent=self.DEFAULT_SPACES)
            f.flush()


AVAILABLE_FORMATS = (('json', JSONConfigFile), ('yaml', YAMLConfigFile))


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
        filename = COMPONENT_CONFIG_FILE_PATHS.get(component, lambda _: None)(
            parent
        )
        key = os.path.basename(filename)
        return {key: ConfigFile(key, filename)}

    def enumerate_nets(self):
        if self.parent is None:
            return set()

        _extract_nets = _get_net_extractor(self.component, self.parent)
        yield from set(_extract_nets())


def _get_net_extractor(component, parent):
    """Returns the relevant network configuration extractor."""
    filename = COMPONENT_CONFIG_FILE_PATHS.get(component, lambda _: None)(
        parent
    )

    def _extract_bcpc_nets():
        try:
            with open(filename) as f:
                config = yaml.load(f)
                try:
                    nodes = config['nodes']

                    def _host_nets(host):
                        host_nets = host['networking']['networks']
                        for net in host_nets:
                            yield net['network']

                    def _all_nets():
                        for host in nodes:
                            yield from _host_nets(host)

                    yield from _all_nets()
                except KeyError as e:
                    raise ConfigurationError(filename) from e
        except OSError as e:
            raise ConfigurationError(filename) from e

    def _extract_leafy_spines_nets():
        try:
            with open(filename) as f:
                config = json.load(f)
                try:

                    def _all_nets():
                        for host in config:
                            yield from host['networks']

                    yield from _all_nets()
                except KeyError as e:
                    raise ConfigurationError(filename) from e
        except OSError as e:
            raise ConfigurationError(filename) from e

    _mapping = {
        'leafy-spines': _extract_leafy_spines_nets,
        'chef-bcpc': _extract_bcpc_nets,
    }

    return _mapping.get(component, lambda _: [])


COMPONENT_CONFIG_FILE_PATHS = {
    'leafy-spines': lambda parent: os.path.join(
        parent.bunit.get_build_path(), 'leafy-spines', 'hosts.json'
    ),
    'chef-bcpc': lambda parent: os.path.join(
        parent.bunit.get_build_path(),
        'chef-bcpc',
        'virtual/topology',
        'topology.yml',
    ),
}


class V8ConfigHandler(ConfigHandler):
    COMPONENTS = ('chef-bcpc', 'leafy-spines')

    def __init__(self, bunit, *args, **kwargs):
        super().__init__(bunit)

    def enumerate_nets(self):
        nets_map = {
            c: list(self._configs[c].enumerate_nets()) for c in self._configs
        }
        # TODO(kmidzi): should this yield (component, net) instead?
        for k in nets_map:
            yield (k, nets_map[k])
