from cx_Freeze import setup, Executable
from os.path import dirname
import lib2to3
from buildinfo import build_date

setup(
    name = 'PyCmd',
    version = build_date[:4] + '.' + build_date[4:6] + '.' + build_date[6:],
    description = 'Smart windows shell',
    executables = [Executable(script='PyCmd.py',
                              icon='PyCmd.ico')],
    options = {
        'build_exe': {
            'include_files': ['example-init.py',
                              'pycmd_public.html',
                              (dirname(lib2to3.__file__), 'lib2to3')],
            'excludes': ['lib2to3', 'Tkinter', 'Tk', 'Tcl', 'test'],
        }
    })
