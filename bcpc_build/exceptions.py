class AllocationError(Exception):
    _MESSAGE = 'Error allocating build area. Existing areas: %s'
    # TODO(kmidzi): careful about length of _areas_

    def __init__(self, areas):
        message = self._MESSAGE % areas
        super(AllocationError, self).__init__(message)
