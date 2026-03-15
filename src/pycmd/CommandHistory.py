import re

class CommandHistory:
    """
    Handle all things related to managing and navigating the command history
    """
    def __init__(self):
        # The actual command list
        self.list = []

        # The current search filter
        self.filter = ''

        # A filtered list based on the current filter
        self.filtered_list = []

        # A trail of visited indices (while navigating)
        self.trail = []

    def start(self, line):
        """
        Start history navigation
        """
        #print '\n\nStart\n\n'
        self.filter = line

        # Create a list of regex patterns to use when navigating the history
        # using a filter
        # A. First use just the space as word separator; these are the most
        # useful matches (think acronyms 'g c m' for 'git checkout master' etc)
        words = [re.escape(w) for w in re.findall('[^\\s]+', line)] # Split the filter into words
        boundary = '[\\s]+'
        patterns = [
            # Prefixes match for each word in the command (strongest, these will be the
            # first in the list
            '^' + boundary.join(['(' + word + ')[^\\s]*' for word in words]) + '$',

            # Prefixes match for some words in the command
            boundary.join(['(' + word + ')[^\\s]*' for word in words]),
        ]

        # B. Then split based on other separator characters as well
        words = [re.escape(w) for w in re.findall('[a-zA-Z0-9]+', line)] # Split the filter into words
        boundary = '[\\s\\.\\-\\\\_]+'   # Word boundary characters
        patterns += [
            # Prefixes match for each word in the command (strongest, these will be the
            # first in the list
            '^' + boundary.join(['(' + word + ')[a-zA-Z0-9]*' for word in words]) + '$',

            # Prefixes match for some words in the command
            boundary.join(['(' + word + ')[a-zA-Z0-9]*' for word in words]),

            # Exact string match
            '(' + re.escape(line) + ')',

            # Substring match in different words
            boundary.join(['(' + word + ').*' for word in words]),

            # Substring match anywhere (weakest, these will be the last results)
            ''.join(['(' + word + ').*' for word in words])
        ]

        if len(words) <= 1:
            # Optimization: Skip the advanced word-based matching for empty or
            # simple (one-word) filters -- this saves a lot of computation effort
            # as these filters will yield a long list of matched lines!
            patterns = [patterns[4]]

        # Traverse the history and build the filtered list
        self.filtered_list = []
        for pattern in patterns:
            #print '\n\n', pattern, '\n\n'
            for line in reversed(self.list):
                if line in [l for (l, p) in self.filtered_list]:
                    # We already added this line, skip
                    continue
                # No need to re.compile() this, the re library automatically caches compiled
                # versions of the recently used expressions
                matches = re.search(pattern, line, re.IGNORECASE)
                if matches:
                    self.filtered_list.insert(0, (line, [matches.span(i) for i in range(1, matches.lastindex + 1)]))
                    #print '\n\n', self.filtered_list[-1], '\n\n'

        # We use the trail to navigate back in the same order
        self.trail = [(self.filter, [(0, len(self.filter))])]

    def up(self):
        """
        Navigate back in the command history
        """
        if self.filtered_list:
            self.trail.append(self.filtered_list.pop())
            return True
        else:
            return False

    def down(self):
        """
        Navigate forward in the command history
        """
        if self.trail:
            self.filtered_list.append(self.trail.pop())
            return True
        else:
            return False

    def zap(self, line):
        """
        Zap current entry out of the history list
        """
        if line in self.list:
            self.list.remove(line)
        self.reset()

    def reset(self):
        """Reset browsing through the history"""
        self.filter = ''
        self.filtered_list = []
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
        """Return the current history item"""
        return self.trail[-1] if self.trail else ('', [])
