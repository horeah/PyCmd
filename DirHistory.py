import os, sys
from console import get_cursor, move_cursor, get_buffer_size
from sys import stdout
from pycmd_public import appearance, color

class DirHistory:
    """
    Handle a history of visited directories, somewhat similar to a browser
    history.
    """

    # Location and buffer size of the last displayed history
    offset_from_bottom = 0
    disp_size = (0, 0)

    # True if a clean display of the history has been shown (i.e. the following
    # call to display() would actually be an update, not a fresh paint)
    shown = False

    # Maximum allowed length (if the history gets too long it becomes hard to
    # navigate)
    max_len = 9

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

    def jump(self, index):
        """Jump to the specified index (checks whether it's still valid)"""
        if index == 9:
            self.index = len(self.locations) - 1
        elif index > len(self.locations):
            pass
        else:
            self.index = index - 1
        return self._apply()

    def _apply(self):
        """Change to the currently selected directory (checks if still valid)"""
        try:
            os.chdir(self.locations[self.index])
            changed = True
            self.keep = True  # keep saved entries even if no command is executed
        except OSError, error:
            stdout.write('\n  ' + str(error) + '\n')
            self.locations.pop(self.index) 
            self.index -= 1
            if self.index < 0:
                self.index = len(self.locations) - 1
            changed = False
            self.shown = False
        return changed

    def visit_cwd(self):
        """Add the current directory to the history of visited locations"""
        cwd = os.getcwd().decode(sys.getfilesystemencoding())
        if self.locations and cwd == self.locations[self.index]:
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



    def display(self):
        """
        Nicely formatted display of the location history, with current location
        highlighted. If a clean display is present on the screen, this
        overwrites it to perform an 'update'.
        """
        buffer_size = get_buffer_size()

        if self.shown and self.disp_size == buffer_size:
            # We just need to update the previous display, so we
            # go back to the original display start point
            move_cursor(0, buffer_size[1] - self.offset_from_bottom)
        else:
            # We need to redisplay, so remember the start point for
            # future updates
            self.disp_size = buffer_size
            self.offset_from_bottom = buffer_size[1] - get_cursor()[1]

        stdout.write('\n')
        lines_written = 2
        stdout.write(color.Fore.DEFAULT + color.Back.DEFAULT)
        for i in range(len(self.locations)):
            location = self.locations[i]
            prefix = ' %d  ' % (i + 1)
            lines_written += (len(prefix + location) / buffer_size[0] + 1)
            if i != self.index:
                # Non-selected entry, simply print 
                stdout.write(prefix + location + '\n')
            else:
                # Currently selected entry, print with highlight
                stdout.write(appearance.colors.dir_history_selection +
                             prefix +
                             location +
                             color.Fore.DEFAULT +
                             color.Back.DEFAULT)
                stdout.write(' ' * (buffer_size[0] - get_cursor()[0]))

        # Check whether we have overflown the buffer
        if lines_written > self.offset_from_bottom:
            self.offset_from_bottom = lines_written

        # Mark a clean display of the history
        self.shown = True

    def check_overflow(self, line):
        """
        Update the known location of a shown history to account for the
        possibility of overflowing the display buffer.
        """
        (buf_width, buf_height) = get_buffer_size()
        (cur_x, cur_y) = get_cursor()
        lines_written = len(line) / buf_width + 1
        if cur_y + lines_written > buf_height:
            self.offset_from_bottom += cur_y + lines_written - buf_height

