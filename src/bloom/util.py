"""
Provides common utility functions for bloom.
"""
from __future__ import print_function

import sys

from subprocess import check_call, check_output, CalledProcessError, PIPE
from subprocess import Popen

_ansi = {}


def create_temporary_directory(prefix_dir=None):
    """Creates a temporary directory and returns its location"""
    from tempfile import mkdtemp
    return mkdtemp(prefix='bloom_', dir=prefix_dir)


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

enable_ANSI_colors()


def maybe_continue(default='y'):
    """Prompts the user for continuation"""
    default = default.lower()
    msg = "{0}Continue ".format(ansi('boldon'))
    if default == 'y':
        msg += "{0}[Y/n]? {1}".format(ansi('yellowf'), ansi('reset'))
    else:
        msg += "{0}[y/N]? {1}".format(ansi('yellowf'), ansi('reset'))

    while True:
        response = raw_input(msg)
        if not response:
            response = default

        response = response.lower()
        if response not in ['y', 'n']:
            error_msg = ansi('redf') + 'Reponse `' + response
            error_msg += '` was not recognized, please use one of y, Y, n, N.'
            error_msg += ansi('reset')
            print(error_msg)
        else:
            break

    if response == 'n':
        return False
    return True


def bailout(reason='Exiting.'):
    """Exits bloom for a given reason"""
    print(ansi('redf') + ansi('boldon') + reason + ansi('reset'))
    sys.exit(1)


def extract_text(element):
    node_list = element.childNodes
    result = []
    for node in node_list:
        if node.nodeType == node.TEXT_NODE:
            result.append(node.data)
    return ''.join(result)


def segment_version(full_version):
    version_list = full_version.split('.')
    if len(version_list) != 3:
        bailout('Invalid version element in the stack.xml, expected: ' \
                '<major>.<minor>.<patch>')
    return version_list


def parse_stack_xml(file_path):
    """
    Returns a dictionary representation of a stack xml file.

    :param file_path: path to stack xml file to be converted
    :returns: dictionary representation of the stack xml file
    """
    from xml.dom.minidom import parse
    dom = parse(file_path)
    results = {}
    results['full_version'] = \
        extract_text(dom.getElementsByTagName('version')[0])
    results['major'], results['minor'], results['patch'] = \
        segment_version(results['full_version'])
    results['package_name'] = extract_text(dom.getElementsByTagName('name')[0])
    return results


def execute_command(cmd, shell=True, autofail=True, silent=True, cwd=None):
    """
    Executes a given command using vcstools' run_shell_command function.
    """
    io_type = None
    result = 0
    error = None
    if silent:
        io_type = PIPE
    try:
        result = check_call(cmd, shell=True, cwd=cwd,
                            stdout=io_type, stderr=io_type)
    except CalledProcessError as cpe:
        result = cpe.returncode
        error = str(cpe)
    if result != 0 and autofail:
        raise RuntimeError("Failed to execute the command:" \
                           " `{0}`: {1}".format(cmd, error))
    return result


def get_current_git_branch(directory=None):
    """
    Returns the current git branch by parsing the output of `git branch`

    This will raise a RuntimeError if the current working directory is not
    a git repository.  If no branch could be determined it will return None,
    i.e. (no branch) will return None.
    """
    cmd = 'git branch --no-color'
    output = check_output(cmd, shell=True, cwd=directory)
    output = output.splitlines()
    for token in output:
        if token.strip().startswith('*'):
            token = token[2:]
            if token == '(no branch)':
                return None
            return token

    return None


def error(msg):
    """Prints a message as an error"""
    print(ansi('redf') + ansi('boldon') + 'Error: ' + msg + ansi('reset'))


def track_all_git_branches(branches=None, cwd=None):
    """
    Tracks all specified branches.

    :param branches: a list of branches that are to be tracked if not already
    tracked.  If this is set to None then all remote branches will be tracked.
    """
    # Save current branch
    current_branch = get_current_git_branch(cwd)
    from subprocess import check_output
    # Get the local branches
    local_branches = check_output('git branch', shell=True, cwd=cwd)
    local_branches = local_branches.splitlines()
    # Strip local_branches of white space
    for index, local_branch in enumerate(local_branches):
        local_branches[index] = local_branch.strip()
    # Either get the remotes or use the given list of branches to track
    remotes_out = check_output('git branch -r', shell=True, cwd=cwd)
    remotes = remotes_out.splitlines()
    if branches == None:
        branches = remotes
    # Subtract the locals from the remotes
    to_track = []
    for remote in branches:
        remote = remote.strip()
        if remote.count('master') != 0:
            continue
        if remote.count('/') > 0:
            remote_branch = remote.split('/')[1]
        else:
            remote_branch = remote
        if remote_branch not in local_branches:
            to_track.append(remote_branch)
    # Now track any remotes that are not local
    for branch in to_track:
        if remotes_out.count(branch) > 0:
            cmd = 'git checkout --track -b {0}'.format(branch)
            execute_command(cmd, cwd=cwd)
    # Restore original branch
    if current_branch:
        execute_command('git checkout {0}'.format(current_branch), cwd=cwd)


def assert_is_remote_git_repo(repo):
    """
    Asserts that the specified repo url points to a valid git repository.
    """
    print('Verifying that {0} is a git repository...'.format(repo), end='')
    cmd = 'git ls-remote --heads {0}'.format(repo)
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    output, _ = p.communicate()
    if p.returncode != 0:
        print(ansi('redf') + ' fail' + ansi('reset'))
        bailout("Repository {0} is not a valid git repository.".format(repo))
    else:
        print(' pass')


def assert_is_not_gbp_repo(repo):
    """
    Asserts that the specified repo url does not point to a gbp repo.
    """
    assert_is_remote_git_repo(repo)
    print('Verifying that {0} is not a gbp repository...'.format(repo), end='')
    cmd = 'git ls-remote --heads {0} upstream*'
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    output, _ = p.communicate()
    if p.returncode != 0:
        print(ansi('redf') + ' fail' + ansi('reset'))
        bailout("Error: {0} appears to have an 'upstream' branch, " \
                "indicating a gbp.")


def get_last_git_tag(cwd=None):
    """
    Returns the latest git tag in the given git repo, but returns '' if
    there are not tags.
    """
    cmd = "git for-each-ref --sort='*authordate' " \
          "--format='%(refname:short)' refs/tags/upstream"
    output = check_output(cmd, shell=True, cwd=cwd, stderr=PIPE)
    output = output.splitlines()
    if len(output) == 0:
        return ''
    return output[-1]
