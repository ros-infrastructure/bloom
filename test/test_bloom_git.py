import os
from shutil import rmtree
from tempfile import mkdtemp


def test_get_current_branch():
    # Create a temporary workfolder
    tmp_dir = mkdtemp()
    from subprocess import check_call, PIPE
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
    from bloom.git import track_branches
    track_branches(['bloom', 'upstream'], clone_dir)
    output = check_output('git branch --no-color', shell=True, cwd=clone_dir)
    assert output == '  bloom\n* master\n  upstream\n'
    track_branches(cwd=clone_dir)
    output = check_output('git branch --no-color', shell=True, cwd=clone_dir)
    assert output == '  bloom\n* master\n  refactor\n  upstream\n', \
           output + ' == `  bloom\n* master\n  refactor\n  upstream\n`'
    track_branches(['fake'], clone_dir)
    output = check_output('git branch', shell=True, cwd=clone_dir)
    assert output.count('fake') == 0
    rmtree(tmp_dir)


def test_get_last_tag_by_date():
    from tempfile import mkdtemp
    tmp_dir = mkdtemp()
    git_dir = os.path.join(tmp_dir, 'repo')
    os.makedirs(git_dir)
    from subprocess import check_call, PIPE
    check_call('git init .', shell=True, cwd=git_dir, stdout=PIPE)
    check_call('touch example.txt', shell=True, cwd=git_dir, stdout=PIPE)
    check_call('git add *', shell=True, cwd=git_dir, stdout=PIPE)
    check_call('git commit -m "Init"', shell=True, cwd=git_dir, stdout=PIPE)
    from bloom.git import get_last_tag_by_date
    assert get_last_tag_by_date(git_dir) == ''
    check_call('git tag upstream/0.3.2', shell=True, cwd=git_dir, stdout=PIPE)
    check_call('git tag upstream/0.3.3', shell=True, cwd=git_dir, stdout=PIPE)
    check_call('git tag upstream/0.3.4', shell=True, cwd=git_dir, stdout=PIPE)
    check_call('git tag upstream/0.3.5', shell=True, cwd=git_dir, stdout=PIPE)
    assert get_last_tag_by_date(git_dir) == 'upstream/0.3.5'
    from shutil import rmtree
    rmtree(tmp_dir)
