import os
import shutil


def test_create_temporary_directory():
    from bloom.util import create_temporary_directory

    tmp_dir = create_temporary_directory()
    assert os.path.exists(tmp_dir)
    shutil.rmtree(tmp_dir)

    if os.path.exists('/tmp'):
        os.mkdir('/tmp/test-bloom-util')
        tmp_dir = create_temporary_directory('/tmp/test-bloom-util')
        assert os.path.exists(tmp_dir)
        shutil.rmtree('/tmp/test-bloom-util')


def test_ANSI_colors():
    from bloom.util import ansi, enable_ANSI_colors, disable_ANSI_colors

    control_str = '\033[1m\033[3m\033[31mBold and Italic and Red \033[0mPlain'
    control_str_disable = 'Bold and Italic and Red Plain'

    test_str = ansi('boldon') + ansi('italicson') + ansi('redf') \
             + 'Bold and Italic and Red ' + ansi('reset') + 'Plain'
    assert control_str == test_str, \
           '{0} == {1}'.format(control_str, test_str)

    disable_ANSI_colors()
    test_str = ansi('boldon') + ansi('italicson') + ansi('redf') \
             + 'Bold and Italic and Red ' + ansi('reset') + 'Plain'
    assert control_str_disable == test_str, \
           '{0} == {1}'.format(control_str_disable, test_str)

    enable_ANSI_colors()
    test_str = ansi('boldon') + ansi('italicson') + ansi('redf') \
             + 'Bold and Italic and Red ' + ansi('reset') + 'Plain'
    assert control_str == test_str, \
           '{0} == {1}'.format(control_str, test_str)


def test_maybe_continue():
    from subprocess import Popen, PIPE
    this_dir = os.path.abspath(os.path.dirname(__file__))
    cmd = '/usr/bin/env python maybe_continue_helper.py'

    p = Popen(cmd, shell=True, cwd=this_dir, stdin=PIPE, stdout=PIPE)
    p.communicate('y')
    assert p.returncode == 0

    p = Popen(cmd, shell=True, cwd=this_dir, stdin=PIPE, stdout=PIPE)
    p.communicate('n')
    assert p.returncode == 1


def test_get_current_git_branch():
    from tempfile import mkdtemp
    # Create a temporary workfolder
    tmp_dir = mkdtemp()
    from subprocess import check_call, PIPE
    # Create a test repo
    check_call('git init .', shell=True, cwd=tmp_dir, stdout=PIPE)

    from bloom.util import get_current_git_branch
    assert get_current_git_branch(tmp_dir) == None, \
           get_current_git_branch(tmp_dir) + ' == None'

    # Make a commit
    check_call('touch example.txt', shell=True, cwd=tmp_dir, stdout=PIPE)
    check_call('git add *', shell=True, cwd=tmp_dir, stdout=PIPE)
    check_call('git commit -a -m "Initial commit."', shell=True, cwd=tmp_dir,
               stdout=PIPE)
    # Make a branch
    check_call('git branch bloom', shell=True, cwd=tmp_dir, stdout=PIPE)

    assert get_current_git_branch(tmp_dir) == 'master'

    # Change to the bloom branch
    check_call('git checkout bloom', shell=True, cwd=tmp_dir, stdout=PIPE,
                stderr=PIPE)

    assert get_current_git_branch(tmp_dir) == 'bloom'

    from vcstools import VcsClient
    client = VcsClient('git', tmp_dir)
    spec = client.get_version('master')
    check_call('git checkout {0}'.format(spec), shell=True, cwd=tmp_dir,
               stdout=PIPE, stderr=PIPE)

    assert get_current_git_branch(tmp_dir) == None, \
           get_current_git_branch(tmp_dir) + ' == None'

    from shutil import rmtree
    rmtree(tmp_dir)
