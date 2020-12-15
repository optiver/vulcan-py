import shlex
import sys
import subprocess
import shutil
import os
try:
    import setuptools.build_meta
except ImportError:
    pass

class Testing:
    def __init__(self):
        self._pyproject = None

    @property
    def pyproject(self):
        if self._pyproject is None:
            import toml
            self._pyproject = toml.load('pyproject.toml')
        return self._pyproject

    def build_wheel(self, wheel_directory, config_settings=None, metadata_directory=None):
        import setuptools.build_meta
        module_dir = shlex.quote(self.pyproject.get('tool', {}).get('common_py', {}).get('module-dir'))
        if module_dir is not None:
            subprocess.run(f'common_py_builder --module-dir {module_dir}'.split())
        print("CONFIG:", self.pyproject)
        print("INTERP:", sys.executable)
        print("PATH:", sys.path)
        print("SETUPTOOLS:", setuptools)
        print("WHEEL_ARGS:", wheel_directory, config_settings, metadata_directory)
        return setuptools.build_meta.build_wheel(wheel_directory, config_settings, metadata_directory)

    def build_sdist(self, sdist_directory, config_settings=None):
        import setuptools.build_meta
        print("SDIST_ARGS:", sdist_directory, config_settings)
        return setuptools.build_meta.build_sdist(sdist_directory, config_settings)

    @staticmethod
    def get_requires_for_build_wheel(config_settings=None):
        print("GET_REQUIRES_ARGS:", config_settings)
        return ['setuptools', 'wheel >= 0.25', 'common_py', 'toml']

    def prepare_metadata_for_build_wheel(self, metadata_directory, config_settings=None):
        import setuptools.build_meta
        md = setuptools.build_meta.prepare_metadata_for_build_wheel(metadata_directory, config_settings)
        with open(os.path.join(metadata_directory, 'TESTING'), 'w+') as f:
            f.write("PERSON_MAKING_THIS: Joel Christiansen")
        print("PREPARED_METADATA:", md)
        return md



helloworld = Testing()
# helloworld = setuptools.build_meta
