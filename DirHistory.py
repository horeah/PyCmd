import sys, os
import configuration
from console import write_str
from console import get_cursor, move_cursor, get_buffer_size, set_cursor_visible
from pycmd_public import color

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
        else:
            self.index = index - 1
        return self._apply()

    def _apply(self):
        """Change to the currently selected directory (checks if still valid)"""
        try:
            os.chdir(self.locations[self.index])
            changed = True
        except OSError, error:
            write_str('\n  ' + str(error) + '\n')
            self.locations.pop(self.index) 
            self.index -= 1
            if self.index < 0:
                self.index = len(self.locations) - 1
            changed = False
            self.shown = False
        return changed

    def visit_cwd(self):
        """Add the current directory to the history of visited locations"""
        self.locations.insert(self.index + 1, os.getcwd().decode(sys.getfilesystemencoding()))
        self.index += 1
        to_remove = [i for i in range(len(self.locations)) 
                     if self.locations[i].lower() == self.locations[self.index].lower()]
        to_remove.remove(self.index)
        self.index -= len(filter(lambda x: x < self.index, to_remove))
        map(lambda x: self.locations.pop(x), to_remove)
        while len(self.locations) > self.max_len:
            # Unusable if it gets too long
            to_remove = (self.index + 8) % len(self.locations)
            self.locations.pop(to_remove)
            if to_remove < self.index:
                self.index -= 1

    def display(self):
        """
        Nicely formatted display of the location history, with current location
        highlighted. If a clean display is present on the screen, this
        overwrites it to perform an 'update'.
        """
        set_cursor_visible(False)
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

        write_str('\n')
        lines_written = 2

        for i in range(len(self.locations)):
            location = self.locations[i]
            prefix = ' %d  ' % (i + 1)
            lines_written += (len(prefix + location) / buffer_size[0] + 1)
            if i != self.index:
                # Non-selected entry, simply print 
                write_str(prefix + location + '\n')
            else:
                # Currently selected entry, print with highlight
                write_str(color.Fore.DEFAULT + color.Back.DEFAULT +
                          configuration.appearance.colors.dir_history_selection +
                          prefix +
                          location +
                          color.Fore.DEFAULT +
                          color.Back.DEFAULT)
                write_str(' ' * (buffer_size[0] - get_cursor()[0]))

        # Check whether we have overflown the buffer
        if lines_written > self.offset_from_bottom:
            self.offset_from_bottom = lines_written

        # Mark a clean display of the history
        self.shown = True
        set_cursor_visible(True)

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

