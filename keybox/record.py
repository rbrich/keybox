# Record
#

#: Initial columns. This is used only for new keybox files.
COLUMNS = ('site', 'user', 'url', 'tags', 'mtime', 'note', 'password')


class Record(dict):

    """Record is a dict with standard set of keys (columns) always available."""

    def __init__(self, *args, **kwargs):
        self._columns = kwargs.pop('columns', list(COLUMNS))
        super().__init__(*args, **kwargs)
        self._standardize_columns()

    def __repr__(self):
        a = ['{}={!r}'.format(column, self[column]) for column in self._columns]
        return "{}({})".format(self.__class__.__name__, ', '.join(a))

    def __setitem__(self, key, value):
        super().__setitem__(key, value or '')
        if key not in self._columns:
            self._columns.append(key)

    def get_columns(self):
        return tuple(self._columns)

    def _standardize_columns(self):
        """Ensure all standard columns are available and their value is str."""
        for column in self._columns:
            if column not in self.keys() or self[column] is None:
                self[column] = ''
        # Also add unknown columns
        for column in self.keys():
            if column not in self._columns:
                self._columns.append(column)
