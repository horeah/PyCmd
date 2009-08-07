from distutils.core import setup
import py2exe

setup(
    console = [
        {
                'script': 'PyCmd.py',
                'icon_resources': [(0, 'PyCmd.ico')]
        }
    ],
)
