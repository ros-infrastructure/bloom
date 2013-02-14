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

import argparse
import atexit
import os
import shutil
import subprocess
import sys
import tempfile
import traceback

# try:
#     from urllib.parse import urlparse
# except ImportError:
#     from urlparse import urlparse

from bloom.config import DEFAULT_TEMPLATE
from bloom.config import get_tracks_dict_raw
from bloom.config import template_str
from bloom.config import verify_track
from bloom.config import write_tracks_dict_raw

from bloom.logging import fmt
from bloom.logging import error
from bloom.logging import info
from bloom.logging import warning

from bloom.git import ensure_clean_working_env

from bloom.util import add_global_arguments
from bloom.util import handle_global_arguments
from bloom.util import print_exc

try:
    from vcstools.vcs_abstraction import get_vcs_client
except ImportError:
    error("vcstools was not detected, please install it.", file=sys.stderr,
        exit=True)

has_rospkg = False
try:
    import rospkg
    has_rospkg = True
except ImportError:
    warning("rospkg was not detected, stack.xml discovery is disabled",
            file=sys.stderr)

upstream_repos = {}


def get_upstream_repo(uri, vcs_type):
    global upstream_repos
    if uri not in upstream_repos:
        temp_dir = tempfile.mkdtemp()
        upstream_repos[uri] = get_vcs_client(vcs_type, temp_dir)
    return upstream_repos[uri]


@atexit.register
def clean_up_repositories():
    global upstream_repos
    for uri in upstream_repos:
        path = upstream_repos[uri].get_path()
        if os.path.exists(path):
            shutil.rmtree(path)


def find_version_from_upstream_github(vcs_uri, devel_branch=None):
    # TODO: Implement this
    info('  raw.github.com checking is not implemented yet.')
    return None


def get_upstream_meta(upstream_dir):
    meta = None
    # Check for stack.xml
    stack_path = os.path.join(upstream_dir, 'stack.xml')
    info("Checking for package.xml(s)... ", end='')
    # Check for package.xml(s)
    try:
        from catkin_pkg.packages import find_packages
        from catkin_pkg.packages import verify_equal_package_versions
    except ImportError:
        error("catkin_pkg was not detected, please install it.",
              file=sys.stderr, exit=True)
    packages = find_packages(basepath=upstream_dir)
    if packages == {}:
        if has_rospkg:
            info("package.xml(s) not found, looking for stack.xml... ",
                use_prefix=False, end='')
            if os.path.exists(stack_path):
                info("stack.xml found", use_prefix=False)
                # Assumes you are at the top of the repo
                stack = rospkg.stack.parse_stack_file(stack_path)
                meta = {}
                meta['name'] = [stack.name]
                meta['version'] = stack.version
                meta['type'] = 'stack.xml'
            else:
                info('', use_prefix=False)
                error("Neither stack.xml, nor package.xml(s) were detected.",
                    exit=True)
        else:
            info('', use_prefix=False)
            error("Package.xml(s) were not detected.",
                    exit=True)
    else:
        info("package.xml(s) found", use_prefix=False)
        try:
            version = verify_equal_package_versions(packages.values())
        except RuntimeError as err:
            info('', use_prefix=False)
            print_exc(traceback.format_exc())
            error("Releasing multiple packages with different versions is "
                  "not supported: " + str(err), exit=True)
        meta = {}
        meta['version'] = version
        meta['name'] = [p.name for p in packages.values()]
        meta['type'] = 'package.xml'
    return meta


def find_version_from_upstream(vcs_uri, vcs_type, devel_branch=None):
    # Check for github.com
    if vcs_uri.startswith('http') and 'github.com' in vcs_uri:
        info("Detected github.com repository, checking for package.xml "
            "in root of devel branch using raw.github.com...")
        version = find_version_from_upstream_github(vcs_uri, devel_branch)
        if version:
            return version, None
        warning("  Failed to find the version using raw.github.com.")
    # Try to clone the upstream repository
    info("Checking upstream devel branch for a package.xml(s) or stack.xml")
    upstream_repo = get_upstream_repo(vcs_uri, vcs_type)
    if not upstream_repo.checkout(vcs_uri, devel_branch or '', shallow=True):
        error("Failed to checkout to the upstream branch "
            "'{0}' in the repository from '{1}'"
            .format(devel_branch or '<default>', vcs_uri))
    meta = get_upstream_meta(upstream_repo.get_path())
    if not meta:
        error("Failed to find any package.xml(s) or a stack.xml in the "
            "upstream devel branch '{0}' in the repository from '{1}'"
            .format(devel_branch or '<default>', vcs_uri))
    info("Detected version '{0}' from package(s): {1}"
        .format(meta['version'], meta['name']))
    return meta['version'], upstream_repo


