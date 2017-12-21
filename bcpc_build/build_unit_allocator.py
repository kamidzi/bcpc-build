import os

DEFAULT_BUILD_HOME = '/build'


class BuildUnitAllocator(object):
    BUILD_DIR_PREFIX = 'chef-bcpc.'

    def init(self, *args, **kwargs):
        self._conf = kwargs.get('conf', {})
        self._conf.setdefault('build_home', DEFAULT_BUILD_HOME)

    @property
    def conf(self):
        return self._conf

    # TODO(kamidzi): temporary???
    def list_build_areas(self):
        # TODO(kmidzi): should this return [] ???
        try:
            return os.listdir(self.conf.get('build_home'))
        except FileNotFoundError as e:
            return []

    def allocate_build_dir(self, *args, **kwargs):
        """Allocates a Build Unit data directory"""
        dirs = self.list_build_areas()

        # get the suffixes
        def split_suffix(x):
            return int(x.split('.')[-1])

        latest = 0 if not dirs else max(map(split_suffix, dirs))
        new_id = latest + 1
        return os.path.join(self.conf.get('build_home'),
                            self.BUILD_DIR_PREFIX + str(new_id))
