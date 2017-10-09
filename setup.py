from cx_Freeze import setup, Executable
from os.path import dirname
import lib2to3

setup(
    name = 'PyCmd',
    version = '0.9',
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
