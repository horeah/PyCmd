from console import get_buffer_size, get_viewport, get_cursor, move_cursor, set_cursor_attributes, read_input, erase_to
from pycmd_public import color, appearance
from math import log10, ceil
from sys import stdout
from common import fuzzy_match


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
        self._filter = value
        self.entries = [e for e in self.all_entries if fuzzy_match(self.filter, e)]
        
        self.column_width = max([len(e) for e in self.entries]) + 10 if self.entries else 1
        if self.column_width > self.width - 1:
            self.column_width = self.width - 1
        if (len(self.entries) > self.height
            and len(self.entries) > (get_viewport()[3] - get_viewport()[1]) / 4):
            # We print multiple columns to save space
            self.num_columns = (self.width - 1) / self.column_width
        else:
            # We print a single column for clarity
            self.num_columns = 1
            self.column_width = self.width - 1
        self.num_lines = len(self.entries) / self.num_columns
        if len(self.entries) % self.num_columns != 0:
            self.num_lines += 1
        if self.num_lines > self.max_lines:
            self.max_lines = self.num_lines

        if self.selected_line >= 0 and self.selected_column >= 0:
            self.selected_line = self.selected_column = 0
            self.offset = 0


    def display(self):
        default_color = color.Fore.DEFAULT + color.Back.DEFAULT
        stdout.write('\n')
        set_cursor_attributes(10, False)
        for line in range(self.offset, self.offset + self.height):
            # Print one line
            stdout.write('\r')
            for column in range(0, self.num_columns):
                if line < self.num_lines and line + column * self.num_lines < len(self.entries):
                    s = self.entries[line + column * self.num_lines]
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
            stdout.write('\n')

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

            
    def interact(self):
        self.interactive = True
        self.selected_line = 0
        self.selected_column = 0
        while True:
            set_cursor_attributes(10, False)
            self.reset_cursor()
            self.display()
            rec = read_input()
            if rec.Char == chr(0):
                if rec.VirtualKeyCode == 37:
                    self.selected_column -= 1
                elif rec.VirtualKeyCode == 39:
                    self.selected_column += 1
                elif rec.VirtualKeyCode == 40:
                    self.selected_line += 1
                elif rec.VirtualKeyCode == 38:
                    self.selected_line -= 1
                elif rec.VirtualKeyCode == 34:
                    self.selected_line += self.height
                elif rec.VirtualKeyCode == 33:
                    self.selected_line -= self.height
                elif rec.VirtualKeyCode == 36:
                    self.selected_column = 0
                elif rec.VirtualKeyCode == 35:
                    self.selected_column = self.num_columns

                self.selected_line = Window._bound(self.selected_line, 0, self.num_lines - 1)
                num_columns_current_row = self.num_columns
                if self.selected_line + (self.num_columns - 1) * self.num_lines >=  len(self.entries):
                    num_columns_current_row -= 1
                self.selected_column = Window._bound(self.selected_column, 0, num_columns_current_row - 1)
                self.offset = Window._bound(self.offset, self.selected_line - self.height + 1, self.selected_line)
                
            elif rec.Char == chr(13) or rec.Char == '\t':
                self.erase()
                return self.entries[self.selected_line + self.selected_column * self.num_lines]
            elif rec.Char == chr(27):
                if self.filter:
                    self.filter = ''
                else:
                    self.erase()
                    return None
            elif rec.Char.isalnum() or rec.Char == ' ':
                self.filter += rec.Char
            elif rec.Char == '\b':
                self.filter = self.filter[:-1]

                
    @staticmethod
    def _bound(value, lower, upper):
        return max(min(value, upper), lower)
            
