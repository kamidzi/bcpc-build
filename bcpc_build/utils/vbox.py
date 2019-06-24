import shlex
import sys
from subprocess import check_output


class NoSuchPropertyError(ValueError):
    pass


VBOX_SYSTEM_PROPERTIES = None
verinfo = sys.version_info


# vboxapi only *properly* supported with python3.5 on xenial
def _init_vbox_sysprops_from_system():
    global VBOX_SYSTEM_PROPERTIES
    cmd = 'VBoxManage list systemproperties'
    try:
        out = check_output(shlex.split(cmd))
        props = filter(None, out.decode('utf-8').split('\n'))

        def _normalize_key(x):
            return x.replace(' ', '_').lower()

        def _extract_kv(line):
            key, value = line.split(':')
            return (_normalize_key(key), value.strip())

        VBOX_SYSTEM_PROPERTIES = dict(map(_extract_kv, props))
    except Exception as e:
        raise RuntimeError(
            'Failed to enumerate Virtualbox System Properties'
        ) from e


if not (verinfo.major == 3 and verinfo.minor == 5):
    _init_vbox_sysprops = _init_vbox_sysprops_from_system
else:
    import virtualbox
    # see %VBOX_SDK_PATH%/bindings/xpcom/python/xpcom/vboxxpcom.py for why...
    try:
        import xpcom
        _prop_exc = (xpcom.Exception,)
    except ImportError:
        _prop_exc = (Exception,)

    def _init_vbox_sysprops_from_vboxapi():
        global VBOX_SYSTEM_PROPERTIES
        _sysprops = virtualbox.VirtualBox().system_properties
        _sysprop_keys = list(filter(
            lambda x: not x.startswith('_'), dir(_sysprops)
        ))

        def _extract_prop_kv(key):
            try:
                return (key, getattr(_sysprops, key))
            except _prop_exc:
                # throw Warning?
                pass

        VBOX_SYSTEM_PROPERTIES = dict(
            filter(None, map(_extract_prop_kv, _sysprop_keys))
        )
    _init_vbox_sysprops = _init_vbox_sysprops_from_vboxapi


def get_vbox_sysprop(key, refresh=False):
    global VBOX_SYSTEM_PROPERTIES
    if VBOX_SYSTEM_PROPERTIES is None or refresh:
        _init_vbox_sysprops()
    try:
        return VBOX_SYSTEM_PROPERTIES[key]
    except KeyError as e:
        raise NoSuchPropertyError(key) from e
