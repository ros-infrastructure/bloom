from __future__ import print_function

import sys

_ansi = {}
_quiet = False
_debug = False


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


def print_debug(state=True):
    global _debug
    _debug = state

# Default to debug off
print_debug(False)


def debug(msg, file=sys.stdout):
    global _quiet, _debug
    msg = ansi('greenf') + "Debug: " + msg + ansi('reset')
    if not _quiet and _debug:
        print(msg, file=file)


def info(msg, file=sys.stdout):
    global _quiet
    if not _quiet:
        print(msg, file=file)
    return msg


def warning(msg, file=sys.stdout):
    global _quiet
    msg = ansi('yellowf') + ansi('boldon') + "Warning: " + msg + ansi('reset')
    if not _quiet:
        print(msg, file=file)
    return msg


def error(msg, file=sys.stderr):
    global _quiet
    msg = ansi('redf') + ansi('boldon') + "Error: " + msg + ansi('reset')
    if not _quiet:
        print(msg, file=file)
    return msg
