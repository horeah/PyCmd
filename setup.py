from cx_Freeze import setup, Executable
from os.path import dirname
import lib2to3

setup(
    name = 'PyCmd',
    version = '0.8',
    description = 'Smart windows shell',
    executables = [Executable('PyCmd.py')],
    options = {
        'build_exe': {
          'icon': 'PyCmd.ico',
          'include_files': ['example-init.py',
                            'pycmd_public.html',
                            (dirname(lib2to3.__file__), 'lib2to3')],
          'excludes': ['lib2to3'],
        }
    })
