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
