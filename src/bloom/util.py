from tempfile import mkdtemp
import sys

TMPDIR = mkdtemp(prefix='bloom_')

ansi = {}


def enable_ANSI_colors():
    '''
    Populates the global module dictionary `ansi` with ANSI escape sequences.
    '''
    global ansi
    colors = [
        'black', 'red', 'green', 'yellow', 'blue', 'purple', 'cyan', 'white'
    ]
    ansi = {
        'escape': '\033', 'reset': 0,
        'boldon': 1, 'italicson': 3, 'ulon': 4, 'invon': 7,
        'boldoff': 22, 'italicsoff': 23, 'uloff': 24, 'invoff': 27,
    }

    # Foreground
    for index, color in enumerate(colors):
        ansi[color + 'f'] = '{0}[{1}m'.format(ansi['escape'], 30 + index)

    # Background
    for index, color in enumerate(colors):
        ansi[color + 'b'] = '{0}[{1}m'.format(ansi['escape'], 40 + index)


def disable_ANSI_colors():
    '''
    Sets all the ANSI escape sequences to empty strings, effectively disabling
    console colors.
    '''
    global ansi
    for index in range(len(ansi)):
        ansi[index] = ''

enable_ANSI_colors()


def maybe_continue(default='y'):
    '''Prompts the user for continuation'''
    global ansi

    default = default.lower()
    msg = "{0}Continue ".format(ansi['boldon'])
    if default is 'y':
        msg += "{0}[Y/n]?{1}".format(ansi['yellowf'], ansi['reset'])
    else:
        msg += "{0}[y/N]?{1}".format(ansi['yellowf'], ansi['reset'])

    while True:
        response = raw_input(msg)
        if not response:
            response = default

        response = response.lower()
        if response not in ['y', 'n']:
            error_msg = ansi['redf'] + 'Reponse `' + response
            error_msg += '` was not recognized, please use one of y, Y, n, N.'
            error_msg += ansi['reset']
            print(error_msg)
        else:
            break

    if response == 'n':
        bailout("Exiting.")


def bailout(reason='Exiting.'):
    '''Exits bloom for a given reason'''
    print(ansi['redf'] + ansi['boldon'] + reason + ansi['reset'])
    sys.exit(1)
