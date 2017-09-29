from CommandHistory import CommandHistory
from common import fuzzy_match, word_sep
import win32clipboard as wclip

EXTEND_SEPARATORS_OUTSIDE_QUOTES = \
    ['-', '.', '=', '\\', ';', ' ', '>', '<', '&', '|', '\0']
EXTEND_SEPARATORS_INSIDE_QUOTES = ['-', ' ', '.', '&', '|', '\\', '"']

class ActionCode:
    """
    Enum-like class that defines codes for input manipulation actions
    """
    ACTION_none = 0
    ACTION_LEFT = 1
    ACTION_RIGHT = 2
    ACTION_LEFT_WORD = 3
    ACTION_RIGHT_WORD = 4
    ACTION_HOME = 5
    ACTION_END = 6
    ACTION_COPY = 7
    ACTION_CUT = 8
    ACTION_PASTE = 9
    ACTION_PREV = 10
    ACTION_NEXT = 11
    ACTION_INSERT = 12
    ACTION_COMPLETE = 13
    ACTION_DELETE = 14
    ACTION_DELETE_WORD = 15
    ACTION_BACKSPACE = 16
    ACTION_BACKSPACE_WORD = 17
    ACTION_KILL_EOL = 18
    ACTION_ESCAPE = 19
    ACTION_UNDO = 20
    ACTION_REDO = 21
    ACTION_UNDO_EMACS = 22
    ACTION_EXPAND = 23
    ACTION_TOGGLE_OVERWRITE = 24
    ACTION_SEARCH_RIGHT = 25
    ACTION_SEARCH_LEFT = 26
    ACTION_SELECT_UP = 27
    ACTION_SELECT_DOWN = 28