def process_track_settings(track_dict, release_inc_override):
    settings = {}
    settings['name'] = track_dict['name']
    vcs_uri = track_dict['vcs_uri']
    # Is the vcs_uri set?
    if vcs_uri is None or vcs_uri.lower() == ':{none}':
        error("The '{0}' must be set to something other than None."
            .format(DEFAULT_TEMPLATE['vcs_uri'].name),
            exit=True)
    # Is the vcs_type set and valid?
    vcs_type = track_dict['vcs_type']
    vcs_type_prompt = DEFAULT_TEMPLATE['vcs_type']
    if vcs_type is None or vcs_type.lower() not in vcs_type_prompt.values:
        error("The '{0}' cannot be '{1}', valid values are: {2}"
            .format(vcs_type_prompt.name, vcs_type, vcs_type_prompt.values),
            exit=True)
    settings['vcs_type'] = vcs_type
    # Is the version set to auto?
    version = track_dict['version']
    repo = None
    if version.lower() == ':{auto}':
        # Is the vcs_type either hg, git, or svn?
        if vcs_type not in ['git', 'hg', 'svn']:
            error("Auto detection of version is not supported for '{0}'"
                .format(vcs_type), exit=True)
        devel_branch = track_dict['devel_branch']
        if type(devel_branch) in [str, unicode]\
        and devel_branch.lower() == ':{none}':
            devel_branch = None
        version, repo = find_version_from_upstream(vcs_uri,
            vcs_type, devel_branch)
        if version is None:
            warning("Could not determine the version automatically.")
    if version is None or version == ':{ask}':
        ret = raw_input('What version are you releasing '
            '(version should normally be MAJOR.MINOR.PATCH)? ')
        if not ret:
            error("You must specify a version to continue.", exit=True)
        version = ret
    settings['version'] = version
    settings['vcs_local_uri'] = repo.get_path() if repo else vcs_uri
    # Now that we have a version, template the vcs_uri if needed
    if ':{version}' in vcs_uri:
        vcs_uri = vcs_uri.replace(':{version}', version)
    settings['vcs_uri'] = vcs_uri
    # Is the release tag set to ask
    release_tag = track_dict['release_tag']
    release_tag_prompt = DEFAULT_TEMPLATE['release_tag']
    if release_tag is not None and release_tag == ':{ask}':
        ret = raw_input('What upstream tag should bloom import from? ')
        if not ret:
            error("You must specify a release tag.", exit=True)
        release_tag = ret
    elif release_tag is None or release_tag.lower() == ':{none}':
        if vcs_type not in ['svn', 'tar']:
            error("'{0}' can not be None unless '{1}' is either 'svn' or 'tar'"
                .format(release_tag_prompt.name, vcs_type_prompt.name))
        release_tag = ':{none}'
    else:
        release_tag = release_tag.replace(':{version}', version)
    settings['release_tag'] = release_tag
    # Transfer other settings
    settings['devel_branch'] = track_dict['devel_branch']
    settings['patches'] = track_dict['patches']
    settings['ros_distro'] = track_dict['ros_distro']
    # Release increment
    if 'last_version' in track_dict and track_dict['last_version'] != version:
        next_release_inc = str(0)
    else:
        next_release_inc = str(int(track_dict['release_inc']) + 1)
    settings['release_inc'] = release_inc_override or next_release_inc
    return settings


def execute_track(track, track_dict, release_inc, pretend=True):
    info("Processing release track settings for '{0}'".format(track))
    settings = process_track_settings(track_dict, release_inc)
    # setup extra settings
    archive_dir_path = tempfile.mkdtemp()
    settings['archive_dir_path'] = archive_dir_path
    archive_file = '{name}-{version}.tar.gz'.format(**settings)
    settings['archive_path'] = os.path.join(archive_dir_path, archive_file)
    # execute actions
    info("", use_prefix=False)
    info("Executing release track '{0}'".format(track))
    for action in track_dict['actions']:
        templated_action = template_str(action, settings)
        info(fmt("@{bf}@!==> @|@!" + str(templated_action)))
        if pretend:
            continue
        ret = subprocess.call(templated_action, shell=True)
        if ret > 0:
            error(fmt("@{rf}@!<== @|Error running command '@!{0}@|'")
                .format(templated_action), exit=True)
    if not pretend:
        # Update the release_inc
        tracks_dict = get_tracks_dict_raw()
        tracks_dict['tracks'][track]['release_inc'] = settings['release_inc']
        tracks_dict['tracks'][track]['last_version'] = settings['version']
        write_tracks_dict_raw(tracks_dict,
            'Updating release inc to: ' + str(settings['release_inc']))


def get_argument_parser(tracks):
    parser = argparse.ArgumentParser(description="Executes a release track.")
    parser.add_argument('track', choices=tracks,
        help="release track to execute")
    parser.add_argument('--release-increment', '-i',
        help="overrides the automatic release increment number")
    parser.add_argument('--pretend', '-p', action="store_true", default=False,
        help="does everything but actually run the commands")
    return parser


def main(sysargs=None):
    # Check that the current directory is a serviceable git/bloom repo
    ensure_clean_working_env()

    # Get tracks
    tracks_dict = get_tracks_dict_raw()
    if not tracks_dict['tracks']:
        error("No tracks configured, first create a track with "
            "'git-bloom-config new <track_name>'", exit=True)

    # Do argparse stuff
    parser = get_argument_parser([str(t) for t in tracks_dict['tracks']])
    parser = add_global_arguments(parser)
    args = parser.parse_args(sysargs)
    handle_global_arguments(args)

    verify_track(args.track, tracks_dict['tracks'][args.track])

    execute_track(args.track, tracks_dict['tracks'][args.track],
        args.release_increment, args.pretend)

    # Notify the user of success and next action suggestions
    print('\n\n')
    warning("Tip: Check to ensure that the debian tags created have the same "
            "version as the upstream version you are releasing.")
    info(fmt("@{gf}@!Everything went as expected, "
         "you should check that the new tags match your expectations, and "
         "then push to the release repo with:@|"))
    info(fmt("  git push --all && git push --tags  @{kf}@!# You might have to add --force to the second command if you are over-writing existing flags"))
