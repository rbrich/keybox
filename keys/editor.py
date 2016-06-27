import logging
import blessed


class InlineEditor:

    """

    Edit arbitrary text, leaving current terminal content intact.
    Cursor movement is implemented by directly using terminfo sequences
    (curses requires going fullscreen). This may not be supported on some
    terminals.

    References:

    - man 5 terminfo
    - http://pubs.opengroup.org/onlinepubs/007908799/xcurses/terminfo.html

    """

    def __init__(self):
        self._term = blessed.Terminal()
        # Edited text is split to left and right part (according to the cursor)
        self._left = ''
        self._right = ''

    def _key_enter(self):
        self._left += '\n'
        t, right = self._term, self._right
        yield t.el()  # Erase rest of line
        # Scroll down, insert line
        n = right.count('\n')
        if n > 0:
            yield t.cud(n) + t.ind() + t.cuu(n) + t.il1()
        else:
            yield t.ind()
        # Insert wrapped text
        yield right.split('\n')[0] + t.hpa(0)

    def _key_up(self):
        t, left, right = self._term, self._left, self._right
        y, x = t.get_location()
        # Find end of previous line
        ln_end = left.rfind('\n')
        if ln_end == -1:
            return
        # Find start of previous line
        ln_start = left.rfind('\n', None, ln_end) + 1
        # Find corresponding column (if the line is long enough)
        col = min(len(left[ln_start:ln_end]), x - 1)
        i = ln_start + col
        self._right = left[i:] + right
        self._left = left[:i]
        yield t.cuu1() + t.hpa(col)

    def _key_down(self):
        t, left, right = self._term, self._left, self._right
        y, x = t.get_location()
        # Find start of next line
        ln_start = right.find('\n') + 1
        if ln_start == 0:
            return
        # Find end of next line
        ln_end = right.find('\n', ln_start)
        if ln_end == -1:
            ln_end = len(right)
        # Find corresponding column (if the line is long enough)
        col = min(len(right[ln_start:ln_end]), x - 1)
        i = ln_start + col
        self._left = left + right[:i]
        self._right = right[i:]
        yield t.cud1() + t.hpa(col)

    def _key_left(self):
        t, left, right = self._term, self._left, self._right
        if not left:
            return
        self._right = left[-1:] + right
        self._left = left[:-1]
        if left[-1] == '\n':
            if t.bw():
                yield t.cub1()
            else:
                ln_len = len(self._left) - (self._left.rfind('\n') + 1)
                yield t.cuu1() + t.cuf(ln_len)
        else:
            yield t.cub1()

    def _key_right(self):
        t, left, right = self._term, self._left, self._right
        if not right:
            return
        self._left = left + right[:1]
        self._right = right[1:]
        if right[0] == '\n':
            yield '\n'
        else:
            yield t.cuf1()

    def _key_home(self):
        t, left, right = self._term, self._left, self._right
        ln_start = left.rfind('\n') + 1
        self._right = left[ln_start:] + right
        self._left = left[:ln_start]
        yield t.hpa(0)

    def _key_end(self):
        t, left, right = self._term, self._left, self._right
        ln_end = right.find('\n')
        if ln_end == -1:
            ln_end = len(right)
        self._left = left + right[:ln_end]
        self._right = right[ln_end:]
        if ln_end:
            yield t.cuf(ln_end)

    def _key_delete(self):
        t, left, right = self._term, self._left, self._right
        if not right:
            return
        self._right = right[1:]
        if right[0] == '\n':
            right = self._right
            # The el (clr_eol) is needed to clear the next line if it's last row
            yield t.sc() + t.cud1() + t.el() + t.dl1() + t.rc()
            ln_end = right.find('\n') if '\n' in right else len(right)
            yield right[:ln_end] + t.rc()
        else:
            yield t.dch1()

    def _key_backspace(self):
        t, left, right = self._term, self._left, self._right
        if not left:
            return
        self._left = left[:-1]
        if left[-1] == '\n':
            left = self._left
            ln_start = left.rfind('\n') + 1
            yield t.dl1() + t.cuu1() + t.cuf(len(left) - ln_start)
            ln_end = right.find('\n') if '\n' in right else len(right)
            yield t.sc() + right[:ln_end] + t.rc()
        else:
            yield t.cub1() + t.dch1()

    def edit(self, value):
        t = self._term
        t.stream.write(t.hpa(0) + value)
        t.stream.flush()
        self._left, self._right = value, ''
        logger = logging.getLogger(__name__)
        try:
            with t.cbreak():
                while True:
                    ch = t.inkey()
                    # Workaround for Backspace key being reported as Delete
                    if str(ch) == t.kbs():
                        ch._name = 'KEY_BACKSPACE'
                    logger.debug("pressed: %r (%r)" % (ch, str(ch)))
                    if ch.is_sequence:
                        func = getattr(self, '_' + ch.name.lower(), None)
                        if func:
                            for code in func():
                                t.stream.write(code)
                        elif ch.name == 'KEY_F10' or ch.name == 'KEY_ESCAPE':
                            break
                        else:
                            continue
                    elif ch.isprintable():
                        self._left += ch
                        t.stream.write(t.ich(1) + ch)
                    else:
                        continue
                    t.stream.flush()
                    logger.debug("content: %r#%r" % (self._left, self._right))
        finally:
            # Move the cursor to bottom (by printing text following the cursor)
            t.stream.write(self._right + '\n')
        return self._left + self._right


if __name__ == '__main__':
    logging.basicConfig(filename='edit2.log', level='DEBUG')
    print(InlineEditor().edit("first line\nsecond line\n..."))
