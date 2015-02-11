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
import yaml
import subprocess
import sys

from bloom.config import BLOOM_CONFIG_BRANCH
from bloom.config import config_template
from bloom.config import DEFAULT_TEMPLATE
from bloom.config import get_tracks_dict_raw
from bloom.config import PromptEntry
from bloom.config import upconvert_bloom_to_config_branch
from bloom.config import write_tracks_dict_raw

from bloom.git import branch_exists
from bloom.git import ls_tree
from bloom.git import ensure_clean_working_env
from bloom.git import ensure_git_root
from bloom.git import get_root
from bloom.git import inbranch

from bloom.logging import debug
from bloom.logging import error
from bloom.logging import info
from bloom.logging import warning

from bloom.util import add_global_arguments
from bloom.util import execute_command
from bloom.util import check_output
from bloom.util import handle_global_arguments
from bloom.util import maybe_continue
from bloom.util import safe_input

template_entry_order = [
    'name',
    'vcs_uri',
    'vcs_type',
    'version',
    'release_tag',
    'devel_branch',
    'ros_distro',
    'patches',
    'release_repo_url'
]


@inbranch('bloom')
def convert_old_bloom_conf(prefix=None):
    prefix = prefix if prefix is not None else 'convert'
    tracks_dict = get_tracks_dict_raw()
    track = prefix
    track_count = 0
    while track in tracks_dict['tracks']:
        track_count += 1
        track = prefix + str(track_count)
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
    tracks_dict['tracks'][track] = track_dict
    write_tracks_dict_raw(tracks_dict)
    execute_command('git rm bloom.conf', shell=True)
    execute_command('git commit -m "Removed bloom.conf"', shell=True)
    # Now move the old bloom branch into master
    upconvert_bloom_to_config_branch()


def show_current():
    bloom_ls = ls_tree(BLOOM_CONFIG_BRANCH)
    bloom_files = [f for f, t in bloom_ls.items() if t == 'file']
    if 'bloom.conf' in bloom_files:
        info("Old bloom.conf file detected, up converting...")
        convert_old_bloom_conf()
        bloom_ls = ls_tree(BLOOM_CONFIG_BRANCH)
        bloom_files = [f for f, t in bloom_ls.items() if t == 'file']
    if 'tracks.yaml' in bloom_files:
        info(yaml.dump(get_tracks_dict_raw(), indent=2,
             default_flow_style=False))


def check_git_init():
    if get_root() is None:
        error("Not in a valid git repository", exit=True)
    cmd = 'git show-ref --heads'
    result = execute_command(cmd, autofail=False,
                             silent_error=True)
    if result != 0:
        info("Freshly initialized git repository detected.")
        info("An initial empty commit is going to be made.")
        if not maybe_continue():
            error("Answered no to continue, exiting.", exit=True)
        # Make an initial empty commit
        execute_command('git commit --allow-empty -m "Initial commit"', silent=True)


def new_cmd(args):
    new(args.track, args.template)


def new(track, template=None, copy_track=None, overrides={}):
    """
    Creates a new track

    :param track: Name of the track to create
    :param template: Template to base new track off
    :param copy_track: Track to copy values of,
        if '' then use any availabe track if one exists
    :param overrides: dict of entries to override default values
    """
    tracks_dict = get_tracks_dict_raw()
    if track in tracks_dict['tracks']:
        error("Cannot create track '{0}' beause it exists.".format(track))
        error("Run `git-bloom-config edit {0}` instead.".format(track),
              exit=True)
    track_dict = copy.copy(DEFAULT_TEMPLATE)
    template_dict = copy.copy(config_template[template])
    if copy_track is not None:
        if template is not None:
            error("You cannot specify both a template and track to copy.",
                  exit=True)
        if copy_track == '' and len(tracks_dict['tracks']) != 0:
            copy_track = list(reversed(sorted(tracks_dict['tracks'].keys())))[0]
        if copy_track and copy_track not in tracks_dict['tracks']:
            error("Cannot copy a track which does not exist: '{0}'"
                  .format(copy_track), exit=True)
        if copy_track:
            template_dict = tracks_dict['tracks'][copy_track]
        else:
            template_dict = {}
    for key in template_entry_order:
        if key in template_dict:
            track_dict[key].default = template_dict[key]
        if key in overrides:
            track_dict[key].default = overrides[key]
        if track_dict[key].default == ':{name}':
            track_dict[key].default = track
        ret = safe_input(str(track_dict[key]))
        if ret:
            track_dict[key].default = ret  # This type checks against self.values
            if ret in [':{none}', 'None']:
                track_dict[key].default = None
        track_dict[key] = track_dict[key].default
    tracks_dict['tracks'][track] = track_dict
    write_tracks_dict_raw(tracks_dict)
    info("Created '{0}' track.".format(track))


def show(args):
    tracks_dict = get_tracks_dict_raw()
    if args.track not in tracks_dict['tracks']:
        error("Track '{0}' does not exist.".format(args.track), exit=True)
    info(yaml.dump({args.track: tracks_dict['tracks'][args.track]}, indent=2,
         default_flow_style=False))


