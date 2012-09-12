from common import fuzzy_match

class CommandHistory:
    """
    Handle all things related to storing and navigating the command history
    """
    # The actual command list
    def __init__(self):
        self.list = []

        # The current search filter
        self.filter = ''

        # The match groups as returned by the filter function
        self.filter_matches = None

        # The current index in the list (while navigating)
        self.index = 0

        # A trail of visited indices (while navigating)
        self.trail = []

    def start(self, line):
        """
        Start history navigation
        """
        #print '\n\nStart\n\n'
        if self.index != len(self.list):
            print 'index =', self.index, 'len(list) =', len(self.list)
        self.filter = line
        self.trail = []

    def up(self):
        """
        Navigate back in the command history
        """
        orig_index = self.index

        # First search for prefix matches, as they are usually better
        self.index -= 1
        while self.index >= 0:
            self.filter_matches = fuzzy_match(self.filter, self.list[self.index], True)
            if self.filter_matches:
                # Found a match
                break
            self.index -= 1
            # print '\n\n', self.history_index, '\n\n'
        if self.index < 0:
            self.index = orig_index

            # Then search for the less strict, everywhere in the command line, fuzzy matching
            self.index -= 1
            while self.index >= 0:
                self.filter_matches = fuzzy_match(self.filter, self.list[self.index], False)
                if self.filter_matches:
                    break
                self.index -= 1
                # print '\n\n', self.history_index, '\n\n'

        if self.index < 0:
            self.index = orig_index
            self.filter_matches = fuzzy_match(self.filter, self.list[self.index], False)
        else:
            #print '\n\nIndex:', self.index, 'Trail:', orig_index, '\n\n'
            self.trail.append(orig_index)

    def down(self):
        """
        Navigate forward in the command history
        """
        if self.trail:
            self.index = self.trail.pop()
            self.filter_matches = fuzzy_match(self.filter, self.current())

    def reset(self):
        """Reset browsing through the history"""
        self.index = len(self.list)
        self.filter = ''
        self.filter_matches = []
        self.trail = []

    def add(self, line):
        """Add a new line to the history"""
        if line:
            #print 'Adding "' + line + '"'
            if line in self.list:
                self.list.remove(line)
            self.list.append(line)
            self.reset()

    def current(self):
        """Return the current hisotry item"""
        return self.list[self.index] if self.index < len(self.list) else self.filter