"""
Common tools for running tests
"""

from __future__ import print_function

import functools
import os
import re
import shlex
import shutil
import sys
import tempfile

try:
    # Python2
    from StringIO import StringIO
except ImportError:
    # Python3
    from io import StringIO

from subprocess import Popen, PIPE, CalledProcessError


def assert_raises(exception_classes, callable_obj=None, *args, **kwargs):
    context = AssertRaisesContext(exception_classes)
    if callable_obj is None:
        return context
    with context:
        callable_obj(*args, **kwargs)


def assert_raises_regex(exception_classes, expected_regex, callable_obj=None, *args, **kwargs):
    context = AssertRaisesContext(exception_classes, expected_regex)
    if callable_obj is None:
        return context
    with context:
        callable_obj(*args, **kwargs)


class AssertRaisesContext(object):
    def __init__(self, expected, expected_regex=None):
        self.expected = expected
        self.expected_regex = expected_regex

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if self.expected is None:
            if exc_type is None:
                return True
            else:
                raise
        if exc_type is None:
            try:
                exc_name = self.expected.__name__
            except AttributeError:
                exc_name = str(self.expected)
            raise AssertionError("{0} not raised".format(exc_name))
        if not issubclass(exc_type, self.expected):
            raise
        if self.expected_regex is None:
            return True
        expected_regex = self.expected_regex
        expected_regex = re.compile(expected_regex)
        if not expected_regex.search(str(exc_value)):
            raise AssertionError("'{0}' does not match '{1}'".format(expected_regex.pattern, str(exc_value)))
        return True


class bloom_answer(object):
    ASSERT_NO_QUESTION = -1

    def __init__(self, answer, util_module=None):
        self.answer = answer
        if util_module is None:
            import bloom.util as util_module
            import bloom.commands.git.config as config_module
        self.util_module = util_module
        self.config_module = config_module

    def __call__(self, msg=None):
        if msg is not None:
            print(msg)
        assert self.answer != self.ASSERT_NO_QUESTION, \
            "bloom asked a question, and it should not have"
        if isinstance(self.answer, str):
            print(self.answer)
            return self.answer
        elif isinstance(self.answer, list):
            if self.answer:
                print(self.answer)
                return self.answer.pop(0)
            else:
                print('Nada')
                return ''
        else:
            assert False, "Invalid answers given to bloom_answer"

    def __enter__(self):
        self.orig_util_module_input = self.util_module.safe_input
        self.orig_config_module_input = self.config_module.safe_input
        self.util_module.safe_input = self
        self.config_module.safe_input = self

    def __exit__(self, exc_type, exc_value, traceback):
        self.util_module.safe_input = self.orig_util_module_input
        self.config_module.safe_input = self.orig_config_module_input


class change_directory(object):
    def __init__(self, directory=''):
        self.directory = directory
        self.original_cwd = None

    def __enter__(self):
        self.original_cwd = os.getcwd()
        os.chdir(self.directory)
        return self.directory

    def __exit__(self, exc_type, exc_value, traceback):
        if self.original_cwd and os.path.exists(self.original_cwd):
            os.chdir(self.original_cwd)


def in_temporary_directory(f):
    @functools.wraps(f)
    def decorated(*args, **kwds):
        with temporary_directory() as directory:
            from inspect import getargspec
            # If it takes directory of kwargs and kwds does already have
            # directory, inject it
            if 'directory' not in kwds and 'directory' in getargspec(f)[0]:
                kwds['directory'] = directory
            return f(*args, **kwds)
    decorated.__name__ = f.__name__
    return decorated


class redirected_stdio(object):
    def __enter__(self):
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        sys.stdout = out = StringIO()
        sys.stderr = err = StringIO()
        return out, err

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr


class temporary_directory(object):
    def __init__(self, prefix=''):
        self.prefix = prefix

    def __enter__(self):
        self.original_cwd = os.getcwd()
        self.temp_path = tempfile.mkdtemp(prefix=self.prefix)
        os.chdir(self.temp_path)
        return self.temp_path

    def __exit__(self, exc_type, exc_value, traceback):
        if self.temp_path and os.path.exists(self.temp_path):
            shutil.rmtree(self.temp_path)
        if self.original_cwd and os.path.exists(self.original_cwd):
            os.chdir(self.original_cwd)


