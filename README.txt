1. What is PyCmd?  
-----------------
PyCmd is a 'smart' command prompt extension for Windows' cmd.exe; its purpose is
to emulate a few power features of UNIX shells (decent Tab-completion,
persistent history, etc.)


2. What are some important features?
------------------------------------
 a. Tab completion 
    - when several completions are possible, list them (plain/bash- or
      interactive/zsh-style)
    - insert/remove quotes as needed
    - complete executables from the PATH and internal CMD.exe commands
    - complete names of environment variables, including pseudo-variables
    - complete wildcards
    - expand values of environment variables when completing
    - support both '/' and '\' as path separators

 b. Command history
    - the history is persistent across PyCmd sessions
    - one can search through the history (type a few filter characters/words,
      then Up/Down)
    - reordering is more intuitive than cmd's default strategy

 c. Command editing
    - support emacs key bindings
    - Copy-Paste using the keyboard (Ctrl-C/X/V or Emacs-style)
    - Undo/Redo with Ctrl-[Shift-]Z (regular style) or Ctrl-_ (Emacs-style)
    - dynamic, context-sensitive token expansion with Alt-/ (Emacs-style)
    - search string ([Shift-]F3)
    - smart word-by-word navigation
    - lexical selection (Shift-Up/Down)

 d. Navigation
    - history of recently visited directories (Alt-Left/Right/D on empty line)
    - cd to parent (Alt-Up)

 e. Other
    - smart prompt:
      - highlighted for readability
      - abbreviates path to save space
      - displays git and svn status
      - customizable
    - configuration file (init.py) for customizing colors, prompt etc.
    - Shift-PgUp/PgDn to scroll the buffer
    - expand ~ as %HOME% or %USERPROFILE%
    - Ctrl-D on an empty line closes PyCmd
    - show the current working directory in the window title


3. Known problems
-----------------
    - pushd/popd are not supported
    - %ERRORLEVEL% is always 0 when executing commands interactively
    - DOSKEY macros are not supported
    - can NOT be used to fully replace cmd.exe as default shell (e.g. via 
      %COMSPEC%)


4. Future plans
---------------
    - custom TAB-completion for the arguments of common commands
    - clean-up the mechanism that dispatches commands to cmd.exe (currently kind 
      of hacky)


5. How do I download/install/run it?
------------------------------------   
 a. Download the binary distribution (created with cx_freeze, see 
    http://cx-freeze.sourceforge.net/) from
          https://sourceforge.net/projects/pycmd/files/
    Then, unpack and start PyCmd.exe. No installation is necessary.

 b. Fetch the Python sources from the repository at
          git://pycmd.git.sourceforge.net/gitroot/pycmd
    then start PyCmd.py in Python or run 'make' to build the binary 
    distribution.
    You will need:
        - Python 2.7 from
                 http://www.python.org/download/releases/2.7/
        - Python for Windows extensions from 
                 https://sourceforge.net/projects/pywin32/
        - pefile from   
                 http://code.google.com/p/pefile/
    If you want to build (make), you'll also need:
        - cx_freeze from 
                 http://cx-freeze.sourceforge.net/
        - MinGW from
                 http://www.mingw.org/ 


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
