1. What is PyCmd?  

PyCmd is a 'smart' command prompt extension for Windows' cmd.exe; its purpose is
to emulate a few power features of UNIX shells (decent Tab-completion,
persistent history, etc.)


2. What are some important features?

 a. Tab completion 
    - when several completions are possible, list them instead of cycling
      through them
    - insert/remove quotes as needed
    - complete executables from the PATH and internal CMD.exe commands
    - complete names of environment variables, including pseudo-variables
    - expand values of environment variables when completing

 b. Command history
    - the history is persistent across PyCmd sessions
    - one can search through the history (type a few filter characters, then 
      Up/Down)
    - reordering is more intuitive than cmd's default strategy

 c. Other
    - show a highlighted prompt to make the buffer content more readable
    - smart prompt that abbreviates directory names to save screen space
    - Shift-PgUp/PgDn to scroll the buffer
    - Copy-paste using the keyboard (Ctrl-C/X/V or Emacs-style)
    - History of recently visited directories (Alt-Left/Right/D on empty line)
    - expand ~ as %HOME% or %USERPROFILE%
    - support emacs key bindings
    - Ctrl-D on an empty line closes PyCmd
    - show the current working directory in the window title


3. Any known problems?

    - pushd/popd are not supported
    - escaping characters via ^ doesn't work
    - %ERRORLEVEL% is always 0


4. Future plans?

    - add some sort of a configuration mechanism (config file)
    - custom TAB-completion for the arguments of common commands
    - clean-up the mechanism that dispatches commands to cmd.exe (currently kind 
      of hacky)
    - support ANSI colors (e.g. for MinGW utilities)


4. How do I download/install/run it?
   
 a. Download the binary distribution (created with Py2Exe, see 
    http://www.py2exe.org/) from  
          https://sourceforge.net/project/showfiles.php?group_id=261720
    Then, unpack and start PyCmd.exe. No installation is necessary.

 b. Fetch the Python sources from the repository at
          https://pycmd.svn.sourceforge.net/svnroot/pycmd
    then start trunk/PyCmd.py in Python.

