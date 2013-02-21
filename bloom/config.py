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

import yaml
import string

from bloom.git import inbranch
from bloom.git import branch_exists
from bloom.git import create_branch
from bloom.git import show

from bloom.logging import error
from bloom.logging import fmt
from bloom.logging import info
from bloom.logging import sanitize

from bloom.util import execute_command

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
        '<ROS distro>': 'This can be any valid ROS distro, e.g. groovy, hydro'
    },
    'patches': {
        '<path in bloom branch>': '''\
This can be any valid relative path in the bloom branch. The contents
of this folder will be overlaid onto the upstream branch after each
import-upstream.  Additionally, any package.xml files found in the
overlay will have the :{version} string replaced with the current
version being released.'''
    }
}


class PromptEntry(object):
    def __init__(self, name, default=None, values=None, prompt='', spec=None):
        object.__setattr__(self, 'values', values)
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
            for key, val in self.spec.iteritems():
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
    'name': PromptEntry('Repository Name',
        spec=config_spec['name'], default='upstream'),
    'vcs_uri': PromptEntry('Upstream Repository URI',
        spec=config_spec['vcs_uri']),
    'vcs_type': PromptEntry('Upstream VCS Type', default='git',
        spec=config_spec['vcs_type'], values=['git', 'hg', 'svn', 'tar']),
    'version': PromptEntry('Version', default=':{auto}',
        spec=config_spec['version']),
    'release_tag': PromptEntry('Release Tag', default=':{version}',
        spec=config_spec['release_tag']),
    'devel_branch': PromptEntry('Upstream Devel Branch',
        spec=config_spec['devel_branch']),
    'patches': PromptEntry('Patches Directory',
        spec=config_spec['patches']),
    'ros_distro': PromptEntry('ROS Distro', default='groovy',
        spec=config_spec['ros_distro']),
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
    for entry in DEFAULT_TEMPLATE:
        if entry not in track:
            error("Track '{0}' is missing configuration '{1}', it may be out of date, please run 'git-bloom-config edit {0}'."
                .format(track_name, entry), exit=True)


class ConfigTemplate(string.Template):
    delimiter = ':'


def template_str(line, settings):
    t = ConfigTemplate(line)
    return t.substitute(settings)


def write_tracks_dict_raw(tracks_dict, cmt_msg=None, directory=None):
    cmt_msg = cmt_msg if cmt_msg is not None else 'Modified tracks.yaml'
    with inbranch('bloom'):
        with open('tracks.yaml', 'w') as f:
            f.write(yaml.dump(tracks_dict, indent=2, default_flow_style=False))
        execute_command('git add tracks.yaml', cwd=directory)
        execute_command('git commit --allow-empty -m "{0}"'.format(cmt_msg),
            cwd=directory)


def get_tracks_dict_raw(directory=None):
    if not branch_exists('bloom'):
        info("Creating bloom branch.")
        create_branch('bloom', orphaned=True, directory=directory)
    tracks_yaml = show('bloom', 'tracks.yaml', directory=directory)
    if not tracks_yaml:
        write_tracks_dict_raw(
            {'tracks': {}}, 'Initial tracks.yaml', directory=directory
        )
        tracks_yaml = show('bloom', 'tracks.yaml', directory=directory)
    try:
        return yaml.load(tracks_yaml)
    except:
        # TODO handle yaml errors
        raise
