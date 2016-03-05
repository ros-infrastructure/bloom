# Software License Agreement (BSD License)
#
# Copyright (c) 2013, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import print_function

import os
import re
import shutil
import string
import yaml

from tempfile import mkdtemp

from bloom.git import branch_exists
from bloom.git import create_branch
from bloom.git import has_changes
from bloom.git import get_remotes
from bloom.git import get_root
from bloom.git import inbranch
from bloom.git import show
from bloom.git import track_branches

from bloom.logging import error
from bloom.logging import fmt
from bloom.logging import info
from bloom.logging import sanitize

from bloom.util import execute_command
from bloom.util import my_copytree
from bloom.util import get_distro_list_prompt

BLOOM_CONFIG_BRANCH = 'master'
PLACEHOLDER_FILE = 'CONTENT_MOVED_TO_{0}_BRANCH'.format(BLOOM_CONFIG_BRANCH.upper())

config_spec = {
    'name': {
        '<name>': 'Name of the repository (used in the archive name)',
        'upstream': 'Default value, leave this as upstream if you are unsure'
    },
    'vcs_uri': {
        '<uri>': '''\
Any valid URI. This variable can be templated, for example an svn url
can be templated as such: "https://svn.foo.com/foo/tags/foo-:{version}"
where the :{version} token will be replaced with the version for this release.\
'''
    },
    'vcs_type': {
        'git': 'Upstream URI is a git repository',
        'hg': 'Upstream URI is a hg repository',
        'svn': 'Upstream URI is a svn repository',
        'tar': 'Upstream URI is a tarball'
    },
    'version': {
        ':{auto}': '''\
This means the version will be guessed from the devel branch.
This means that the devel branch must be set, the devel branch must exist,
and there must be a valid package.xml in the upstream devel branch.''',
        ':{ask}': '''\
This means that the user will be prompted for the version each release.
This also means that the upstream devel will be ignored.''',
        '<version>': '''\
This will be the version used.
It must be updated for each new upstream version.'''
    },
    'release_tag': {
        ':{version}': '''\
This means that the release tag will match the :{version} tag.
This can be further templated, for example: "foo-:{version}" or "v:{version}"

This can describe any vcs reference. For git that means {tag, branch, hash},
for hg that means {tag, branch, hash}, for svn that means a revision number.
For tar this value doubles as the sub directory (if the repository is
in foo/ of the tar ball, putting foo here will cause the contents of
foo/ to be imported to upstream instead of foo itself).
''',
        ':{ask}': '''\
This means the user will be prompted for the release tag on each release.
''',
        ':{none}': '''\
For svn and tar only you can set the release tag to :{none}, so that
it is ignored.  For svn this means no revision number is used.
'''
    },
    'devel_branch': {
        '<vcs reference>': '''\
Branch in upstream repository on which to search for the version.
This is used only when version is set to ':{auto}'.
''',
    },
    'ros_distro': {
        '<ROS distro>': "This can be any valid ROS distro, e.g. %s" %
                        get_distro_list_prompt()
    },
    'patches': {
        '<path in bloom branch>': '''\
This can be any valid relative path in the bloom branch. The contents
of this folder will be overlaid onto the upstream branch after each
import-upstream.  Additionally, any package.xml files found in the
overlay will have the :{version} string replaced with the current
version being released.''',
        ':{none}': '''\
Use this if you want to disable overlaying of files.'''
    },
    'release_repo_url': {
        '<url>': '''\
(optional) Used when pushing to remote release repositories. This is only
needed when the release uri which is in the rosdistro file is not writable.
This is useful, for example, when a releaser would like to use a ssh url
to push rather than a https:// url.
''',
        ':{none}': '''\
This indicates that the default release url should be used.
'''
    }
}