def update_track(track_dict):
    for key, value in DEFAULT_TEMPLATE.items():
        if key in ['actions']:
            if track_dict[key] != DEFAULT_TEMPLATE[key]:
                warning("Your track's '{0}' configuration is not the same as the default."
                        .format(key))
                default = 'n'
                if key == 'actions':
                    default = 'y'
                    warning("Unless you have manually modified your 'actions' "
                            "(the commands which get run for a release), "
                            "you should update to the new default.")
                warning("Should it be updated to the default setting?")
                if maybe_continue(default):
                    track_dict[key] = DEFAULT_TEMPLATE[key]
        elif key not in track_dict:
            value = value.default if isinstance(value, PromptEntry) else value
            track_dict[key] = value
    return track_dict


def edit_cmd(args):
    edit(args.track)


def edit(track):
    tracks_dict = get_tracks_dict_raw()
    if track not in tracks_dict['tracks']:
        error("Track '{0}' does not exist.".format(track), exit=True)
    # Ensure the track is complete
    track_dict = tracks_dict['tracks'][track]
    update_track(track_dict)
    # Prompt for updates
    for key in template_entry_order:
        pe = DEFAULT_TEMPLATE[key]
        pe.default = tracks_dict['tracks'][track][key]
        ret = safe_input(str(pe))
        if ret:
            pe.default = ret  # This type checks against self.values
            if ret in [':{none}', 'None']:
                pe.default = None
        tracks_dict['tracks'][track][key] = pe.default
    tracks_dict['tracks'][track] = track_dict
    info("Saving '{0}' track.".format(track))
    write_tracks_dict_raw(tracks_dict)


def delete(args):
    delete_cmd(args.track)


def delete_cmd(track):
    tracks_dict = get_tracks_dict_raw()
    if track not in tracks_dict['tracks']:
        error("Track '{0}' does not exist.".format(track), exit=True)
    del tracks_dict['tracks'][track]
    info("Deleted track '{0}'.".format(track))
    write_tracks_dict_raw(tracks_dict)


def copy_cmd(args):
    copy_track(args.src, args.dst)


def copy_track(src, dst):
    tracks_dict = get_tracks_dict_raw()
    if src not in tracks_dict['tracks']:
        error("Track '{0}' does not exist.".format(src), exit=True)
    if dst in tracks_dict['tracks']:
        error("Track '{0}' already exists.".format(dst), exit=True)
    tracks_dict['tracks'][dst] = copy.deepcopy(tracks_dict['tracks'][src])
    info("Saving '{0}' track.".format(dst))
    write_tracks_dict_raw(tracks_dict)


def rename_cmd(args):
    rename_track(args.src, args.dst)


def rename_track(src, dst):
    copy_track(src, dst)
    delete_cmd(src)


def get_argument_parser():
    parser = argparse.ArgumentParser(description="""\
Configures the bloom repository with information in groups called tracks.
""")
    metavar = "[new|show|edit|delete|copy|rename]"
    subparsers = parser.add_subparsers(
        title="Commands", metavar=metavar, description="""\
Call `git-bloom-config {0} -h` for additional help information on each command.
""".format(metavar))
    new_parser = subparsers.add_parser('new')
    add = new_parser.add_argument
    add('track', help="name of track to create")
    add('--template', '-t',
        help="tempate to base new track on",
        choices=[x for x in config_template.keys() if x is not None],
        default=None)
    new_parser.set_defaults(func=new_cmd)
    new_parser = subparsers.add_parser('show')
    add = new_parser.add_argument
    add('track', help="name of track to show")
    new_parser.set_defaults(func=show)
    new_parser = subparsers.add_parser('edit')
    add = new_parser.add_argument
    add('track', help="name of track to edit")
    new_parser.set_defaults(func=edit_cmd)
    new_parser = subparsers.add_parser('delete')
    add = new_parser.add_argument
    add('track', help="name of track to delete")
    new_parser.set_defaults(func=delete)
    new_parser = subparsers.add_parser('copy')
    add = new_parser.add_argument
    add('src', help="name of track to copy from")
    add('dst', help="name of track to copy to")
    new_parser.set_defaults(func=copy_cmd)
    new_parser = subparsers.add_parser('rename')
    add = new_parser.add_argument
    add('src', help="name of track to rename")
    add('dst', help="new name of track")
    new_parser.set_defaults(func=rename_cmd)
    return parser


def main(sysargs=None):
    from bloom.config import upconvert_bloom_to_config_branch
    upconvert_bloom_to_config_branch()

    if len(sysargs if sysargs is not None else sys.argv[1:]) == 0:
        # This means show me the current config, first check we have an env
        ensure_clean_working_env()
        if not branch_exists(BLOOM_CONFIG_BRANCH):
            sys.exit("No {0} branch found".format(BLOOM_CONFIG_BRANCH))
        show_current()
        info("See: 'git-bloom-config -h' on how to change the configs")
        return 0

    parser = get_argument_parser()
    add_global_arguments(parser)
    args = parser.parse_args(sysargs)
    handle_global_arguments(args)

    # Also check to see if git has been init'ed
    check_git_init()
    # Check that the current directory is a serviceable git/bloom repo
    try:
        ensure_clean_working_env()
        ensure_git_root()
    except SystemExit:
        parser.print_usage()
        raise
    # Then call the verb
    try:
        args.func(args)
    except (KeyboardInterrupt, EOFError):
        error("\nUser sent a Keyboard Interrupt, aborting.", exit=True)
