1. What is PyCmd?  
-----------------
PyCmd is a 'smart' command prompt extension for Windows' cmd.exe; its purpose is
to emulate a few power features of UNIX shells (decent Tab-completion,
persistent history, etc.)


2. What are some important features?
------------------------------------
 a. Tab completion 
    - when several completions are possible, list them instead of cycling
      through them
    - insert/remove quotes as needed
    - complete executables from the PATH and internal CMD.exe commands
    - complete names of environment variables, including pseudo-variables
    - complete wildcards
    - expand values of environment variables when completing

 b. Command history
    - the history is persistent across PyCmd sessions
    - one can search through the history (type a few filter characters, then 
      Up/Down)
    - reordering is more intuitive than cmd's default strategy

 c. Command editing
    - support emacs key bindings
    - Copy-Paste using the keyboard (Ctrl-C/X/V or Emacs-style)
    - Undo/Redo with Ctrl-(Shift-)Z (regular style) or Ctrl-_ (Emacs-style)
    - dynamic, context-sensitive token expansion with Alt-/ (Emacs-style)
    - smart word-by-word navigation

 d. Other
    - show a highlighted prompt to make the buffer content more readable
    - smart prompt that abbreviates directory names to save screen space
    - Shift-PgUp/PgDn to scroll the buffer
    - history of recently visited directories (Alt-Left/Right/D on empty line)
    - expand ~ as %HOME% or %USERPROFILE%
    - Ctrl-D on an empty line closes PyCmd
    - show the current working directory in the window title


3. Known problems
-----------------
    - pushd/popd are not supported
    - %ERRORLEVEL% is always 0 when executing commands interactively
    - DOSKEY macros are not supported


4. Future plans
---------------
    - add some sort of a configuration mechanism (config file)
    - custom TAB-completion for the arguments of common commands
    - clean-up the mechanism that dispatches commands to cmd.exe (currently kind 
      of hacky)


5. How do I download/install/run it?
------------------------------------   
 a. Download the binary distribution (created with Py2Exe, see 
    http://www.py2exe.org/) from  
          https://sourceforge.net/projects/pycmd/files/
    Then, unpack and start PyCmd.exe. No installation is necessary.

 b. Fetch the Python sources from the repository at
          git://pycmd.git.sourceforge.net/gitroot/pycmd
    then start PyCmd.py in Python or run 'make' to build the binary 
    distribution.
    You will need:
        - Python 2.5 from
                 http://www.python.org/download/releases/2.5/
        - Python for Windows extensions from 
                 https://sourceforge.net/projects/pywin32/
        - py2exe from 
                 http://www.py2exe.org/
        - pefile from   
                 http://code.google.com/p/pefile/
                 NOTE: install with `python setup.py install_lib` 
                       as py2exe won't handle .egg files


6. How do I report a crash/problem?
-----------------------------------
For any kind of bug, please use the bug tracker provided by SourceForge at
  http://sourceforge.net/tracker/?group_id=261720&atid=1127597
When reporting crashes, please try to locate and attach a crash log (look in
%APPDATA%\PyCmd for files named crash-yyyymmdd_hhmmss.log).


7. Credits
----------
   - The fish shell is an endless source of good ideas:
            http://fishshell.org/index.php
   - fsm.py is a nice package for implementing a Finite State Machine:
            http://code.activestate.com/recipes/146262



---------------------------------------------------
Horea Haitonic (h o r e a h _at_ g m a i l . c o m)