class PromptEntry(object):
    def __init__(self, name, default=None, values=None, prompt='', spec=None):
        self.values = values
        self.name = name
        self.default = default
        self.prompt = prompt
        self.spec = spec

    def __setattr__(self, key, value):
        if key == 'default' and self.values:
            if value not in self.values:
                error(
                    "Invalid input '{0}' for '{1}', acceptable values: {2}."
                    .format(value, self.name, self.values),
                    exit=True
                )
        object.__setattr__(self, key, value)

    def __str__(self):
        msg = fmt('@_' + sanitize(self.name) + ':@|')
        if self.spec is not None:
            for key, val in self.spec.items():
                msg += '\n  ' + key
                for line in val.splitlines():
                    msg += '\n    ' + line
        else:
            msg += '\n  ' + self.prompt
        msg += '\n '
        if self.default is None:
            msg += fmt(" @![@{yf}None@|@!]@|: ")
        else:
            msg += fmt(" @!['@{yf}" + sanitize(self.default) + "@|@!']@|: ")
        return msg

DEFAULT_TEMPLATE = {
    'name': PromptEntry('Repository Name', spec=config_spec['name'], default='upstream'),
    'vcs_uri': PromptEntry('Upstream Repository URI', spec=config_spec['vcs_uri']),
    'vcs_type': PromptEntry(
        'Upstream VCS Type', default='git', spec=config_spec['vcs_type'],
        values=['git', 'hg', 'svn', 'tar']),
    'version': PromptEntry('Version', default=':{auto}', spec=config_spec['version']),
    'release_tag': PromptEntry('Release Tag', default=':{version}', spec=config_spec['release_tag']),
    'devel_branch': PromptEntry('Upstream Devel Branch', spec=config_spec['devel_branch']),
    'patches': PromptEntry('Patches Directory', spec=config_spec['patches']),
    'ros_distro': PromptEntry('ROS Distro', default='indigo', spec=config_spec['ros_distro']),
    'release_repo_url': PromptEntry('Release Repository Push URL', spec=config_spec['release_repo_url']),
    'release_inc': -1,
    'actions': [
        'bloom-export-upstream :{vcs_local_uri} :{vcs_type}'
        ' --tag :{release_tag} --display-uri :{vcs_uri}'
        ' --name :{name} --output-dir :{archive_dir_path}',
        'git-bloom-import-upstream :{archive_path} :{patches}'
        ' --release-version :{version} --replace',
        'git-bloom-generate -y rosrelease :{ros_distro}'
        ' --source upstream -i :{release_inc}',
        'git-bloom-generate -y rosdebian --prefix release/:{ros_distro}'
        ' :{ros_distro} -i :{release_inc} --os-name ubuntu',
        'git-bloom-generate -y rosdebian --prefix release/:{ros_distro}'
        ' :{ros_distro} -i :{release_inc} --os-name debian --os-not-required',
        'git-bloom-generate -y rosrpm --prefix release/:{ros_distro}'
        ' :{ros_distro} -i :{release_inc}'
    ]
}

CUSTOM_TEMPLATE = {
    'reference': ':{ask}',
    'patches': ':{name}'
}

config_template = {
    'third-party': CUSTOM_TEMPLATE,
    None: {}
}


def verify_track(track_name, track):
    upconvert_bloom_to_config_branch()
    for entry in DEFAULT_TEMPLATE:
        if entry not in track:
            error("Track '{0}' is missing configuration ".format(track_name) +
                  "'{0}', it may be out of date, please run 'git-bloom-config edit {1}'."
                  .format(entry, track_name), exit=True)


class ConfigTemplate(string.Template):
    delimiter = ':'


def template_str(line, settings):
    t = ConfigTemplate(line)
    return t.substitute(settings)


def write_tracks_dict_raw(tracks_dict, cmt_msg=None, directory=None):
    upconvert_bloom_to_config_branch()
    cmt_msg = cmt_msg if cmt_msg is not None else 'Modified tracks.yaml'
    with inbranch(BLOOM_CONFIG_BRANCH):
        with open('tracks.yaml', 'w') as f:
            f.write(yaml.safe_dump(tracks_dict, indent=2, default_flow_style=False))
        execute_command('git add tracks.yaml', cwd=directory)
        execute_command('git commit --allow-empty -m "{0}"'.format(cmt_msg),
                        cwd=directory)

