import sys
if sys.platform == 'win32':
    from .console_win32 import *
else:
    from .console_linux import *
    