def user_bloom(cmd, args=None, directory=None, auto_assert=True,
               return_io=True, silent=False):
    """Runs the given bloom cmd ('git-bloom-{cmd}') with the given args"""
    assert type(cmd) == str, \
        "user_bloom cmd takes str only, got " + str(type(cmd))
    if args is None:
        args = cmd.split()[1:]
        cmd = cmd.split()[0]
    assert type(args) in [list, tuple, str], \
        "user_bloom args takes [list, tuple, str] only, got " + \
        str(type(args))
    from pkg_resources import load_entry_point
    from bloom import __version__ as ver
    if not cmd.startswith('git-bloom-'):
        cmd = 'git-bloom-' + cmd
    if type(args) != list:
        if type(args) == str:
            args = args.split()
        args = list(args)
    with change_directory(directory if directory is not None else os.getcwd()):
        with redirected_stdio() as (out, err):
            func = load_entry_point('bloom==' + ver, 'console_scripts', cmd)
            try:
                ret = func(args) or 0
            except SystemExit as e:
                ret = e.code
                if ret != 0 and auto_assert:
                    raise
    if not silent:
        print("Command '{0}' returned '{1}':".format(cmd, ret))
        print(out.getvalue(), file=sys.stdout, end='')
        print(err.getvalue(), file=sys.stderr, end='')
    if return_io:
        return ret, out.getvalue(), err.getvalue()
    return ret


def user_cd(cmd, **kwargs):
    """
    Used in system tests to emulate a user changing directories

    Used in place of user('cd <new_directory>')
    """
    if type(cmd) is str:
        assert cmd is not '', "no arguments passed to cd, not allowed"
        cmd = cmd.split()
    new_directory = cmd[0]
    assert os.path.exists(new_directory), \
        "user tried to cd to '" + new_directory + "' which does not exist"
    os.chdir(new_directory)
    return 0


def user_echo(cmd, **kwargs):
    """
    Used to emulate the user echoing something even to a file with >>
    """
    assert type(cmd) is str, "user echo only takes str for the cmd argument"
    cmd = shlex.split(cmd)
    if len(cmd) == 1:
        print(cmd[0])
    elif len(cmd) == 3 and cmd[1] in ['>>', '>']:
        # echo into somefile
        assert not os.path.isdir(cmd[2]), \
            "user tried to echo into a directory: '" + cmd[2] + "'"
        if cmd[1] == '>>':
            mode = 'a'
        else:
            mode = 'w+'
        with open(cmd[2], mode) as f:
            f.write(cmd[0])
    return 0


def user_mkdir(cmd, **kwargs):
    """
    Used in system tests to emulte a user creating a directory
    """
    if type(cmd) is str:
        assert cmd is not '', "no arguments passed to mkdir, not allowed"
        cmd = cmd.split()
    if len(cmd) == 2:
        assert '-p' in cmd, "two args to mkdir, neither is '-p', not allowed"
        cmd.remove('-p')
        mkdir_cmd = os.makedirs
    else:
        mkdir_cmd = os.mkdir
    new_dir = cmd[0]
    assert not os.path.exists(new_dir), \
        "directory '" + new_dir + "' already exists"
    mkdir_cmd(new_dir)
    return 0


def user_touch(cmd, **kwargs):
    """
    Used to emulat a user touching a file
    """
    assert not os.path.exists(cmd), \
        "user tried to touch a file '" + cmd + "' but it exists"
    if os.path.exists(cmd):
        os.utime(cmd, None)
    else:
        open(cmd, 'w').close()


_special_user_commands = {
    'cd': user_cd,
    'echo': user_echo,
    'git-bloom-': user_bloom,
    'mkdir': user_mkdir,
    'touch': user_touch
}


def user(cmd, directory=None, auto_assert=True, return_io=False,
         bash_only=False, silent=True):
    """Used in system tests to emulate a user action"""
    if type(cmd) in [list, tuple]:
        cmd = ' '.join(cmd)
    if not bash_only:
        # Handle special cases
        for case in _special_user_commands:
            if cmd.startswith(case):
                cmd = ''.join(cmd.split(case)[1:]).strip()
                return _special_user_commands[case](
                    cmd,
                    directory=directory,
                    auto_assert=auto_assert,
                    return_io=return_io,
                    silent=silent
                )
    ret = -1
    try:
        p = Popen(cmd, shell=True, cwd=directory, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if out is not None and not isinstance(out, str):
            out = out.decode('utf-8')
        if err is not None and not isinstance(err, str):
            err = err.decode('utf-8')
        ret = p.returncode
    except CalledProcessError as err:
        ret = err.returncode
    if not silent:
        print(out, file=sys.stdout, end='')
        print(err, file=sys.stderr, end='')
    if auto_assert:
        assert ret == 0, \
            "user command '" + cmd + "' returned " + str(p.returncode)
    if return_io:
        return ret, out, err
    return ret
