class DuplicateNameError(ValueError):
    def __init__(self, name, message=None):
        self.name = name
        if not message:
            message = 'Duplicate name "%s" exists.' % self.name
        self.message = message
        super().__init__(message)


class AllocationError(RuntimeError):
    pass


class ProvisionError(RuntimeError):
    pass


class ConfigurationError(RuntimeError):
    pass


class BuildError(RuntimeError):
    pass


class SignalException(BuildError):
    def __init__(self, signal, message=None):
        self.signal = signal
        if not message:
            message = 'Build process killed with signal %d' % (-1*signal)
        self.message = message
        super().__init__(message)


class NonZeroExit(BuildError):
    def __init__(self, code, message=None):
        self.code = code
        if not message:
            message = 'Build process exited with status %d' % code
        self.message = message
        super().__init__(message)
