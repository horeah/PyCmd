#
# Example init.py for documentation purposes
#
# Use this file as a template/example for creating an
# initialization/configuration script for PyCmd. Scripts are loaded and applied
# based on the following rules:
#
#  * If present, an init.py script in PyCmd's installation directory is
#    automatically executed and defines "global" (system-wide) settings
#
#  * If present, an init.py script in %APPDATA%\PyCmd is automatically executed
#    and defines "user" settings, possibly overriding the "global" ones
#
#  * An additional .py script can be specified using the '-i' switch on the
#    command line to define settings custom to a PyCmd session (possibly
#    overriding the "global" and "user" ones)
#
# This file lists all the configuration options supported by PyCmd, together
# with default values, explanations and various advice. 
#


# An important thing to have in mind: this is a regular Python script that gets
# executed in PyCmd's Python context; therefore, you can do virtually anything
# you want here, like play a song, format your hard-disk or show some custom
# greeting:
print '\n*** Hi, there! ***\n'


# Custom prompt function, see below for comments on appearance.prompt
def git_prompt():
    """
    Custom prompt that displays the name of the current git branch in addition
    to the typical "abbreviated current path" PyCmd prompt.

    Requires git & grep to be present in the PATH.
    """
    # Many common modules (sys, os, subprocess, time, re, ...) are readily
    # shipped with PyCmd, you can directly import them for use in your
    # configuration script. If you need extra modules that are not bundled,
    # manipulate the sys.path so that they can be found (just make sure that the
    # version is compatible with the one used to build PyCmd -- check
    # README.txt)
    import os, subprocess

    # pycmd_public is a collection of utilities that PyCmd "exports" for use
    # within init.py files; you can safely rely on these being maintained
    # throughout following versions. The documentation for this module can be
    # found in pycmd_public.html.
    import pycmd_public
    from pycmd_public import color

    stdout = subprocess.Popen(
        'git branch | grep "^*"', 
        shell=True,
        stdout=subprocess.PIPE,
        stderr=-1).communicate()[0]
    branch_name = stdout.strip(' \n\r*')
    abbrev_path = pycmd_public.abbrev_path(os.getcwd())

    prompt = ''
    if branch_name != '':
        prompt += color.Fore.TOGGLE_BLUE + '[' + branch_name + ']' + color.Fore.DEFAULT + ' '        
    prompt += color.Fore.TOGGLE_BRIGHT + abbrev_path + '> ' + color.Fore.TOGGLE_BRIGHT

    return prompt


# Define a custom prompt function.
#
# This is called by PyCmd whenever a prompt is to be displayed. It should return
# a string to be shown as a prompt.
#
# The default is the typical "abbreviated path" prompt:
#       appearance.prompt = pycmd_public.abbrev_path_prompt
appearance.prompt = git_prompt


# Make PyCmd be "quiet", i.e. skip its welcome and goodbye messages
#
# Note that even if this is set to True, you can still override it using the
# '-q' (quiet) flag on the command line.
#
# The default is False, i.e. the splash messages are shown:
#       behavior.quiet_mode = False
behavior.quiet_mode = False


# Change the way PyCmd handles Tab-completion
# 
# Currently, the only accepted (and, of course, default) value is 'bash', giving
# the typical bash-like completion.
#
behavior.completion_mode = 'bash'
