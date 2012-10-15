"""
This system test tests the scenario of setting up a new bloom repository.
"""

import os

from ..utils import in_temporary_directory
from ..utils import bloom_answer
from ..utils import user

from bloom.git import branch_exists
from bloom.git import inbranch

from bloom.util import code


@in_temporary_directory
def test_create_a_bloom_repository(directory=None):
    """
    Create a Bloom Repository:
        User creates a new release repository, and immediately calls
        git-bloom-config.

    actions:
        - user creates a folder
        - user calls 'git init .' in that folder
        - user calls 'git-bloom-config <url> <type> [<branch>]'

    expects:
        - bloom to ask the user if initialization is desired
        - bloom branch to be created
        - bloom.conf to be in bloom branch with appropriate contents
    """
    # Setup
    user('mkdir new_repo')
    assert os.getcwd() == directory, str(os.getcwd()) + " == " + str(directory)
    user('cd new_repo')
    assert os.getcwd() != directory, str(os.getcwd()) + " != " + str(directory)
    user('git init .')
    # Test bloom command
    with bloom_answer('y'):
        r = user('git-bloom-config https://github.com/foo/foo.git git devel',
                 return_io=True)
        _, out, err = r
    assert out.count('ontinue') > 0, \
           "git-bloom-config didn't ask about git init: \n`" + out + "`"
    assert branch_exists('bloom'), "branch 'bloom' does not exist"
    with inbranch('bloom'):
        assert os.path.exists('bloom.conf'), \
               "no bloom.conf file in the 'bloom' branch"
        bloom_file = open('bloom.conf').read()
        assert bloom_file.count('foo/foo.git') > 0, "bad content in bloom.conf"
        assert bloom_file.count(' git') > 0, "bad content in bloom.conf"
        assert bloom_file.count(' devel') > 0, "bad content in bloom.conf"
    # Assert no question on the second attempt
    with bloom_answer(bloom_answer.ASSERT_NO_QUESTION):
        user('git-bloom-config https://github.com/foo/foo.git git devel')


@in_temporary_directory
def test_call_config_outside_of_git_repo(directory=None):
    """
    Call git-bloom-config Outside of a Git Repository:
        User calls git-bloom-config outside of a git repository.

    actions:
        - user calls 'git-bloom-config'

    expects:
        - git-bloom-config should error out with an appropriate message
    """
    with bloom_answer(bloom_answer.ASSERT_NO_QUESTION):
        r = user('git-bloom-config https://github.com/foo/foo.git git devel',
                 auto_assert=False)
    assert r == code.NOT_A_GIT_REPOSITORY, "actually returned " + str(r)


def setup_git_repo(directory=None):
    user('mkdir new_repo')
    user('cd new_repo')
    user('git init .')
    user('touch README.md')
    user('git add README.md')
    user('git commit -m "Initial commit"')


@in_temporary_directory
def test_call_config_with_local_changes(directory=None):
    """
    Call git-bloom-config on a git repository with local changes.
    """
    setup_git_repo(directory)
    user('echo "some text" >> README.md')
    # Try to run bloom
    with bloom_answer(bloom_answer.ASSERT_NO_QUESTION):
        r = user('git-bloom-config https://gh.com/foo/foo.git git --quiet',
                 auto_assert=False)
    assert r == code.GIT_HAS_LOCAL_CHANGES, "actually returned " + str(r)


@in_temporary_directory
def test_call_config_with_untracked_files(directory=None):
    """
    Call git-bloom-config on a git repository with local changes.
    """
    setup_git_repo(directory)
    user('echo "some text" > somefile.txt')
    # Try to run bloom
    with bloom_answer(bloom_answer.ASSERT_NO_QUESTION):
        r = user('git-bloom-config https://gh.com/foo/foo.git git --quiet',
                 auto_assert=False)
    assert r == code.GIT_HAS_UNTRACKED_FILES, "actually returned " + str(r)