version_regex = re.compile(r'^\d+\.\d+\.\d+$')


def validate_track_versions(tracks_dict):
    for track in tracks_dict['tracks'].values():
        if 'version' in track:
            if track['version'] in [':{ask}', ':{auto}']:
                continue
            if version_regex.match(track['version']) is None:
                raise ValueError(
                    "Invalid version '{0}', it must be formatted as 'MAJOR.MINOR.PATCH'"
                    .format(track['version']))


def get_tracks_dict_raw(directory=None):
    upconvert_bloom_to_config_branch()
    if not branch_exists(BLOOM_CONFIG_BRANCH):
        info("Creating '{0}' branch.".format(BLOOM_CONFIG_BRANCH))
        create_branch(BLOOM_CONFIG_BRANCH, orphaned=True, directory=directory)
    tracks_yaml = show(BLOOM_CONFIG_BRANCH, 'tracks.yaml', directory=directory)
    if not tracks_yaml:
        write_tracks_dict_raw(
            {'tracks': {}}, 'Initial tracks.yaml', directory=directory
        )
        tracks_yaml = show(BLOOM_CONFIG_BRANCH, 'tracks.yaml',
                           directory=directory)
    tracks_dict = yaml.load(tracks_yaml)
    validate_track_versions(tracks_dict)
    return tracks_dict

_has_checked_bloom_branch = False


def check_for_multiple_remotes():
    if get_root() is None:
        return
    remotes = get_remotes()
    if len(remotes) < 0:
        error("Current git repository has no remotes. "
              "If you are running bloom-release, please change directories.",
              exit=True)
    if len(remotes) > 1:
        error("Current git repository has multiple remotes. "
              "If you are running bloom-release, please change directories.",
              exit=True)


def upconvert_bloom_to_config_branch():
    global _has_checked_bloom_branch
    if _has_checked_bloom_branch:
        return
    # Assert that this repository does not have multiple remotes
    check_for_multiple_remotes()
    if get_root() is None:
        # Not a git repository
        return
    track_branches(['bloom', BLOOM_CONFIG_BRANCH])
    if show('bloom', PLACEHOLDER_FILE) is not None:
        return
    if show('bloom', 'bloom.conf') is not None:
        # Wait for the bloom.conf upconvert...
        return
    if not branch_exists('bloom'):
        return
    _has_checked_bloom_branch = True
    info("Moving configurations from deprecated 'bloom' branch "
         "to the '{0}' branch.".format(BLOOM_CONFIG_BRANCH))
    tmp_dir = mkdtemp()
    git_root = get_root()
    try:
        # Copy the new upstream source into the temporary directory
        with inbranch('bloom'):
            ignores = ('.git', '.gitignore', '.svn', '.hgignore', '.hg', 'CVS')
            configs = os.path.join(tmp_dir, 'configs')
            my_copytree(git_root, configs, ignores)
            if [x for x in os.listdir(os.getcwd()) if x not in ignores]:
                execute_command('git rm -rf ./*')
            with open(PLACEHOLDER_FILE, 'w') as f:
                f.write("""\
This branch ('bloom') has been deprecated in favor of storing settings and overlay files in the master branch.

Please goto the master branch for anything which referenced the bloom branch.

You can delete this branch at your convenience.
""")
            execute_command('git add ' + PLACEHOLDER_FILE)
            if has_changes():
                execute_command('git commit -m "DEPRECATING BRANCH"')
        if not branch_exists(BLOOM_CONFIG_BRANCH):
            info("Creating '{0}' branch.".format(BLOOM_CONFIG_BRANCH))
            create_branch(BLOOM_CONFIG_BRANCH, orphaned=True)
        with inbranch(BLOOM_CONFIG_BRANCH):
            my_copytree(configs, git_root)
            execute_command('git add ./*')
            if has_changes():
                execute_command('git commit -m '
                                '"Moving configs from bloom branch"')
    finally:
        # Clean up
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
