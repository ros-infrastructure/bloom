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

import argparse
import copy
import json
import subprocess
import sys

from bloom.config import write_track
from bloom.config import get_tracks_dict_raw
from bloom.config import write_tracks_dict_raw

from bloom.git import branch_exists
from bloom.git import ls_tree
from bloom.git import ensure_clean_working_env
from bloom.git import GitClone
from bloom.git import get_root
from bloom.git import inbranch

from bloom.logging import fmt
from bloom.logging import debug
from bloom.logging import error
from bloom.logging import info

from bloom.util import add_global_arguments
from bloom.util import execute_command
from bloom.util import check_output
from bloom.util import handle_global_arguments
from bloom.util import maybe_continue

AUTO = ':{auto}'
ASK = ':{ask}'


class PromptEntry(object):
    def __init__(self, name, default=None, values=None, prompt=''):
        self.name = name
        self.default = default
        self.values = values
        self.prompt = prompt

    def __str__(self):
        msg = '@_' + self.name + ':@|\n  '
        msg += self.prompt
        if self.values:
            msg += ' (' + ', '.join(self.values) + ')'
        msg += '\n '
        if self.default is None:
            msg += " @![@{yf}None@|@!]@|: "
        else:
            msg += " @!['@{{yf}}{0}@|@!']@|: ".format(self.default)
        return fmt(msg)

DEFAULT_TEMPLATE = {
    'vcs_uri': PromptEntry('Upstream Repository URI',
        prompt='URI of the repository which holds the project source code'),
    'vcs_type': PromptEntry('Upstream VCS Type', default='git',
        prompt='Type of the upstream VCS', values=['git', 'hg', 'svn', 'tar']),
    'version': PromptEntry('Version', default=AUTO,
        prompt='Current version tagged in upstream ({0} trys to guess from upstream devel branch, {1} will ask each release)'.format(AUTO, ASK)),
    'release_tag': PromptEntry('Release Tag', default=AUTO,
        prompt='VCS tag to import from the next release from. ({0} will guess this from the version, {1} will ask each release for the tag to import from)'.format(AUTO, ASK)),
    'devel_branch': PromptEntry('Upstream Devel Branch',
        prompt='Upstream branch on which development happens (used when version is set to {0})'.format(AUTO)),
    'patches': PromptEntry('Patched Directory',
        prompt='Directory located relatively from the root of the bloom branch, which is overlayed onto the upstream repository just after each import.\n  Package.xml versions are also templated before overlay.'),
    'ros_distro': PromptEntry('ROS Distro', default='groovy',
        prompt='ROS distrobution (groovy, hydro, etc...)'),
    'release_inc': 0,
    'actions': [
        'git-bloom-import-upstream', ['--replace'],
        'git-bloom-generate', ['-y', 'rosrelease', '--source', 'upstream'],
        'git-bloom-generate', ['-y', 'rosdebian', '--prefix', 'release',
            ':{ros_distro}', '-i', ':{release_inc}']
    ]
}

template_entry_order = [
    'vcs_uri',
    'vcs_type',
    'version',
    'release_tag',
    'devel_branch',
    'ros_distro',
    'patches'
]

CUSTOM_TEMPLATE = {
    'reference': ASK,
    'patches': ':name'
}

config_template = {
    'third-party': CUSTOM_TEMPLATE,
    None: {}
}


@inbranch('bloom')
def convert_old_bloom_conf():
    track = 'convert'
    track_dict = copy.copy(DEFAULT_TEMPLATE)
    cmd = 'git config -f bloom.conf bloom.upstream'
    upstream_repo = check_output(cmd, shell=True).strip()
    cmd = 'git config -f bloom.conf bloom.upstreamtype'
    upstream_type = check_output(cmd, shell=True).strip()
    try:
        cmd = 'git config -f bloom.conf bloom.upstreambranch'
        upstream_branch = check_output(cmd, shell=True).strip()
    except subprocess.CalledProcessError:
        upstream_branch = ''
    for key in template_entry_order:
        if key == 'vcs_uri':
            track_dict[key] = upstream_repo
            continue
        if key == 'vcs_type':
            track_dict[key] = upstream_type
            continue
        if key == 'vcs_uri':
            track_dict[key] = upstream_branch or None
            continue
        track_dict[key] = track_dict[key].default
    debug('Converted bloom.conf:')
    with open('bloom.conf', 'r') as f:
        debug(f.read())
    debug('To this track:')
    debug(str({track: track_dict}))
    write_track(track, track_dict)
    execute_command('git rm bloom.conf', shell=True)
    execute_command('git commit -m "Removed bloom.conf"', shell=True)


