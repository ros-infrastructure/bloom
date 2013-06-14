"""
This system test tests the scenario of setting up a new bloom repository.
"""

import os

import yaml

from ..utils.common import in_temporary_directory
from ..utils.common import bloom_answer
from ..utils.common import user

from bloom.config import BLOOM_CONFIG_BRANCH

from bloom.git import branch_exists
from bloom.git import inbranch


@in_temporary_directory
def test_create_a_bloom_repository(directory=None):
    """
    Create a Bloom Repository:
        User creates a new release repository, and calls git-bloom-config new.

    actions:
        - user creates a folder
        - user calls 'git init .' in that folder
        - user calls 'git-bloom-config new <track name>'

    expects:
        - bloom to ask the user if initialization is desired
        - bloom prompts the user for input on the settings
        - bloom branch to be created
        - tracks.yaml to be in bloom branch with appropriate contents
    """
    # Setup
    user('mkdir new_repo')
    user('cd new_repo')
    user('git init .')
    # Test bloom command
    with bloom_answer(['', 'foo', 'https://github.com/bar/foo.git']):
        r = user('git-bloom-config new foo', return_io=True, silent=False)
        _, out, err = r
    assert out.count('ontinue') > 0, \
        "git-bloom-config didn't ask about git init:\n```\n" + out + "\n```"
    assert branch_exists(BLOOM_CONFIG_BRANCH), \
        "branch '{0}' does not exist".format(BLOOM_CONFIG_BRANCH)
    with inbranch(BLOOM_CONFIG_BRANCH):
        assert os.path.exists('tracks.yaml'), \
            "no tracks.yaml file in the 'bloom' branch"
        with open('tracks.yaml', 'r') as f:
            tracks_dict = yaml.load(f.read())
        assert 'tracks' in tracks_dict, "bad bloom configurations"
        assert 'foo' in tracks_dict['tracks'], "bad bloom configurations"
        track = tracks_dict['tracks']['foo']
        assert 'vcs_uri' in track, "bad bloom configurations"
        assert 'https://github.com/bar/foo.git' == track['vcs_uri'], \
            "bad bloom configurations" + str(track)
    # Assert no question on the second attempt
    with bloom_answer(bloom_answer.ASSERT_NO_QUESTION):
        user('git-bloom-config')


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
        r = user('git-bloom-config --quite new foo',
                 auto_assert=False)
    assert r != 0, "actually returned " + str(r)


def setup_git_repo(directory=None):
    user('mkdir new_repo')
    user('cd new_repo')
    user('git init .')
    user('touch README.md')
    user('git add README.md')
    user('git commit --allow-empty -m "Initial commit"')


@in_temporary_directory
def test_call_config_with_local_changes(directory=None):
    """
    Call git-bloom-config on a git repository with local changes.
    """
    setup_git_repo(directory)
    user('echo "some text" >> README.md')
    # Try to run bloom
    with bloom_answer(bloom_answer.ASSERT_NO_QUESTION):
        r = user('git-bloom-config --quite new foo',
                 auto_assert=False)
    assert r != 0, "actually returned " + str(r)


@in_temporary_directory
def test_call_config_with_untracked_files(directory=None):
    """
    Call git-bloom-config on a git repository with untracked files.
    """
    setup_git_repo(directory)
    user('echo "some text" > somefile.txt')
    # Try to run bloom
    with bloom_answer(bloom_answer.ASSERT_NO_QUESTION):
        r = user('git-bloom-config --quite new foo',
                 auto_assert=False)
    assert r != 0, "actually returned " + str(r)
