import sys, os
from console import set_text_attributes, get_text_attributes
from console import BACKGROUND_BRIGHT, FOREGROUND_BRIGHT

class DirHistory:
    """
    Handle a history of visited directories, somewhat similar to a browser
    history.
    """

    def __init__(self):
        """Create an empty directory history"""
        self.locations = []
        self.index = -1

    def go_left(self):
        """Go to the previous location (checks whether it's still valid)"""
        self.index -= 1
        if self.index < 0:
            self.index = len(self.locations) - 1
        try:
            os.chdir(self.locations[self.index])
            changed = True
        except OSError, error:
            sys.stdout.write('\n  ' + str(error) + '\n')
            self.locations.pop(self.index) 
            changed = False
        return changed

    def go_right(self):
        """Go to the next location (checks whether it's still valid)"""
        self.index += 1
        if self.index >= len(self.locations):
            self.index = 0
        try:
            os.chdir(self.locations[self.index])
            changed = True
        except OSError, error:
            sys.stdout.write('\n  ' + str(error) + '\n')
            self.locations.pop(self.index) 
            self.index -= 1
            changed = False
        return changed

    def visit_cwd(self):
        """Add the current directory to the history of visited locations"""
        self.locations.insert(self.index + 1, os.getcwd())
        self.index += 1
        to_remove = [i for i in range(len(self.locations)) 
                     if self.locations[i].lower() == self.locations[self.index].lower()]
        to_remove.remove(self.index)
        self.index -= len(filter(lambda x: x < self.index, to_remove))
        map(lambda x: self.locations.pop(x), to_remove)
        while len(self.locations) > 16:
            # Unusable if it gets too long
            to_remove = (self.index + 8) % len(self.locations)
            self.locations.pop(to_remove)
            if to_remove < self.index:
                self.index -= 1

    def display(self):
        """
        Nicely formatted display of the location history.
        The current location is highlighted.
        """
        orig_attr = get_text_attributes()
        set_text_attributes(orig_attr)
        sys.stdout.write('\n')
        map(sys.stdout.write, ['  ' + d + '\n' for d in self.locations[: self.index]])
        sys.stdout.write('  ')
        set_text_attributes(orig_attr ^ BACKGROUND_BRIGHT ^ FOREGROUND_BRIGHT)
        sys.stdout.write(self.locations[self.index])
        set_text_attributes(orig_attr)
        sys.stdout.write('\n')
        map(sys.stdout.write, ['  ' + d + '\n' for d in self.locations[self.index + 1 :]])


