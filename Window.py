from console import get_buffer_size, get_viewport, get_cursor, move_cursor, set_cursor_attributes
from console import read_input, erase_to, is_ctrl_pressed, is_alt_pressed
from pycmd_public import color, appearance
from math import log10, ceil
from sys import stdout
from common import fuzzy_match
import sys
from common import debug
if sys.platform == 'linux':
    import pty_control


class Window(object):
    def __init__(self, entries, pattern, width=0, height=0):
        self.all_entries = entries
        self.pattern = pattern
        self.width = width if width else get_buffer_size()[0]
        self.height = height
        self.offset = 0
        self.interactive = False
        self.selected_line = None
        self.selected_column = None
        self.orig_cursor = self.final_cursor = get_cursor()
        self.max_lines = self.num_lines = 0
        self.filter = ''
        if self.height == 0 or self.height > self.num_lines:
            self.height = self.num_lines

        
    @property
    def filter(self):
        return self._filter

    
    @filter.setter
    def filter(self, value):
        self._filter =  ' '.join(value.split())
        if value.endswith(' '):
            self._filter += ' '
        self.entries = [e for e in self.all_entries if fuzzy_match(self.filter, e)]
        
        self.column_width = max([len(e) for e in self.entries]) + 10 if self.entries else 1
        if self.column_width > self.width - 1:
            self.column_width = self.width - 1
        if (len(self.entries) > self.height
            and len(self.entries) > (get_viewport()[3] - get_viewport()[1]) // 4):
            # We print multiple columns to save space
            self.num_columns = (self.width - 1) // self.column_width
        else:
            # We print a single column for clarity
            self.num_columns = 1
            self.column_width = self.width - 1
        self.num_lines = len(self.entries) // self.num_columns
        if len(self.entries) % self.num_columns != 0:
            self.num_lines += 1
        if self.num_lines > self.max_lines:
            self.max_lines = self.num_lines

        if self.selected_line is not None and self.selected_column is not None:
            if self._default_selection_last:
                self.selected_column = self.num_columns - 1
                self.selected_line = self.num_lines - (self.num_lines * self.num_columns - len(self.entries)) - 1
            else:
                self.selected_line = self.selected_column = 0
                self.offset = 0
            self._center_on_selection()


    def display(self):
        def shorten(s):
            half_len = self.width // 2 - 2
            return s if len(s) <= self.width else s[0:half_len] + '\u00b7' * 3 + s[len(s) - half_len:]

        default_color = color.Fore.DEFAULT + color.Back.DEFAULT
        stdout.write('\n')
        set_cursor_attributes(10, False)
        for line in range(self.offset, self.offset + self.height):
            # Print one line
            stdout.write('\r')
            for column in range(0, self.num_columns):
                if line < self.num_lines and line + column * self.num_lines < len(self.entries):
                    s = shorten(self.entries[line + column * self.num_lines])
                    if self.selected_line == line and self.selected_column == column:
                        # Highlight selected line
                        stdout.write(appearance.colors.selection + s + default_color)
                    else:
                        # Print wildcard matches in a different color
                        match = self.pattern.match(s)
                        current_index = 0
                        for i in range(1, match.lastindex + 1):
                            stdout.write(default_color +
                                         appearance.colors.completion_match +
                                         s[current_index : match.start(i)] +
                                         default_color +
                                         s[match.start(i) : match.end(i)])
                            current_index = match.end(i)
                    stdout.write(default_color + ' ' * (self.column_width - len(s)))
                else:
                    stdout.write(default_color + ' ' * (self.column_width))                    
            stdout.write('\n\r')

        if self.height < self.max_lines:
            format_width = int(ceil(log10(self.max_lines)))
            progress = '%*d to %*d of ' % (format_width, self.offset + 1,
                                           format_width, min(self.num_lines, self.offset + self.height))
            rows = '%*d rows' % (format_width, self.num_lines)
            if self.num_lines == 0:
                progress = len(progress) * ' '
            stdout.write(' -- ' + progress + rows + ' --')
            
        if self.interactive:
            stdout.write(appearance.colors.prompt + ' Filter: ' + default_color + self.filter)
            
        erase_to((self.width - 1, get_cursor()[1]))

        if (get_cursor()[1], get_cursor()[0]) > (self.final_cursor[1], self.final_cursor[0]):
            self.final_cursor = get_cursor()
        # correct orig cursor if we have overflown the buffer height
        self.orig_cursor = (self.orig_cursor[0], self.final_cursor[1] - self.height - 1)
            
        set_cursor_attributes(10, True)


    def reset_cursor(self):
        move_cursor(self.orig_cursor[0], self.orig_cursor[1])
    

    def erase(self):
        self.reset_cursor()
        erase_to(self.final_cursor)
        self.reset_cursor()

            
    def interact(self, initial_index=None, default_selection_last=False, can_zap=False):
        self._default_selection_last = default_selection_last
        if initial_index is None:
            initial_index = len(self.entries) - 1 if default_selection_last else 0
        self.interactive = True
        if self.num_lines > 0:
            self.selected_column = initial_index // self.num_lines
            self.selected_line = initial_index % self.num_lines
        else:
            self.selected_column = self.selected_line = 0
        self._center_on_selection()
        while True:
            set_cursor_attributes(10, False)
            self.reset_cursor()
            self.display()
            if sys.platform == 'linux':
                debug('Window interact input_processed.set')
                pty_control.input_processed.set()
            rec = read_input()
            if rec.Char == chr(0) or is_ctrl_pressed(rec) and not rec.VirtualKeyCode == 71 or is_alt_pressed(rec):
                if rec.VirtualKeyCode == 37 or is_ctrl_pressed(rec) and rec.VirtualKeyCode == 66:
                    self.selected_column -= 1
                elif rec.VirtualKeyCode == 39 or is_ctrl_pressed(rec) and rec.VirtualKeyCode == 70:
                    self.selected_column += 1
                elif rec.VirtualKeyCode == 40 or is_ctrl_pressed(rec) and rec.VirtualKeyCode == 78:
                    self.selected_line += 1
                elif rec.VirtualKeyCode == 38 or is_ctrl_pressed(rec) and rec.VirtualKeyCode == 80:
                    self.selected_line -= 1
                elif rec.VirtualKeyCode == 34 or is_ctrl_pressed(rec) and rec.VirtualKeyCode == 86:
                    self.selected_line += self.height
                elif rec.VirtualKeyCode == 33 or is_alt_pressed(rec) and rec.VirtualKeyCode == 86:
                    self.selected_line -= self.height
                elif rec.VirtualKeyCode == 36 or is_ctrl_pressed(rec) and rec.VirtualKeyCode == 65:
                    self.selected_column = 0
                elif rec.VirtualKeyCode == 35 or is_ctrl_pressed(rec) and rec.VirtualKeyCode == 69:
                    self.selected_column = self.num_columns
                elif rec.VirtualKeyCode == 75 and is_ctrl_pressed(rec) and is_alt_pressed(rec) and can_zap:
                    self.erase()
                    return 'zap', self.entries[self.selected_line + self.selected_column * self.num_lines]

                self.selected_line = Window._bound(self.selected_line, 0, self.num_lines - 1)
                num_columns_current_row = self.num_columns
                if self.selected_line + (self.num_columns - 1) * self.num_lines >=  len(self.entries):
                    num_columns_current_row -= 1
                self.selected_column = Window._bound(self.selected_column, 0, num_columns_current_row - 1)
                self._center_on_selection()
            elif (rec.Char == chr(13) or rec.Char == '\t') and self.entries:
                self.erase()
                return 'select', self.entries[self.selected_line + self.selected_column * self.num_lines]
            elif rec.Char == chr(27) or is_ctrl_pressed(rec) and rec.VirtualKeyCode == 71:
                if self.filter:
                    self.filter = ''
                else:
                    self.erase()
                    return None, None
            elif not is_ctrl_pressed(rec) and not is_alt_pressed(rec):
                if rec.Char == '\b':
                    self.filter = self.filter[:-1]
                else:            
                    self.filter += rec.Char

                
    def _center_on_selection(self):
        self.offset = Window._bound(self.offset,
                                    self.selected_line - self.height * 3 // 4,
                                    self.selected_line - self.height // 4)
        self.offset = Window._bound(self.offset, 0, self.num_lines - self.height)

                
    @staticmethod
    def _bound(value, lower, upper):
        return max(min(value, upper), lower)

            
