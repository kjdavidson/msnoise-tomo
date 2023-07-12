import glob
import inspect
import os
import platform
import shutil
import subprocess
import sys

import setuptools
from setuptools import Extension, find_packages, setup

from distutils.ccompiler import get_default_compiler
from distutils.command.build import build
from distutils.command.install import install
from distutils.errors import DistutilsSetupError
from distutils.util import change_root

#from obspy.core.util.libnames import _get_lib_name

print(sys.path.pop(0))

# Directory of the current file in the (hopefully) most reliable way
# possible, according to krischer
SETUP_DIRECTORY = os.path.dirname(os.path.abspath(inspect.getfile(
    inspect.currentframe())))

print(SETUP_DIRECTORY)

# check for MSVC
if platform.system() == "Windows" and (
        'msvc' in sys.argv or
        '-c' not in sys.argv and
        get_default_compiler() == 'msvc'):
    IS_MSVC = True
else:
    IS_MSVC = False


# helper function for collecting export symbols from .def files
def export_symbols(*path):
    lines = open(os.path.join(*path), 'r').readlines()[2:]
    return [s.strip() for s in lines if s.strip() != '']

# Use system libraries? Set later...
EXTERNAL_LIBS = False
# adds --with-system-libs command-line option if possible
def add_features():
    if 'setuptools' not in sys.modules or not hasattr(setuptools, 'Feature'):
        return {}

    class ExternalLibFeature(setuptools.Feature):
        def include_in(self, dist):
            global EXTERNAL_LIBS
            EXTERNAL_LIBS = True

        def exclude_from(self, dist):
            global EXTERNAL_LIBS
            EXTERNAL_LIBS = False

    return {
        'system-libs': ExternalLibFeature(
            'use of system C libraries',
            standard=False,
            EXTERNAL_LIBS=True
        )
    }


# monkey patches for MS Visual Studio
if IS_MSVC:
    import distutils
    from distutils.msvc9compiler import MSVCCompiler

    # for Python 2.x only -> support library paths containing spaces
    if distutils.__version__.startswith('2.'):
        def _library_dir_option(self, dir):
            return '/LIBPATH:"%s"' % (dir)

        MSVCCompiler.library_dir_option = _library_dir_option

    # remove 'init' entry in exported symbols
    def _get_export_symbols(self, ext):
        return ext.export_symbols
    from distutils.command.build_ext import build_ext
    build_ext.get_export_symbols = _get_export_symbols
    
#def get_extensions():
#    extensions=[]
    
    # Smoothing Matrix
#    path = ["src"]
#    files = [os.path.join(path, "mk_MatPaths.c"),]
#    kwargs = {}
#   extensions.append(Extension("mk_MatPaths", files, **kwargs))
    


def configuration(parent_package="", top_path=None):
    """
    Config function mainly used to compile C code.
    """
    config = Configuration("", parent_package, top_path)
    extensions = []

    # Smoothing Matrix
    path = "src"
    files = [os.path.join(path, "mk_MatPaths.c"),]
    # compiler specific options
    kwargs = {}
    if IS_MSVC:
        # get export symbols
        kwargs['export_symbols'] = export_symbols(path, 'mk_MatPaths.def')
    #config.add_extension(_get_lib_name("mk_MatPaths", add_extension_suffix=False),
    #                                   files, **kwargs)
    extensions.append(Extension("mk_MatPaths", files, **kwargs))

    # Smoothing Matrix
    path = "src"
    files = [os.path.join(path, "mkMatSmoothing.c"),]
    # compiler specific options
    kwargs = {}
    if IS_MSVC:
        # get export symbols
        kwargs['export_symbols'] = export_symbols(path, 'mkMatSmoothing.def')
    #config.add_extension(_get_lib_name("mkMatSmoothing", add_extension_suffix=False),
    #                                   files, **kwargs)
    extensions.append(Extension("mkMatSmoothing", files, **kwargs))


    # FTAN
    path = "src"
    files = []
    for module in ["configparser.cpp",
                   "fft_NR.cpp",
                   "fta_param.cpp",
                   "libfta.cpp",
                   "readsac.cpp",
                   "vg_fta.cpp"]:
        files.append(os.path.join(path, module))
    # compiler specific options
    kwargs = {}
    if IS_MSVC:
        # get export symbols
        kwargs['export_symbols'] = export_symbols(path, 'vg_fta.def')

    #config.add_extension(_get_lib_name("vg_fta", add_extension_suffix=False), files, **kwargs)
    extensions.append(Extension("vg_fta", files, **kwargs))


    # HACK to avoid: "WARNING: '' not a valid package name; please use only .-separated package names in setup.py"
    config = config.todict()
    config["packages"] = []
    del config["package_dir"]
    return extensions
    return config



def setupPackage():
    setup(
        name='msnoise_tomo',
        version='0.1b',
        packages=find_packages(),
        package_dir={"msnoise_tomo": "msnoise_tomo"},
        package_data={'msnoise_tomo': ['img/*.*']},
        namespace_packages=[],
        include_package_data=True,
        install_requires=['msnoise',
                          'shapely',
                          'pyproj',
                          ],
        entry_points={
            'msnoise.plugins.commands': [
                'tomo = msnoise_tomo.plugin_definition:tomo',
            ],
            'msnoise.plugins.jobtypes': [
                'register = msnoise_tomo.plugin_definition:register_job_types',
            ],
            'msnoise.plugins.table_def': [
                'TomoConfig = msnoise_tomo.tomo_table_def:TomoConfig',
            ],
            'msnoise.plugins.admin_view': [
                'TomoConfigView = msnoise_tomo.plugin_definition:TomoConfigView',
            ],
        },
        author="Thomas Lecocq & MSNoise dev team",
        author_email="Thomas.Lecocq@seismology.be",
        description="A Python Package for Monitoring Seismic Velocity Changes using Ambient Seismic Noise",
        license="EUPL 1.1",
        url="http://www.msnoise.org",
        keywords="",
        extras_require={},
        features=add_features(),
        zip_safe=False,
        ext_package="msnoise_tomo.lib",
        configuration=configuration
    )

if __name__ == "__main__":
    if 'clean' in sys.argv and '--all' in sys.argv:
        print("I'm here!!")
        import shutil
        # delete complete build directory
        path = os.path.join(SETUP_DIRECTORY, 'build')
        try:
            shutil.rmtree(path)
        except:
            pass
        # delete all shared libs from lib directory
        path = os.path.join(SETUP_DIRECTORY, 'msnoise_tomo', 'lib')
        for filename in glob.glob(path + os.sep + '*.pyd'):
            try:
                os.remove(filename)
            except:
                pass
        for filename in glob.glob(path + os.sep + '*.so'):
            try:
                os.remove(filename)
            except:
                pass
    else:
        setupPackage()