import os, sys
from console import get_cursor, move_cursor, get_buffer_size
from sys import stdout
from pycmd_public import appearance, color

class DirHistory:
    """
    Handle a history of visited directories, somewhat similar to a browser
    history.
    """

    # Maximum allowed length (if the history gets too long it becomes hard to
    # navigate)
    max_len = 30

    def __init__(self):
        """Create an empty directory history"""
        self.locations = []
        self.index = -1
        self.keep = True

    def go_left(self):
        """Go to the previous location (checks whether it's still valid)"""
        self.index -= 1
        if self.index < 0:
            self.index = len(self.locations) - 1
        return self._apply()

    def go_right(self):
        """Go to the next location (checks whether it's still valid)"""
        self.index += 1
        if self.index >= len(self.locations):
            self.index = 0
        return self._apply()

    def jump(self, location):
        """Jump to the specified location (this must be an actual entry from the locations list!)"""
        self.index = self.locations.index(location)
        return self._apply()

    def _apply(self):
        """Change to the currently selected directory (checks if still valid)"""
        try:
            os.chdir(self.locations[self.index])
            self.keep = True  # keep saved entries even if no command is executed
        except OSError as error:
            stdout.write('\n  ' + str(error) + '\n')
            self.locations.pop(self.index) 
            self.index -= 1
            if self.index < 0:
                self.index = len(self.locations) - 1
            self.shown = False
        return

    def visit_cwd(self):
        """Add the current directory to the history of visited locations"""
        cwd = os.getcwd()
        if self.locations and cwd.lower() == self.locations[self.index].lower():
            return

        if self.keep:
            # some command has actually executed here, keep this location
            self.locations.insert(self.index + 1, cwd)
            self.index += 1
        else:
            # discard current location, we were just passing by
            self.locations[self.index] = cwd

        # by default we don't keep a new location, if a command is executed here at
        # a later time the flag will be marked True then
        self.keep = False

        # remove duplicates
        self.locations = ([l for l in self.locations[:self.index] if l.lower() != cwd.lower()]
                          + [cwd]
                          + [l for l in self.locations[self.index + 1:] if l.lower() != cwd.lower()])
        self.index = self.locations.index(cwd)

        # rotate the history so that the current directory is last
        self.locations = self.locations[self.index + 1:] + self.locations[:self.index + 1]

        # shorten
        self.locations = self.locations[-self.max_len:]
        self.index = len(self.locations) - 1
