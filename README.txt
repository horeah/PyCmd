1. What is PyCmd?  
-----------------
PyCmd is a front-end for `cmd.exe` (on Windows) and respectively `bash` 
(on Linux/WSL); it brings a powerful, modern and efficient interactive 
experience to classic, ubiquitous shells.


2. What are some important features?
------------------------------------
 a. Tab completion 
    - when several completions are possible, list them (plain/bash- or
      interactive/zsh-style)
    - insert/remove quotes as needed
    - complete executables from the PATH and internal CMD or bash commands
    - complete names of environment variables, including pseudo-variables
    - complete wildcards
    - expand values of environment variables when completing
    - [Windows] support both '/' and '\' as path separators

 b. Command suggestions
    - automatically suggest commands from history or from available
      completions:
        - accept with Right/End
        - accept partially with "forward-word" (Ctrl-Right etc.)
        - accept & run with Ctrl-Enter

 b. Command history
    - the history is persistent across PyCmd sessions
    - direct history search (type a few filter characters/words, then Up/Down)
    - incremental history search (Ctrl-R)
    - remove command from history (Ctrl-Alt-K)
    - history ordering is more intuitive than cmd's default strategy

 c. Command editing
    - support emacs key bindings
    - Copy-Paste using the keyboard (Ctrl-C/X/V or Emacs-style)
    - Undo/Redo with Ctrl-[Shift-]Z (regular style) or Ctrl-_ (Emacs-style)
    - dynamic, context-sensitive token expansion with Alt-/ (Emacs-style)
    - delete to end of line (Ctrl-K) and beginning of line (Ctrl-U)
    - search string ([Shift-]F3)
    - smart word-by-word navigation
    - lexical selection (Shift-Up/Down)

 d. Chat ("AI") mode
    - only enabled if
      - the "chat" variant of the PyCmd distribution has been downloaded/installed
      - `behavior.chat.template` is configured in `init.py` (see `example-init.py`)
    - Ctrl-Alt-I to switch to "chat" mode
    - describe what you want to do, get a suggested command
    - each switch to "chat" mode is a brand new "session"
      - but the inputs are stored in a dedicated history, so it's easy to iterate
    - feel free to experiment with providers, system prompts etc. in your `init.py`

 e. Navigation
    - history of recently visited directories (Alt-Left/Right/D on empty line)
    - cd to parent (Alt-Up)

 f. Other
    - smart prompt:
      - highlighted for readability
      - abbreviates path to save space
      - displays git and svn status
      - displays exit code of last command (if > 0)
      - customizable
    - configuration file (init.py) for customizing colors, prompt etc.
    - Shift-PgUp/PgDn to scroll the buffer
    - expand/abbreviate ~ as %HOME% or %USERPROFILE% [Windows] or $HOME [Linux]
    - Ctrl-D on an empty line closes PyCmd
    - Ctrl-L clears the screen
    - [Windows] show the current working directory in the window title


3. Known problems
-----------------
    a. Windows
      - when DelayedExpansion is disabled (PyCmd.exe /V:OFF), %ERRORLEVEL% is not
        properly processed
      - DOSKEY macros are not supported
      - can NOT be used to fully replace cmd.exe as default shell (e.g. via 
        %COMSPEC%)
    b. Linux
      - keys pressed while a command is running (before the prompt reappears) are lost
      - commands producing copious stdout/stderr run slower
      - setting $PS1 breaks PyCmd


4. Future plans
---------------
    - custom TAB-completion for the arguments of common commands
    - [Windows] clean-up the mechanism that dispatches commands to cmd.exe (currently kind 
      of hacky)
    - [Linux] clean-up the mechanism that dispatches commands to bash


5. How do I download/install/run it?
------------------------------------   
 a. Download a standalone binary distribution from 
          https://github.com/horeah/PyCmd/releases
    Then, unpack and start PyCmd.exe. No installation is necessary.

 b. Download and install a wheel distribution from 
          https://github.com/horeah/PyCmd/releases
    Then run `pip install Pycmd-<version>.whl` to install (this will also create
    a starter script/executable). 
    
 c. Clone the repository and run/build directly with Python (>=3.10):
       (1) `pip install -r requirements.txt` to install dependencies
       (2) `python run_tests.py` to run tests
       (3) `python PyCmd.py` to start the application
       (4) `make` to build the binary distributions


6. How do I report a crash/problem?
-----------------------------------
For bugs or feature requests, please use the bug tracker provided by GitHub
at https://github.com/horeah/PyCmd/issues

When reporting crashes, please try to locate and attach a crash log (look in
%APPDATA%\PyCmd for files named crash-yyyymmdd_hhmmss.log).


7. Credits
----------
   - The fish shell is an endless source of good ideas:
            https://fishshell.com/
   - fsm.py is a nice package for implementing a Finite State Machine:
            http://code.activestate.com/recipes/146262


---------------------------------------------------
Horea Haitonic (h o r e a h _at_ g m a i l . c o m)
---------------------------------------------------

