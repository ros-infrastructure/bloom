from __future__ import print_function

import sys

_ansi = {}
_quiet = False
_debug = False
_log_prefix_stack = ['']
_log_prefix = ''
_log_indent = False


def ansi(key):
    """Returns the escape sequence for a given ansi color key"""
    global _ansi
    return _ansi[key]


def enable_ANSI_colors():
    """
    Populates the global module dictionary `ansi` with ANSI escape sequences.
    """
    global _ansi
    colors = [
        'black', 'red', 'green', 'yellow', 'blue', 'purple', 'cyan', 'white'
    ]
    _ansi = {
        'escape': '\033', 'reset': 0,
        'boldon': 1, 'italicson': 3, 'ulon': 4, 'invon': 7,
        'boldoff': 22, 'italicsoff': 23, 'uloff': 24, 'invoff': 27,
    }

    # Convert plain numbers to escapes
    for key in _ansi:
        if key != 'escape':
            _ansi[key] = '{0}[{1}m'.format(_ansi['escape'], _ansi[key])

    # Foreground
    for index, color in enumerate(colors):
        _ansi[color + 'f'] = '{0}[{1}m'.format(_ansi['escape'], 30 + index)

    # Background
    for index, color in enumerate(colors):
        _ansi[color + 'b'] = '{0}[{1}m'.format(_ansi['escape'], 40 + index)


def disable_ANSI_colors():
    """
    Sets all the ANSI escape sequences to empty strings, effectively disabling
    console colors.
    """
    global _ansi
    for key in _ansi:
        _ansi[key] = ''

# Default to ansi colors on
enable_ANSI_colors()


def quiet(state=True):
    global _quiet
    _quiet = state

# Default to quiet off
quiet(False)


def enable_debug(state=True):
    global _debug
    _debug = state

# Default to debug off
enable_debug(False)


def enable_debug_indent(state=True):
    global _log_indent
    _log_indent = state

enable_debug_indent(True)


def _get_log_prefix():
    global _log_prefix_stack, _log_indent
    if _log_indent:
        return (' ' * (len(_log_prefix_stack) - 2)) + _log_prefix_stack[-1]
    else:
        return _log_prefix_stack[-1]


def push_log_prefix(prefix):
    global _log_prefix, _log_prefix_stack
    _log_prefix_stack.append(prefix)
    _log_prefix = _get_log_prefix()


def pop_log_prefix():
    global _log_prefix, _log_prefix_stack
    if len(_log_prefix_stack) > 1:
        _log_prefix_stack.pop()
    _log_prefix = _get_log_prefix()


def log_prefix(prefix):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            push_log_prefix(prefix)
            try:
                result = fn(*args, **kwargs)
            finally:
                pop_log_prefix()
            return result
        return wrapper
    return decorator


def debug(msg, file=sys.stdout, end='\n', use_prefix=True):
    global _quiet, _debug, _log_prefix
    if use_prefix:
        msg = ansi('greenf') + _log_prefix + msg + ansi('reset')
    else:
        msg = ansi('greenf') + msg + ansi('reset')
    if not _quiet and _debug:
        print(msg, file=file, end=end)


def info(msg, file=sys.stdout, end='\n', use_prefix=True):
    global _quiet
    if use_prefix:
        msg = _log_prefix + msg
    if not _quiet:
        print(msg, file=file, end=end)
    return msg


def warning(msg, file=sys.stdout, end='\n', use_prefix=True):
    global _quiet
    if use_prefix:
        msg = ansi('yellowf') + ansi('boldon') + _log_prefix + msg \
            + ansi('reset')
    else:
        msg = ansi('yellowf') + ansi('boldon') + msg + ansi('reset')
    if not _quiet:
        print(msg, file=file, end=end)
    return msg


def error(msg, file=sys.stderr, end='\n', use_prefix=True):
    global _quiet
    if use_prefix:
        msg = ansi('redf') + ansi('boldon') + _log_prefix + msg + ansi('reset')
    else:
        msg = ansi('redf') + ansi('boldon') + msg + ansi('reset')
    if not _quiet:
        print(msg, file=file, end=end)
    return msg
