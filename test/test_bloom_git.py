import os
from shutil import rmtree, copy
from tempfile import mkdtemp

from subprocess import check_call, PIPE


def test_get_current_branch():
    # Create a temporary workfolder
    tmp_dir = mkdtemp()
    # Create a test repo
    check_call('git init .', shell=True, cwd=tmp_dir, stdout=PIPE)

    from bloom.git import get_current_branch
    assert get_current_branch(tmp_dir) == None, \
           get_current_branch(tmp_dir) + ' == None'

    # Make a commit
    check_call('touch example.txt', shell=True, cwd=tmp_dir, stdout=PIPE)
    check_call('git add *', shell=True, cwd=tmp_dir, stdout=PIPE)
    check_call('git commit -a -m "Initial commit."', shell=True, cwd=tmp_dir,
               stdout=PIPE)
    # Make a branch
    check_call('git branch bloom', shell=True, cwd=tmp_dir, stdout=PIPE)

    assert get_current_branch(tmp_dir) == 'master'

    # Change to the bloom branch
    check_call('git checkout bloom', shell=True, cwd=tmp_dir, stdout=PIPE,
                stderr=PIPE)

    assert get_current_branch(tmp_dir) == 'bloom'

    from vcstools import VcsClient
    client = VcsClient('git', tmp_dir)
    spec = client.get_version('master')
    check_call('git checkout {0}'.format(spec), shell=True, cwd=tmp_dir,
               stdout=PIPE, stderr=PIPE)

    assert get_current_branch(tmp_dir) == None, \
           get_current_branch(tmp_dir) + ' == None'

    rmtree(tmp_dir)


def test_track_branches():
    tmp_dir = mkdtemp()
    orig_dir = os.path.join(tmp_dir, 'orig')
    clone_dir = os.path.join(tmp_dir, 'clone')
    os.makedirs(orig_dir)
    os.makedirs(clone_dir)
    from subprocess import check_call, PIPE
    from bloom.util import check_output
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
    from bloom.git import track_branches
    track_branches(['bloom', 'upstream'], clone_dir)
    output = check_output('git branch --no-color', shell=True, cwd=clone_dir)
    assert output == '  bloom\n* master\n  upstream\n', \
           '\n' + str(output) + '\n == \n' + '  bloom\n* master\n  upstream\n'
    track_branches(directory=clone_dir)
    output = check_output('git branch --no-color', shell=True, cwd=clone_dir)
    assert output == '  bloom\n* master\n  refactor\n  upstream\n', \
           output + ' == `  bloom\n* master\n  refactor\n  upstream\n`'
    track_branches(['fake'], clone_dir)
    output = check_output('git branch', shell=True, cwd=clone_dir)
    assert output.count('fake') == 0
    rmtree(tmp_dir)


def create_git_repo():
    from tempfile import mkdtemp
    tmp_dir = mkdtemp()
    git_dir = os.path.join(tmp_dir, 'repo')
    os.makedirs(git_dir)
    check_call('git init .', shell=True, cwd=git_dir, stdout=PIPE)
    check_call('touch example.txt', shell=True, cwd=git_dir, stdout=PIPE)
    check_call('git add *', shell=True, cwd=git_dir, stdout=PIPE)
    check_call('git commit -m "Init"', shell=True, cwd=git_dir, stdout=PIPE)
    return tmp_dir, git_dir


def test_get_last_tag_by_date():
    tmp_dir, git_dir = create_git_repo()
    from bloom.git import get_last_tag_by_date
    assert get_last_tag_by_date(git_dir) == ''
    check_call('git tag upstream/0.3.2', shell=True, cwd=git_dir, stdout=PIPE)
    check_call('git tag upstream/0.3.3', shell=True, cwd=git_dir, stdout=PIPE)
    check_call('git tag upstream/0.3.4', shell=True, cwd=git_dir, stdout=PIPE)
    check_call('git tag upstream/0.3.5', shell=True, cwd=git_dir, stdout=PIPE)
    assert get_last_tag_by_date(git_dir) == 'upstream/0.3.5'
    rmtree(tmp_dir)


def test_show():
    tmp_dir, git_dir = create_git_repo()
    from bloom.git import show
    assert show('master', 'something.txt') == None
    with open(os.path.join(git_dir, 'something.txt'), 'w+') as f:
        f.write('v1\n')
    assert show('master', 'something.txt') == None
    check_call('git add something.txt', shell=True, cwd=git_dir,
               stdout=PIPE)
    check_call('git commit -am "added something.txt"', shell=True, cwd=git_dir,
               stdout=PIPE)
    assert show('master', 'something.txt', git_dir) == 'v1\n', \
           str(show('master', 'something.txt', git_dir)) + ' == v1'
    os.makedirs(os.path.join(git_dir, 'adir'))
    copy(os.path.join(git_dir, 'something.txt'), os.path.join(git_dir, 'adir'))
    with open(os.path.join(git_dir, 'adir', 'something.txt'), 'a') as f:
        f.write('v2\n')
    check_call('git add adir', shell=True, cwd=git_dir,
               stdout=PIPE)
    check_call('git commit -am "made a subfolder"', shell=True, cwd=git_dir,
               stdout=PIPE)
    assert show('master', os.path.join('adir', 'something.txt'), git_dir) == 'v1\nv2\n'
    rmtree(tmp_dir)