def show_current():
    bloom_ls = ls_tree('bloom')
    bloom_files = [f for f, t in bloom_ls.iteritems() if t == 'file']
    if 'bloom.conf' in bloom_files:
        info("Old bloom.conf file detected, up converting...")
        convert_old_bloom_conf()
        bloom_ls = ls_tree('bloom')
        bloom_files = [f for f, t in bloom_ls.iteritems() if t == 'file']
    if 'tracks.json' in bloom_files:
        info(json.dumps(get_tracks_dict_raw(), indent=2))


def check_git_init():
    if get_root() is None:
        error("Not in a valid git repository", exit=True)
    cmd = 'git show-ref --heads'
    result = execute_command(cmd, shell=True, autofail=False,
        silent_error=True)
    if result != 0:
        info("Freshly initialized git repository detected.")
        info("An initial empty commit is going to be made.")
        if not maybe_continue():
            error("Answered no to continue, exiting.", exit=True)
        # Make an initial empty commit
        execute_command('git commit -m "initial commit" --allow-empty')


def new(args):
    tracks_dict = get_tracks_dict_raw()
    if args.track in tracks_dict['tracks']:
        error("Cannot create track '{0}' beause it exists.".format(args.track))
        error("Run `git-bloom-config edit {0}` instead.".format(args.track),
            exit=True)
    track = copy.copy(DEFAULT_TEMPLATE)
    template = copy.copy(config_template[args.template])
    for key in template_entry_order:
        if key in template:
            track[key].default = template[key]
        if track[key].default == ':name':
            track[key].default = args.track
        ret = raw_input(str(track[key]))
        if ret:
            track[key] = ret
        else:
            track[key] = str(track[key].default)
    tracks_dict['tracks'][args.track] = track
    write_tracks_dict_raw(tracks_dict)
    info("Created '{0}' track.".format(args.track))


def show(args):
    tracks_dict = get_tracks_dict_raw()
    if args.track not in tracks_dict['tracks']:
        error("Track '{0}' does not exist.".format(args.track), exit=True)
    info(json.dumps({args.track: tracks_dict['tracks'][args.track]}, indent=2))


def edit(args):
    tracks_dict = get_tracks_dict_raw()
    if args.track not in tracks_dict['tracks']:
        error("Track '{0}' does not exist.".format(args.track), exit=True)
    for key in template_entry_order:
        pe = DEFAULT_TEMPLATE[key]
        pe.default = tracks_dict['tracks'][args.track][key]
        ret = raw_input(str(pe))
        if ret:
            tracks_dict['tracks'][args.track][key] = ret
    write_tracks_dict_raw(tracks_dict)


def delete(args):
    tracks_dict = get_tracks_dict_raw()
    if args.track not in tracks_dict['tracks']:
        error("Track '{0}' does not exist.".format(args.track), exit=True)
    del tracks_dict['tracks'][args.track]
    info("Deleted track '{0}'.".format(args.track))
    write_tracks_dict_raw(tracks_dict)


def get_argument_parser():
    parser = argparse.ArgumentParser(description="""\
Configures the bloom repository with information in groups called tracks.
""")
    metavar = "[new|show|edit|delete]"
    subparsers = parser.add_subparsers(title="Commands", metavar=metavar,
        description="""\
Call `git-bloom-config {0} -h` for additional help information on each command.
""".format(metavar))
    new_parser = subparsers.add_parser('new')
    new_parser.add_argument('track', help="name of track to create")
    new_parser.add_argument('--template', '-t',
        help="tempate to base new track on",
        choices=[x for x in config_template.keys() if x is not None],
        default=None)
    new_parser.set_defaults(func=new)
    new_parser = subparsers.add_parser('show')
    new_parser.add_argument('track', help="name of track to show")
    new_parser.set_defaults(func=show)
    new_parser = subparsers.add_parser('edit')
    new_parser.add_argument('track', help="name of track to edit")
    new_parser.set_defaults(func=edit)
    new_parser = subparsers.add_parser('delete')
    new_parser.add_argument('track', help="name of track to delete")
    new_parser.set_defaults(func=delete)
    return parser


def main(sysargs=None):
    if len(sysargs if sysargs is not None else sys.argv[1:]) == 0:
        # This means show me the current config, first check we have an env
        ensure_clean_working_env()
        if not branch_exists('bloom'):
            sys.exit("No bloom branch found")
        show_current()
        info("See: 'git-bloom-config -h' on how to change the configs")
        return 0

    parser = get_argument_parser()
    add_global_arguments(parser)
    args = parser.parse_args(sysargs)
    handle_global_arguments(args)

    # Also check to see if git has been init'ed
    check_git_init()
    # Getting here means we mean to do something, first check we have an env
    ensure_clean_working_env()
    # Then call the verb
    git_clone = GitClone()
    try:
        with git_clone:
            args.func(args)
        git_clone.commit()
    except KeyboardInterrupt:
        error("\nUser sent a Keyboard Interrupt, aborting.", exit=True)
