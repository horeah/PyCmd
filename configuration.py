#
# Basic mechanism for customizing PyCmd
#
import os, traceback

class Settings(object):
    """
    Generic settings class; extend this to create a "group" of options
    (accessible as instance members in the settings.py files)
    """
    def sanitize(self):
        """Make sure the settings have sane values"""
        pass

    
class Appearance(Settings):
    """Appearance settings"""

    # Abbreviate current path when displaying the prompt
    abbreviate_prompt = True


class Behavior(Settings):
    """Behavior settings"""
    # Skip splash message (welcome and bye).
    # This can be also overriden with the '-Q' command line argument'
    quiet_mode = False

    # Select the completion mode; currently supported: 'bash'
    completion_mode = 'bash'


    def sanitize(self):
        if not self.completion_mode in ['bash']:
            print 'Invalid setting "' + self.completion_mode + '" for "completion_mode" -- using default "bash"'
            self.completion_mode = 'bash'


def apply_settings(settings_file):
    """
    Execute a configuration file (if it exists), overriding values from the
    specified global_variables dictionary
    """
    if os.path.exists(settings_file):
        try:
            # We initialize the dictionary to readily contain the settings
            # structures; anything else needs to be explicitly imported
            execfile(settings_file, {'appearance': appearance,
                                     'behavior': behavior})
        except Exception, e:
            print 'Error encountered when loading ' + settings_file
            print 'Subsequent settings will NOT be applied!'
            traceback.print_exc()

def sanitize():
    """Sanitize all the configuration instances"""
    appearance.sanitize()
    behavior.sanitize()

# Initialize global configuration instances with default values
#
# These objects are directly manipulated by the settings.py files, executed via
# apply_settings(). Then, they are directly used by PyCmd.py to get the current
# configuration settings
appearance = Appearance()
behavior = Behavior()
