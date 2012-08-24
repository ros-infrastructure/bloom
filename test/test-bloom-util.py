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


def test_track_all_git_branches():
    from tempfile import mkdtemp
    tmp_dir = mkdtemp()
    orig_dir = os.path.join(tmp_dir, 'orig')
    clone_dir = os.path.join(tmp_dir, 'clone')
    os.makedirs(orig_dir)
    os.makedirs(clone_dir)
    from subprocess import check_call, PIPE, check_output
    check_call('git init .', shell=True, cwd=orig_dir, stdout=PIPE)
    check_call('touch example.txt', shell=True, cwd=orig_dir, stdout=PIPE)
    check_call('git add *', shell=True, cwd=orig_dir, stdout=PIPE)
    check_call('git commit -m "Init"', shell=True, cwd=orig_dir, stdout=PIPE)
    check_call('git branch bloom', shell=True, cwd=orig_dir, stdout=PIPE)
    check_call('git branch upstream', shell=True, cwd=orig_dir, stdout=PIPE)
    check_call('git branch refactor', shell=True, cwd=orig_dir, stdout=PIPE)
    from vcstools import VcsClient
    clone = VcsClient('git', clone_dir)
    clone.checkout('file://{0}'.format(orig_dir), 'master')
    output = check_output('git branch --no-color', shell=True, cwd=clone_dir)
    assert output == '* master\n'
    from bloom.util import track_all_git_branches
    track_all_git_branches(['bloom', 'upstream'], clone_dir)
    output = check_output('git branch --no-color', shell=True, cwd=clone_dir)
    assert output == '  bloom\n* master\n  upstream\n'
    track_all_git_branches(cwd=clone_dir)
    output = check_output('git branch --no-color', shell=True, cwd=clone_dir)
    assert output == '  bloom\n* master\n  refactor\n  upstream\n', \
           output + ' == `  bloom\n* master\n  refactor\n  upstream\n`'