class InputState:
    """
    Handles the current state of the input line:
        * user input chars
        * displaying the prompt and command line
        * handling text selection and Cut/Copy/Paste
        * the command history
        * dynamic expansion based on the input history
    """

    def __init__(self):
        # Current state of the input line
        self.prompt = ''
        self.before_cursor = ''
        self.after_cursor = ''

        # Previous state of the input line
        self.prev_prompt = ''
        self.prev_before_cursor = ''
        self.prev_after_cursor = ''

        # Some error needs to be notified with a bell
        self.bell = False

        # Typing overwrite mode
        self.overwrite = False

        # Command history
        self.history = CommandHistory()

        # Text selection
        self.selection_start = 0

        # Previous line, stub and list of matches for the dynamic expansion
        self.expand_line = ''
        self.expand_stub = ''
        self.expand_matches = []

        # Line history for undo/redo - (before_cursor, after_cursor) pairs
        self.undo = []
        self.redo = []
        self.undo_emacs = []
        self.undo_emacs_index = -1
        self.last_action = ActionCode.ACTION_none

        # Selection history for extend/shrink selection (before_cursor, after_cursor, selection_start, extend_separators) tuple
        self.selection_history = []

        # Search string
        self.search_substr = None
        self.search_rev = False

        # List of delimiters for the "extend-selection" feature
        self.extend_separators = None

        # Action handlers
        self.handlers = {
            ActionCode.ACTION_none: None,
            ActionCode.ACTION_LEFT: self.key_left,
            ActionCode.ACTION_RIGHT: self.key_right,
            ActionCode.ACTION_LEFT_WORD: self.key_left_word,
            ActionCode.ACTION_RIGHT_WORD: self.key_right_word,
            ActionCode.ACTION_HOME: self.key_home,
            ActionCode.ACTION_END: self.key_end,
            ActionCode.ACTION_SEARCH_RIGHT: self.key_search_right,
            ActionCode.ACTION_SEARCH_LEFT: self.key_search_left,
            ActionCode.ACTION_SELECT_UP: self.key_extend_selection,
            ActionCode.ACTION_SELECT_DOWN: self.key_shrink_selection,
            ActionCode.ACTION_COPY: self.key_copy,
            ActionCode.ACTION_CUT: self.key_cut,
            ActionCode.ACTION_PASTE: self.key_paste,
            ActionCode.ACTION_PREV: self.key_up,
            ActionCode.ACTION_NEXT: self.key_down,
            ActionCode.ACTION_INSERT: self.key_insert,
            ActionCode.ACTION_COMPLETE: self.key_complete,
            ActionCode.ACTION_DELETE: self.key_del,
            ActionCode.ACTION_DELETE_WORD: self.key_del_word,
            ActionCode.ACTION_BACKSPACE: self.key_backspace,
            ActionCode.ACTION_BACKSPACE_WORD: self.key_backspace_word,
            ActionCode.ACTION_KILL_EOL: self.key_kill_line,
            ActionCode.ACTION_ESCAPE: self.key_esc,
            ActionCode.ACTION_UNDO: self.key_undo,
            ActionCode.ACTION_REDO: self.key_redo,
            ActionCode.ACTION_UNDO_EMACS: self.key_undo_emacs,
            ActionCode.ACTION_EXPAND: self.key_expand,
            ActionCode.ACTION_TOGGLE_OVERWRITE: self.key_toggle_overwrite, }

        # Action categories
        self.insert_actions = [ActionCode.ACTION_INSERT,
                               ActionCode.ACTION_COMPLETE,
                               ActionCode.ACTION_EXPAND]
        self.delete_actions = [ActionCode.ACTION_DELETE,
                               ActionCode.ACTION_DELETE_WORD,
                               ActionCode.ACTION_BACKSPACE,
                               ActionCode.ACTION_BACKSPACE_WORD,
                               ActionCode.ACTION_KILL_EOL]
        self.navigate_actions = [ActionCode.ACTION_LEFT,
                                 ActionCode.ACTION_LEFT_WORD,
                                 ActionCode.ACTION_RIGHT,
                                 ActionCode.ACTION_RIGHT_WORD,
                                 ActionCode.ACTION_HOME,
                                 ActionCode.ACTION_END,
                                 ActionCode.ACTION_SEARCH_RIGHT,
                                 ActionCode.ACTION_SEARCH_LEFT,
                                 ActionCode.ACTION_SELECT_UP]
        self.manip_actions = [ActionCode.ACTION_CUT,
                              ActionCode.ACTION_COPY,
                              ActionCode.ACTION_PASTE,
                              ActionCode.ACTION_ESCAPE]
        self.state_actions = [ActionCode.ACTION_UNDO,
                              ActionCode.ACTION_REDO,
                              ActionCode.ACTION_UNDO_EMACS]
        self.batch_actions = [ActionCode.ACTION_DELETE_WORD,
                              ActionCode.ACTION_BACKSPACE_WORD,
                              ActionCode.ACTION_KILL_EOL] + self.manip_actions


    def step_line(self):
        """Prepare for a new key event"""
        self.prev_prompt = self.prompt
        self.prev_before_cursor = self.before_cursor
        self.prev_after_cursor = self.after_cursor

    def reset_line(self, prompt):
        """Prepare for a new input line"""
        self.prompt = prompt
        self.before_cursor = ''
        self.after_cursor = ''
        self.overwrite = False
        self.reset_prev_line()

    def reset_prev_line(self):
        """Reset previous line (current line will repaint as new)"""
        self.prev_prompt = ''
        self.prev_before_cursor = ''
        self.prev_after_cursor = ''

    def changed(self):
        """Check whether a change has occurred in the input state (e.g. for repaint)"""
        return self.prompt != self.prev_prompt \
               or self.before_cursor != self.prev_before_cursor \
               or self.after_cursor != self.prev_after_cursor

    def handle(self, action, arg = None):
        """Handle a keyboard action"""
        handler = self.handlers[action]
        if action in self.navigate_actions:
            # Navigation actions have a "select" argument
            handler(arg)
        elif action in self.insert_actions:
            # Insert actions have a "text" argument
            handler(arg)
        else:
            # Other actions don't have arguments
            handler()

        # Add the previous state as an undo state if needed
        if self.changed():
            if action in self.batch_actions \
                    or (action in self.insert_actions + self.delete_actions \
                                and action != self.last_action) \
                    or action == ActionCode.ACTION_UNDO_EMACS:
                self.undo.append((self.prev_before_cursor, self.prev_after_cursor))
                self.redo = []
            if action in self.batch_actions \
                    or (action in self.insert_actions + self.delete_actions \
                                and action != self.last_action) \
                    or action == ActionCode.ACTION_UNDO:
                self.undo_emacs.append((self.prev_before_cursor, self.prev_after_cursor))
                self.undo_emacs_index = -1

        # print "\n", self.undo, "    ", self.redo, "\n"

        self.last_action = action


    def key_left(self, select=False):
        """
        Move cursor one position to the left
        Also handle text selection according to flag
        """
        if self.before_cursor != '':
            self.after_cursor = self.before_cursor[-1] + self.after_cursor
            self.before_cursor = self.before_cursor[0 : -1]
        if not select:
            self.reset_selection()
        self.history.reset()
        self.search_substr = None

    def key_right(self, select=False):
        """
        Move cursor one position to the right
        Also handle text selection according to flag
        """
        if self.after_cursor != '':
            self.before_cursor = self.before_cursor + self.after_cursor[0]
            self.after_cursor = self.after_cursor[1 : ]
        if not select:
            self.reset_selection()
        self.history.reset()
        self.search_substr = None

    def key_home(self, select=False):
        """
        Home key
        Also handle text selection according to flag
        """
        self.after_cursor = self.before_cursor + self.after_cursor
        self.before_cursor = ''
        if not select:
            self.reset_selection()
        self.history.reset()
        self.search_substr = None

    def key_end(self, select=False):
        """
        End key
        Also handle text selection according to flag
        """
        self.before_cursor = self.before_cursor + self.after_cursor
        self.after_cursor = ''
        if not select:
            self.reset_selection()
        self.history.reset()
        self.search_substr = None

    def key_search_right(self, _):
        """
        Search for text to the right of the cursor
        """
        if (self.before_cursor + self.after_cursor).strip() == '':
            self.bell = True
            return
        self.search_rev = False
        if self.search_substr is None:
            self.search_substr = ''
        elif self.search_substr:
            self.search_right_next()

    def key_search_left(self, _):
        """
        Search for text to the left of the cursor
        """
        if (self.before_cursor + self.after_cursor).strip() == '':
            self.bell = True
            return
        self.search_rev = True
        if self.search_substr is None:
            self.search_substr = ''
        elif self.search_substr:
            self.search_left_prev()

    def key_extend_selection(self, _):
        """
        Extend the selection "lexically, i.e. select an increasingly larger chunk going
        from: word -> filename/extension -> full filename + extension -> full file path ->
        complete command -> entire line
        """
        if self.extend_separators is None:
            self.reset_selection()
            self.history.reset()

            # stick to the closest word to the left or right
            whitespace_left = len(self.before_cursor) - len(self.before_cursor.rstrip(' '))
            whitespace_right = len(self.after_cursor) - len(self.after_cursor.lstrip(' '))
            if whitespace_left == len(self.before_cursor) or whitespace_left >= whitespace_right > 0:
                for _ in range(whitespace_right):
                    self.key_right(False)
            elif whitespace_right == len(self.after_cursor) or whitespace_right >= whitespace_left > 0:
                for _ in range(whitespace_left):
                    self.key_left(False)

            # skip over trailing backslashes
            while (self.before_cursor.endswith('\\') and
                (self.after_cursor == '' or self.after_cursor.startswith(' '))):
                self.key_left(False)

            if self.before_cursor.count('"') % 2 == 0:
                if self.before_cursor.endswith('"'):
                    self.key_left(False)
                elif self.after_cursor.startswith('"'):
                    self.key_right(False)

            if self.before_cursor.count('"') % 2 == 0:
                self.extend_separators = list(EXTEND_SEPARATORS_OUTSIDE_QUOTES)
            else:
                self.extend_separators = list(EXTEND_SEPARATORS_INSIDE_QUOTES)

        self.extend_selection()

    def key_shrink_selection(self):
        if self.selection_history:
            self.before_cursor, self.after_cursor, self.selection_start, self.extend_separators = self.selection_history.pop()
            if not self.selection_history:
                self.reset_selection()
        else:
            self.bell = True


    def key_left_word(self, select=False):
        """Move backward one word (Ctrl-Left)"""
        # Skip spaces
        while self.before_cursor != '' and self.before_cursor[-1] in word_sep:
            self.key_left(select)

        # Jump over word
        while self.before_cursor != '' and not self.before_cursor[-1] in word_sep:
            self.key_left(select)

    def key_right_word(self, select=False):
        """Move forward one word (Ctrl-Right)"""
        # Skip spaces
        while self.after_cursor != '' and self.after_cursor[0] in word_sep:
            self.key_right(select)

        # Jump over word
        while self.after_cursor != '' and not self.after_cursor[0] in word_sep:
            self.key_right(select)

    def key_backspace_word(self):
        """Delte backwards one word (Ctrl-Left), or delete selection"""
        if self.get_selection() != '':
            self.delete_selection()
        else:
            # Skip spaces
            while self.before_cursor != '' and self.before_cursor[-1] in word_sep:
                self.key_backspace()

            # Jump over word
            while self.before_cursor != '' and not self.before_cursor[-1] in word_sep:
                self.key_backspace()

    def key_del_word(self):
        """Delete forwards one word (Ctrl-Right), or delete selection"""
        if self.get_selection() != '':
            self.delete_selection()
        else:
            # Skip spaces
            while self.after_cursor != '' and self.after_cursor[0] in word_sep:
                self.key_del()

            # Jump over word
            while self.after_cursor != '' and not self.after_cursor[0] in word_sep:
                self.key_del()

    def key_del(self):
        """Delete character at cursor"""
        if self.get_selection() != '':
            self.delete_selection()
        else:
            self.after_cursor = self.after_cursor[1 : ]
            self.history.reset()
            self.reset_selection()

    def key_kill_line(self):
        """Kill the rest of the current line"""
        if self.get_selection() != '':
            self.delete_selection()
        else:
            self.after_cursor = ''
        self.history.reset()

    def key_up(self):
        """Arrow up (history previous)"""

        # Clear undo/redo history
        self.undo = []
        self.redo = []

        # print '\n\n', history, history_index, '\n\n'
        if not self.history.trail:
            # Start search
            self.history.start(self.before_cursor + self.after_cursor)
        if not self.history.up():
            self.bell = True
        self.before_cursor = self.history.current()[0]
        self.after_cursor = ''

        #print '\n\nHistory:', self.history
        #print 'Trail:', self.history_trail, '\n\n'

        self.reset_selection()

    def key_down(self):
        """Arrow down (history next)"""

        # Clear undo/redo history
        self.undo = []
        self.redo = []

        if self.history.down():
            self.before_cursor = self.history.current()[0]
            self.after_cursor = ''
        else:
            self.bell = True
        self.reset_selection()

    def key_esc(self):
        """Esc key"""
        if self.get_selection() != '' or self.search_substr is not None:
            self.reset_selection()
        else:
            if self.history.filter != '':
                # Reset search filter, if any
                self.history.reset()
            else:
                # Clear current line (we keep it in the history though)
                self.history.add(self.before_cursor + self.after_cursor)
                self.before_cursor = ''
                self.after_cursor = ''

    def key_backspace(self):
        """Backspace key"""
        if self.get_selection() != '':
            self.delete_selection()
        else:
            self.before_cursor = self.before_cursor[0 : -1]
            self.history.reset()
            self.reset_selection()

    def key_copy(self):
        """Copy selection to clipboard"""
        wclip.OpenClipboard()
        wclip.EmptyClipboard()
        wclip.SetClipboardText(self.get_selection())
        wclip.CloseClipboard()
        self.history.reset()

    def key_cut(self):
        """Cut selection to clipboard"""
        self.key_copy()
        self.delete_selection()
        self.history.reset()

    def key_paste(self):
        """Paste from clipboard"""
        wclip.OpenClipboard()
        if wclip.IsClipboardFormatAvailable(wclip.CF_TEXT):
            text = wclip.GetClipboardData()

            # Purge garbage chars that some apps put in the clipboard
            if text.find('\0') >= 0:
                text = text[:text.find('\0')]

            # Convert newlines to blanks
            text = text.replace('\r', '').replace('\n', ' ')

            # Insert into command line
            if self.get_selection() != '':
                self.delete_selection()
            self.before_cursor = self.before_cursor + text
            if self.overwrite:
                self.after_cursor = self.after_cursor[len(text):]
            self.reset_selection()
        wclip.CloseClipboard()
        self.history.reset()

    def key_insert(self, text):
        """Insert text at the current cursor position"""
        self.history.reset()

        if self.search_substr is not None:
            # Search mode
            self.search_substr += text
            if self.after_cursor.lower().startswith(text.lower()):
                self.before_cursor += self.after_cursor[:len(text)]
                self.after_cursor = self.after_cursor[len(text):]
            else:
                self.advance_search()
        else:
            # Typing mode
            if self.get_selection() != '':
                self.delete_selection()
            self.before_cursor += text
            if self.overwrite:
                self.after_cursor = self.after_cursor[len(text):]
            self.reset_selection()

    def key_complete(self, completed):
        """Update the text before cursor to match some completion"""
        if (completed.endswith(' ') and self.after_cursor.startswith(' ')) \
                or (completed.endswith('\\') and self.after_cursor.startswith('\\')):
            self.after_cursor = self.after_cursor[1:]
        if (completed.endswith('"\\') and self.after_cursor.startswith('"\\')
            or completed.endswith('" ') and self.after_cursor.startswith('" ')) :
            self.after_cursor = self.after_cursor[2:]
        chars_added = len(completed) - len(self.before_cursor)
        self.before_cursor = completed
        if self.overwrite:
            self.after_cursor = self.after_cursor[chars_added:]
        self.reset_selection()
        self.history.reset()

    def key_undo(self):
        """Undo the last action or group of actions"""
        if self.undo != []:
            self.redo.append((self.before_cursor, self.after_cursor))
            (before, after) = self.undo.pop()
            self.before_cursor = before
            self.after_cursor = after
            self.selection_start = len(before)

    def key_undo_emacs(self):
        """Emacs-style undo"""
        if self.undo_emacs != []:
            if self.last_action != ActionCode.ACTION_UNDO_EMACS:
                self.undo_emacs.append((self.before_cursor, self.after_cursor))
                self.undo_emacs_index -= 1

            if len(self.undo_emacs) + self.undo_emacs_index >= 0:
                (before, after) = self.undo_emacs[self.undo_emacs_index]
                self.before_cursor = before
                self.after_cursor = after
                self.undo_emacs_index -= 1
                self.selection_start = len(before)

    def key_redo(self):
        """Redo the last action or group of actions"""
        if self.redo != []:
            self.undo.append((self.before_cursor, self.after_cursor))
            (before, after) = self.redo.pop()
            self.before_cursor = before
            self.after_cursor = after
            self.selection_start = len(before)

    def key_expand(self, text):
        """
        Dynamically expand the word at the cursor.

        This expands the current token based by looking at the input
        history, similar to Emacs' Alt-/
        """
        if self.expand_matches == [] or self.last_action != ActionCode.ACTION_EXPAND:
            # Re-initialize the list of matches
            self.expand_line = self.before_cursor
            line_words = [''] + self.expand_line.split(' ')
            expand_stub = line_words[-1]
            expand_context = line_words[-2]

            context_matches = []
            no_context_matches = []
            for line in reversed(self.history.list):
                line_words = [''] + line.split(' ')
                for i in range(len(line_words) - 1, 0, -1):
                    word = line_words[i]
                    context = line_words[i - 1]
                    if (word.lower().startswith(expand_stub.lower())
                        and word.lower() != expand_stub.lower()):
                        if context.lower() == expand_context.lower():
                            context_matches.append(word)
                        else:
                            no_context_matches.append(word)

            # print '\n\n', no_context_matches, context_matches, '\n\n'

            self.expand_stub = expand_stub
            matches_set = {}
            self.expand_matches = [matches_set.setdefault(e, e)
                                   for e in context_matches + no_context_matches
                                   if e not in matches_set] + [self.expand_stub]
            self.expand_matches.reverse()
            # print '\n\n', self.expand_matches, '\n\n'

        match = self.expand_matches[-1]
        old_len_before_cursor = len(self.before_cursor)
        self.before_cursor = self.expand_line[:len(self.expand_line)
                                               - len(self.expand_stub)] + match
        if self.overwrite:
            self.after_cursor = self.after_cursor[len(self.before_cursor) - old_len_before_cursor:]
        self.reset_selection()
        self.history.reset()
        del self.expand_matches[-1]

    def key_toggle_overwrite(self):
        """Toggle typing overwrite mode"""
        self.overwrite = not self.overwrite

    def reset_selection(self):
        """Reset text selection"""
        self.selection_start = len(self.before_cursor)
        self.search_substr = None
        self.extend_separators = None
        self.selection_history = []

    def delete_selection(self):
        """Remove currently selected text"""
        len_before = len(self.before_cursor)
        if self.selection_start < len_before:
            self.before_cursor = self.before_cursor[: self.selection_start]
        else:
            self.after_cursor = self.after_cursor[self.selection_start - len_before: ]
        self.reset_selection()

    def get_selection_range(self):
        """Return the start and end indexes of the selection"""
        return (min(len(self.before_cursor), self.selection_start),
                max(len(self.before_cursor), self.selection_start))

    def get_selection(self):
        """Return the current selected text"""
        start, end = self.get_selection_range()
        return (self.before_cursor + self.after_cursor)[start: end]

    def advance_search(self):
        if not self.search_rev:
            self.search_right_next()
        else:
            self.search_left_prev()

    def search_right_next(self):
        pos = self.after_cursor.lower().find(self.search_substr.lower())
        if pos == -1:
            self.bell = True
            return
        self.selection_start = len(self.before_cursor) + pos
        pos += len(self.search_substr)
        self.before_cursor += self.after_cursor[:pos]
        self.after_cursor = self.after_cursor[pos:]

    def search_left_prev(self):
        pos = self.before_cursor.lower().rfind(self.search_substr.lower(), 0, -1)
        if pos == -1:
            self.bell = True
            return
        self.selection_start = pos
        pos += len(self.search_substr)
        self.before_cursor, self.after_cursor = \
            self.before_cursor[:pos], self.before_cursor[pos:] + self.after_cursor

    def extend_selection(self):
        line = self.before_cursor + self.after_cursor
        extend_begin = len(self.before_cursor)
        extend_end = max(self.selection_start, extend_begin)
        separators = list(self.extend_separators)
        expanded = False

        while not expanded and separators != []:
            while extend_begin >= 1 and not line[extend_begin - 1] in separators:
                extend_begin -= 1
                expanded = True
            while extend_end < len(line) and not line[extend_end] in separators:
                extend_end += 1
                expanded = True
            separators.pop(0)

            if separators == [] and self.before_cursor.count('"') % 2 == 1:
                separators = list(EXTEND_SEPARATORS_OUTSIDE_QUOTES)

        if expanded:
            self.selection_history.append((self.before_cursor, self.after_cursor, self.selection_start, self.extend_separators))
            self.before_cursor = line[:extend_begin]
            self.after_cursor = line[extend_begin:]
            self.selection_start = extend_end
            self.extend_separators = separators
        else:
            self.bell = True
