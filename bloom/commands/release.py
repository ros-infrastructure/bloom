# Software License Agreement (BSD License)
#
# Copyright (c) 2014, Open Source Robotics Foundation, Inc.
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
from __future__ import unicode_literals

import argparse
import atexit
import datetime
import difflib
import os
import pkg_resources
import platform
import shutil
import subprocess
import sys
import tempfile
import traceback
import webbrowser
import yaml

from pkg_resources import parse_version

# python2/3 compatibility
try:
    from urllib.error import HTTPError, URLError
    from urllib.parse import urlparse
    from urllib.request import Request, urlopen
except ImportError:
    from urllib2 import HTTPError, Request, URLError, urlopen
    from urlparse import urlparse

import bloom

from bloom.config import get_tracks_dict_raw
from bloom.config import upconvert_bloom_to_config_branch
from bloom.config import write_tracks_dict_raw

from bloom.git import branch_exists
from bloom.git import checkout
from bloom.git import get_branches
from bloom.git import get_current_branch
from bloom.git import inbranch
from bloom.git import ls_tree

from bloom.github import GithubException
from bloom.github import get_gh_info
from bloom.github import get_github_interface

from bloom.logging import debug
from bloom.logging import error
from bloom.logging import fmt
from bloom.logging import get_error_prefix
from bloom.logging import get_success_prefix
from bloom.logging import info
from bloom.logging import sanitize
from bloom.logging import warning

from bloom.packages import get_package_data
from bloom.packages import get_ignored_packages

from bloom.rosdistro_api import get_distribution_file
from bloom.rosdistro_api import get_index
from bloom.rosdistro_api import get_most_recent
from bloom.rosdistro_api import get_rosdistro_index_commit
from bloom.rosdistro_api import get_rosdistro_index_original_branch

from bloom.summary import commit_summary
from bloom.summary import get_summary_file

from bloom.util import add_global_arguments
from bloom.util import change_directory
from bloom.util import disable_git_clone
from bloom.util import get_rfc_2822_date
from bloom.util import handle_global_arguments
from bloom.util import load_url_to_file_handle
from bloom.util import maybe_continue
from bloom.util import quiet_git_clone_warning
from bloom.util import safe_input
from bloom.util import temporary_directory
from bloom.util import to_unicode

try:
    import vcstools
except ImportError:
    debug(traceback.format_exc())
    error("vcstools was not detected, please install it.", file=sys.stderr,
          exit=True)
import vcstools.__version__
from vcstools.vcs_abstraction import get_vcs_client

from rosdistro import DistributionFile
from rosdistro import get_distribution_files
from rosdistro import get_index_url
from rosdistro.writer import yaml_from_distribution_file

try:
    import rosdep2
except ImportError:
    debug(traceback.format_exc())
    error("rosdep was not detected, please install it.",
          file=sys.stderr, exit=True)

try:
    import catkin_pkg
except ImportError:
    debug(traceback.format_exc())
    error("catkin_pkg was not detected, please install it.",
          file=sys.stderr, exit=True)

from catkin_pkg.changelog import get_changelog_from_path

_repositories = {}

_success = get_success_prefix()
_error = get_error_prefix()

_user_provided_release_url = None


@atexit.register
def exit_cleanup():
    global _repositories
    for repo in _repositories.values():
        repo_path = repo.get_path()
        if os.path.exists(repo_path):
            shutil.rmtree(repo_path)


_rosdistro_distribution_file_urls = {}


def get_distribution_file_url(distro):
    global _rosdistro_distribution_file_urls
    if distro not in _rosdistro_distribution_file_urls:
        index = get_index()
        if distro not in index.distributions:
            error("'{0}' distro is not in the index file.".format(distro), exit=True)
        distro_file = index.distributions[distro]
        if 'distribution' not in distro_file:
            error("'{0}' distro does not have a distribution file.".format(distro), exit=True)
        if isinstance(distro_file['distribution'], list):
            _rosdistro_distribution_file_urls[distro] = distro_file['distribution'][-1]
        else:
            _rosdistro_distribution_file_urls[distro] = distro_file['distribution']
    return _rosdistro_distribution_file_urls[distro]


def validate_github_url(url, url_type):
    if 'github.com' not in url:
        return True
    valid_url = True
    if not url.endswith('.git') and not url.endswith('.git/'):
        valid_url = False
        warning("The {0} repository url you provided does not end in `.git`."
                .format(url_type))
    if not url.startswith('https://'):
        valid_url = False
        warning("The {0} repository url you provided is not a `https://` address."
                .format(url_type))
    if not valid_url:
        if maybe_continue(msg="Would you like to enter the address again"):
            return False
        else:
            warning("Very well, the address '{0}' will be used as is.".format(url))
            return True
    # url is OK
    return True


def infer_release_repo_from_env(repository):
    """
    Generate a release repo url from a hint variable.

    If the environment var BLOOM_RELEASE_REPO_BASE exists, and
    BLOOM_RELEASE_REPO_BASE + repository + '-release.git' exists online, then
    this function will return the newly composed url
    """
    base = os.environ.get('BLOOM_RELEASE_REPO_BASE', None)
    if base is None:
        return None
    url = base + repository + '-release.git'
    try:
        urlopen(Request(url))
    except URLError:
        return None
    except HTTPError:
        return None
    return url


def get_repo_uri(repository, distro):
    url = None
    # Fetch the distro file
    distribution_file = get_distribution_file(distro)
    if repository in distribution_file.repositories and \
       distribution_file.repositories[repository].release_repository is not None:
        url = distribution_file.repositories[repository].release_repository.url
    else:
        error("Specified repository '{0}' is not in the distribution file located at '{1}'"
              .format(repository, get_distribution_file_url(distro)))
        matches = difflib.get_close_matches(repository, distribution_file.repositories)
        if matches:
            info(fmt("@{yf}Did you mean one of these: '" + "', '".join([m for m in matches]) + "'?"))
    if url is None:
        url = infer_release_repo_from_env(repository)
    if url is None:
        info("Could not determine release repository url for repository '{0}' of distro '{1}'"
             .format(repository, distro))
        info("You can continue the release process by manually specifying the location of the RELEASE repository.")
        info("To be clear this is the url of the RELEASE repository not the upstream repository.")
        info("For release repositories on GitHub, you should provide the `https://` url which should end in `.git`.")
        info("Here is the url for a typical release repository on GitHub: https://github.com/ros-gbp/rviz-release.git")
        # Calculate a reasonable default from the list of previous distros
        info(fmt("@{gf}@!==> @|") + "Looking for a release of this repository in a different distribution...")
        default_distro, default_release = get_most_recent('release', repository, distro)
        default_release_repo_url = default_release.url if default_release else "press enter to abort"
        if default_distro is not None:
            warning("A different distribution, '{0}', released this repository.".format(default_distro))
        else:
            warning("No reasonable default release repository url could be determined from previous releases.")
        while True:
            url = None
            try:
                url = safe_input('Release repository url [{0}]: '.format(default_release_repo_url))
            except (KeyboardInterrupt, EOFError):
                info('', use_prefix=False)
                error("User exited at prompt.", exit=True)
            if not url:
                if default_distro is None:
                    url = None
                    error("No release repository url given, aborting.", exit=True)
                if url is not None:
                    url = default_release_repo_url
            if url is None:
                break
            # If github.com address, validate it
            # If not, validate_github_url will print some messages about why
            if not validate_github_url(url, 'release'):
                continue
            break
        global _user_provided_release_url
        _user_provided_release_url = url
    return url


def get_release_repo(repository, distro, override_url):
    global _repositories

    if override_url is not None:
        warning("Overriding the release repository url, using '{0}'".format(override_url))
        url = override_url
    else:
        url = get_repo_uri(repository, distro)

    if repository not in _repositories.values():
        temp_dir = tempfile.mkdtemp()
        _repositories[repository] = get_vcs_client('git', temp_dir)
        info(fmt("@{gf}@!==> @|") +
             "Fetching '{0}' repository from '{1}'".format(repository, url))
        _repositories[repository].checkout(url, 'master')
    return _repositories[repository]


def check_for_bloom_conf(repository):
    bloom_ls = ls_tree('bloom')
    if bloom_ls is None:
        return False
    bloom_files = [f for f, t in bloom_ls.items() if t == 'file']
    return 'bloom.conf' in bloom_files


def list_tracks(repository, distro, override_release_repository_url):
    release_repo = get_release_repo(repository, distro, override_release_repository_url)
    tracks_dict = None
    with change_directory(release_repo.get_path()):
        upconvert_bloom_to_config_branch()
        if check_for_bloom_conf(repository):
            info("No tracks, but old style bloom.conf available for conversion")
        else:
            tracks_dict = get_tracks_dict_raw()
            if tracks_dict and tracks_dict['tracks'].keys():
                info("Available tracks: " + str(tracks_dict['tracks'].keys()))
            else:
                error("Release repository has no tracks nor an old style bloom.conf file.", exit=True)
    return tracks_dict['tracks'].keys() if tracks_dict else None


def get_relative_distribution_file_path(distro):
    distribution_file_url = urlparse(get_distribution_file_url(distro))
    index_file_url = urlparse(get_index_url())
    return os.path.relpath(distribution_file_url.path,
                           os.path.commonprefix([index_file_url.path, distribution_file_url.path]))


def generate_release_tag(distro):
    tag = ('release/%s/{package}/{version}' % distro)
    if sys.version_info[0] < 3:
        tag == tag.encode('utf-8')
    return tag


def generate_ros_distro_diff(track, repository, distro, override_release_repository_url):
    def convert_unicode_dict_to_str(d):
        for key, value in d.items():
            if type(key) == unicode:
                del d[key]
                key = key.encode('utf-8')
            if type(value) == unicode:
                value = value.encode('utf-8')
            if type(value) == dict:
                convert_unicode_dict_to_str(value)
            d[key] = value

    global _user_provided_release_url
    distribution_dict = get_distribution_file(distro).get_data()
    # Get packages
    packages = get_packages()
    if len(packages) == 0:
        warning("No packages found, will not generate 'package: path' entries for rosdistro.")
    # Get version
    track_dict = get_tracks_dict_raw()['tracks'][track]
    last_version = track_dict['last_version']
    release_inc = track_dict['release_inc']
    version = '{0}-{1}'.format(last_version, release_inc)
    # Create a repository if there isn't already one
    if repository not in distribution_dict['repositories']:
        distribution_dict['repositories'][repository] = {}
    # Create a release entry if there isn't already one
    if 'release' not in distribution_dict['repositories'][repository]:
        distribution_dict['repositories'][repository]['release'] = {
            'url': override_release_repository_url or _user_provided_release_url
        }
    # Update the repository
    repo = distribution_dict['repositories'][repository]['release']
    # Consider the override
    if override_release_repository_url is not None:
        repo['url'] = override_release_repository_url
    if 'tags' not in repo:
        repo['tags'] = {}
    repo['tags']['release'] = generate_release_tag(distro)
    repo['version'] = version
    if 'last_release' in track_dict:
        repo['upstream_tag'] = track_dict['last_release']
    if 'packages' not in repo:
        repo['packages'] = []
    for path, pkg in packages.items():
        if pkg.name not in repo['packages']:
            repo['packages'].append(pkg.name)
    # Remove any missing packages
    packages_being_released = [p.name for p in packages.values()]
    for pkg_name in list(repo['packages']):
        if pkg_name not in packages_being_released:
            repo['packages'].remove(pkg_name)
    repo['packages'].sort()
    if sys.version_info[0] < 3:
        convert_unicode_dict_to_str(repo)

    def get_repository_info_from_user(url_type, defaults=None):
        data = {}
        defaults = defaults or {}
        while True:
            info("VCS Type must be one of git, svn, hg, or bzr.")
            default = defaults.get('type', None)
            insert = '' if default is None else ' [{0}]'.format(default)
            vcs_type = safe_input('VCS type{0}: '.format(insert))
            if not vcs_type:
                vcs_type = default
            if vcs_type in ['git', 'svn', 'hg', 'bzr']:
                break
            error("'{0}' is not a valid vcs type.".format(vcs_type))
            if not maybe_continue(msg='Try again'):
                return {}
        data['type'] = vcs_type
        while True:
            default = defaults.get('url', None)
            insert = '' if default is None else ' [{0}]'.format(default)
            url = safe_input('VCS url{0}: '.format(insert))
            if not url:
                url = default
            if url:
                if not validate_github_url(url, url_type):
                    # User wants to try again
                    continue
                break
            error("Nothing entered for url.")
            if not maybe_continue(msg='Try again'):
                return {}
        data['url'] = url
        while True:
            info("VCS version must be a branch, tag, or commit, e.g. master or 0.1.0")
            default = defaults.get('version', None)
            insert = '' if default is None else ' [{0}]'.format(default)
            version = safe_input('VCS version{0}: '.format(insert))
            if not version:
                version = default
            if version:
                break
            error("Nothing entered for version.")
            if not maybe_continue(msg='Try again'):
                return {}
        data['version'] = version
        return data

    # Ask for doc entry
    if 'BLOOM_DONT_ASK_FOR_DOCS' not in os.environ:
        docs = distribution_dict['repositories'][repository].get('doc', {})
        if not docs and maybe_continue(msg='Would you like to add documentation information for this repository?'):
            defaults = None
            info(fmt("@{gf}@!==> @|") + "Looking for a doc entry for this repository in a different distribution...")
            default_distro, default_doc = get_most_recent('doc', repository, distro)
            if default_distro is None:
                warning("No existing doc entries found for use as defaults.")
            else:
                warning("Using defaults from the doc entry of distribution '{0}'.".format(default_distro))
                if default_doc is not None:
                    defaults = {
                        'type': default_doc.type or None,
                        'url': default_doc.url or None,
                        'version': default_doc.version or None,
                    }
            info("Please enter your repository information for the doc generation job.")
            info("This information should point to the repository from which documentation should be generated.")
            docs = get_repository_info_from_user('doc', defaults)
        distribution_dict['repositories'][repository]['doc'] = docs

    # Ask for source entry
    if 'BLOOM_DONT_ASK_FOR_SOURCE' not in os.environ:
        source = distribution_dict['repositories'][repository].get('source', {})
        if not source and maybe_continue(msg='Would you like to add source information for this repository?'):
            defaults = None
            info(fmt("@{gf}@!==> @|") +
                 "Looking for a source entry for this repository in a different distribution...")
            default_distro, default_source = get_most_recent('source', repository, distro)
            if default_distro is None:
                warning("No existing source entries found for use as defaults.")
            else:
                warning("Using defaults from the source entry of distribution '{0}'.".format(default_distro))
                if default_source is not None:
                    defaults = {
                        'type': default_source.type or None,
                        'url': default_source.url or None,
                        'version': default_source.version or None,
                    }
            info("Please enter information which points to the active development branch for this repository.")
            info("This information is used to run continuous integration jobs and for developers to checkout from.")
            source = get_repository_info_from_user('source', defaults)

            if validate_github_url(source['url'], 'source'):
                info("Since you are on github we can add a job to run your tests on each pull request."
                     "If you would like to turn this on please see "
                     "http://wiki.ros.org/buildfarm/Pull%20request%20testing for more information. "
                     "There is more setup required to setup the hooks correctly. ")
                if maybe_continue(msg='Would you like to turn on pull request testing?', default='n'):
                    source['test_pull_requests'] = 'true'
        distribution_dict['repositories'][repository]['source'] = source

    # Ask for maintainership information
    if 'BLOOM_DONT_ASK_FOR_MAINTENANCE_STATUS' not in os.environ:
        status = distribution_dict['repositories'][repository].get('status', None)
        description = distribution_dict['repositories'][repository].get('status_description', None)
        if status is None and maybe_continue(msg='Would you like to add a maintenance status for this repository?'):
            info("Please enter a maintenance status.")
            info("Valid maintenance statuses:")
            info("- developed: active development is in progress")
            info("- maintained: no new development, but bug fixes and pull requests are addressed")
            info("- unmaintained: looking for new maintainer, bug fixes and pull requests will not be addressed")
            info("- end-of-life: should not be used, will disappear at some point")
            while True:
                status = safe_input('Status: ')
                if status in ['developed', 'maintained', 'unmaintained', 'end-of-life']:
                    break
                error("'{0}' is not a valid status.".format(status))
                if not maybe_continue(msg='Try again'):
                    status = None
                    break
            if status is not None:
                info("You can also enter a status description.")
                info("This is usually reserved for giving a reason when a status is 'end-of-life'.")
                if description is not None:
                    info("Current status description: {0}".format(description))
                description_in = safe_input('Status Description [press Enter for no change]: ')
                if description_in:
                    description = description_in
        if status is not None:
            distribution_dict['repositories'][repository]['status'] = status
            if description is not None:
                distribution_dict['repositories'][repository]['status_description'] = description

    # Do the diff
    distro_file_name = get_relative_distribution_file_path(distro)
    updated_distribution_file = DistributionFile(distro, distribution_dict)
    distro_dump = yaml_from_distribution_file(updated_distribution_file)
    distro_file_raw = load_url_to_file_handle(get_distribution_file_url(distro)).read().decode('utf-8')
    if distro_file_raw != distro_dump:
        # Calculate the diff
        udiff = difflib.unified_diff(distro_file_raw.splitlines(), distro_dump.splitlines(),
                                     fromfile=distro_file_name, tofile=distro_file_name)
        temp_dir = tempfile.mkdtemp()
        udiff_file = os.path.join(temp_dir, repository + '-' + version + '.patch')
        udiff_raw = ''
        info("Unified diff for the ROS distro file located at '{0}':".format(udiff_file))
        for line in udiff:
            if line.startswith('@@'):
                udiff_raw += line
                line = fmt('@{cf}' + sanitize(line))
            if line.startswith('+'):
                if not line.startswith('+++'):
                    line += '\n'
                udiff_raw += line
                line = fmt('@{gf}' + sanitize(line))
            if line.startswith('-'):
                if not line.startswith('---'):
                    line += '\n'
                udiff_raw += line
                line = fmt('@{rf}' + sanitize(line))
            if line.startswith(' '):
                line += '\n'
                udiff_raw += line
            info(line, use_prefix=False, end='')
        # Assert that only this repository is being changed
        distro_file_yaml = yaml.safe_load(distro_file_raw)
        distro_yaml = yaml.safe_load(distro_dump)
        if 'repositories' in distro_file_yaml:
            distro_file_repos = distro_file_yaml['repositories']
            for repo in distro_yaml['repositories']:
                if repo == repository:
                    continue
                if repo not in distro_file_repos or distro_file_repos[repo] != distro_yaml['repositories'][repo]:
                    error("This generated pull request modifies a repository entry other than the one being released.")
                    error("This likely occurred because the upstream rosdistro changed during this release.")
                    error("This pull request will abort, please re-run this command with the -p option to try again.",
                          exit=True)
        # Write the diff out to file
        with open(udiff_file, 'w+') as f:
            f.write(udiff_raw)
        # Return the diff
        return updated_distribution_file
    else:
        warning("This release resulted in no changes to the ROS distro file...")
    return None


def get_repo_info(distro_url):
    gh_info = get_gh_info(distro_url)
    if gh_info:
        return gh_info


def get_changelog_summary(release_tag):
    summary = u""
    packages = dict([(p.name, p) for p in get_packages().values()])
    for package_name in sorted(packages.keys()):
        package = packages[package_name]
        release_branch = '/'.join(release_tag.split('/')[:-1]).format(package=package.name)
        if not branch_exists(release_branch):
            continue
        with inbranch(release_branch):
            changelog = get_changelog_from_path(os.getcwd())
            if changelog is None:
                continue
            for version, date, changes in changelog.foreach_version():
                if version == package.version:
                    msgs = []
                    for change in changes:
                        msgs.extend([i for i in to_unicode(change).splitlines()])
                    msg = '\n'.join(msgs)
                    summary += u"""
## {package.name}
""".format(**locals())
                    if msg:
                        summary += u"""
```
{msg}
```
""".format(**locals())
                    else:
                        summary += u"""
- No changes
"""
    return summary


def open_pull_request(track, repository, distro, interactive, override_release_repository_url):
    # Get the diff
    distribution_file = get_distribution_file(distro)
    if repository in distribution_file.repositories and \
       distribution_file.repositories[repository].release_repository is not None:
        orig_version = distribution_file.repositories[repository].release_repository.version
    else:
        orig_version = None
    updated_distribution_file = generate_ros_distro_diff(track, repository, distro, override_release_repository_url)
    if updated_distribution_file is None:
        # There were no changes, no pull request required
        return None
    version = updated_distribution_file.repositories[repository].release_repository.version
    updated_distro_file_yaml = yaml_from_distribution_file(updated_distribution_file)

    # Determine where the distro file is hosted...
    distro_url = get_distribution_file_url(distro)
    base_info = get_repo_info(distro_url)
    if not base_info:
        warning("Automated pull request only available via github.com")
        return

    # If we did replace the branch in the url with a commit, restore that now
    rosdistro_index_original_branch = get_rosdistro_index_original_branch()
    if rosdistro_index_original_branch is not None:
        base_info['branch'] = rosdistro_index_original_branch

    # Create content for PR
    title = "{0}: {1} in '{2}' [bloom]".format(repository, version, base_info['path'])
    track_dict = get_tracks_dict_raw()['tracks'][track]
    body = u"""\
Increasing version of package(s) in repository `{repository}` to `{version}`:

- upstream repository: {upstream_repo}
- release repository: {release_repo}
- distro file: `{distro_file}`
- bloom version: `{bloom_version}`
- previous version for package: `{orig_version}`
""".format(
        repository=repository,
        orig_version=orig_version or 'null',
        version=version,
        distro_file=base_info['path'],
        bloom_version=bloom.__version__,
        upstream_repo=track_dict['vcs_uri'],
        release_repo=updated_distribution_file.repositories[repository].release_repository.url,
    )
    body += get_changelog_summary(generate_release_tag(distro))

    if base_info['server'] == 'github.com':
        # Get the github interface
        gh = get_github_interface()
        if gh is None:
            return None
        # Determine the head org/repo for the pull request
        head_org = gh.username  # The head org will always be gh user
        head_repo = None
        base_repo_id = '{org}/{repo}'.format(**base_info)
        # Check if the github user and the base org are the same
        if gh.username == base_info['org']:
            # If it is, then a fork is not necessary
            head_repo = gh.get_repo(base_info['org'], base_info['repo'])
        else:
            info(fmt("@{bf}@!==> @|@!Checking on GitHub for a fork to make the pull request from..."))
            # It is not, so a fork will be required
            # Check if a fork already exists on the user's account

            try:
                # There are a lot of forks of the ros/rosdistro repository so
                # listing those forks takes a very long time.
                # Let's try a little shortcut by checking if the repository of
                # the same name owned by the current GitHub user, if that
                # repository exists and is in the same fork network as the
                # target repo let's take it.
                # If it is not, we still fall back to listing forks.
                target_repo = gh.get_repo(base_info['org'], base_info['repo'])
                target_repo_source = target_repo['full_name']
                if target_repo['fork']:
                    target_repo_source = target_repo['source']['full_name']
                try:
                    user_repo = gh.get_repo(gh.username, base_info['repo'])
                    if user_repo['fork'] and user_repo['source']['full_name'] == target_repo_source:
                        head_repo = user_repo
                except GithubException as exc:
                    debug("Received GithubException while checking for fork: {exc}".format(**locals()))
                    # 404 on finding an exact match repo.
                    # Proceed listing all forks.
                    pass
                if head_repo is None:
                    repo_forks = gh.list_forks(base_info['org'], base_info['repo'])
                    user_forks = [r for r in repo_forks if r.get('owner', {}).get('login', '') == gh.username]
                    # github allows only 1 fork per org as far as I know. We just take the first one.
                    head_repo = user_forks[0] if user_forks else None

            except GithubException as exc:
                debug("Received GithubException while checking for fork: {exc}".format(**locals()))
                pass  # 404 or unauthorized, but unauthorized should have been caught above

            # If not head_repo still, a fork does not exist and must be created
            if head_repo is None:
                warning("Could not find a fork of {base_repo_id} on the {gh.username} GitHub account."
                        .format(**locals()))
                warning("Would you like to create one now?")
                if not maybe_continue():
                    warning("Skipping the pull request...")
                    return
                # Create a fork
                try:
                    head_repo = gh.create_fork(base_info['org'], base_info['repo'])  # Will raise if not successful
                except GithubException as exc:
                    error("Aborting pull request: {0}".format(exc))
                    return
        head_repo = head_repo.get('name', '')
        info(fmt("@{bf}@!==> @|@!" +
                 "Using this fork to make a pull request from: {head_org}/{head_repo}".format(**locals())))
        # Clone the fork
        info(fmt("@{bf}@!==> @|@!" + "Cloning {0}/{1}...".format(head_org, head_repo)))
        new_branch = None

        with temporary_directory() as temp_dir:
            def _my_run(cmd, msg=None):
                if msg:
                    info(fmt("@{bf}@!==> @|@!" + sanitize(msg)))
                else:
                    info(fmt("@{bf}@!==> @|@!" + sanitize(str(cmd))))
                from subprocess import check_call
                check_call(cmd, shell=True)
            # Use the oauth token to clone
            rosdistro_url = 'https://{gh.token}:x-oauth-basic@github.com/{base_repo_id}.git'.format(**locals())
            fork_template = 'https://{gh.token}:x-oauth-basic@github.com/{head_org}/{head_repo}.git'
            rosdistro_fork_url = fork_template.format(**locals())
            _my_run("mkdir -p {base_info[repo]}".format(**locals()))
            with change_directory(base_info['repo']):
                _my_run('git init')
                branches = [x['name'] for x in gh.list_branches(head_org, head_repo)]
                new_branch = 'bloom-{repository}-{count}'
                count = 0
                while new_branch.format(repository=repository, count=count) in branches:
                    count += 1
                new_branch = new_branch.format(repository=repository, count=count)
                # Final check
                info(fmt("@{cf}Pull Request Title: @{yf}" + sanitize(title)))
                info(fmt("@{cf}Pull Request Body : \n@{yf}" + sanitize(body)))
                msg = fmt("@!Open a @|@{cf}pull request@| @!@{kf}from@| @!'@|@!@{bf}" +
                          "{head_org}/{head_repo}:{new_branch}".format(**locals()) +
                          "@|@!' @!@{kf}into@| @!'@|@!@{bf}" +
                          "{base_repo_id}:{base_info[branch]}".format(**locals()) +
                          "@|@!'?")
                info(msg)
                if interactive and not maybe_continue():
                    warning("Skipping the pull request...")
                    return
                _my_run('git checkout -b {new_branch}'.format(**locals()))
                _my_run("git pull {rosdistro_url} {base_info[branch]}".format(**locals()),
                        "Pulling latest rosdistro branch")
                rosdistro_index_commit = get_rosdistro_index_commit()
                if rosdistro_index_commit is not None:
                    _my_run('git reset --hard {rosdistro_index_commit}'.format(**locals()))
                with open('{0}'.format(base_info['path']), 'w') as f:
                    info(fmt("@{bf}@!==> @|@!Writing new distribution file: ") + str(base_info['path']))
                    f.write(updated_distro_file_yaml)
                _my_run('git add {0}'.format(base_info['path']))
                _my_run('git commit -m "{0}"'.format(title))
                _my_run('git push {rosdistro_fork_url} {new_branch}'.format(**locals()), "Pushing changes to fork")
        # Open the pull request
        return gh.create_pull_request(base_info['org'], base_info['repo'], base_info['branch'],
                                      head_org, new_branch, title, body)

_original_version = None


def start_summary(track):
    global _original_version
    track_dict = get_tracks_dict_raw()['tracks'][track]
    if 'last_version' not in track_dict or 'release_inc' not in track_dict:
        _original_version = 'null'
    else:
        last_version = track_dict['last_version']  # Actually current version now
        release_inc = track_dict['release_inc']
        _original_version = "{0}-{1}".format(last_version, release_inc)


def get_packages():
    with inbranch('upstream'):
        _, _, packages = get_package_data('upstream')
    return packages


def update_summary(track, repository, distro):
    global _original_version
    track_dict = get_tracks_dict_raw()['tracks'][track]
    last_version = track_dict['last_version']  # Actually current version now
    release_inc = track_dict['release_inc']
    version = "{0}-{1}".format(last_version, release_inc)
    summary_file = get_summary_file()
    msg = """\
## {repository} ({distro}) - {version}

The packages in the `{repository}` repository were released into the \
`{distro}` distro by running `{cmd}` on `{date}`

""".format(
        repository=repository,
        distro=distro,
        date=get_rfc_2822_date(datetime.datetime.now()),
        cmd=' '.join(sys.argv),
        version=version
    )
    packages = [p.name for p in get_packages().values()]
    if len(packages) > 1:
        msg += "These packages were released:\n"
        for p in sorted(packages):
            msg += "- `{0}`\n".format(p)
    else:
        package_name = packages[0]
        msg += "The `{0}` package was released.\n".format(package_name)
    ignored_packages = get_ignored_packages()
    if ignored_packages:
        msg += "\nThese packages were explicitly ignored:\n"
        for ip in ignored_packages:
            msg += "- `{0}`\n".format(ip)
    summary_file = get_summary_file()
    release_file = get_distribution_file(distro)
    reps = release_file.repositories
    distro_version = None
    release_repo_url = 'unknown'
    if repository in reps and reps[repository].release_repository is not None:
        distro_version = reps[repository].release_repository.version
        release_repo_url = reps[repository].release_repository.url
    msg += """
Version of package(s) in repository `{repo}`:

- upstream repository: {upstream_repo_url}
- release repository: {release_repo_url}
- rosdistro version: `{rosdistro_pv}`
- old version: `{old_pv}`
- new version: `{new_pv}`

Versions of tools used:

- bloom version: `{bloom_v}`
- catkin_pkg version: `{catkin_pkg_v}`
- rosdep version: `{rosdep_v}`
- rosdistro version: `{rosdistro_v}`
- vcstools version: `{vcstools_v}`
""".format(
        repo=repository,
        upstream_repo_url=track_dict['vcs_uri'],
        release_repo_url=release_repo_url,
        rosdistro_pv=distro_version or 'null',
        old_pv=_original_version,
        new_pv=version,
        bloom_v=bloom.__version__,
        catkin_pkg_v=catkin_pkg.__version__,
        # Until https://github.com/ros-infrastructure/rosdistro/issues/16
        rosdistro_v=pkg_resources.require("rosdistro")[0].version,
        rosdep_v=rosdep2.__version__,
        vcstools_v=vcstools.__version__.version
    )
    summary_file.write(msg)


def _perform_release(
    repository, track, distro, new_track, interactive, pretend, tracks_dict,
    override_release_repository_url, override_release_repository_push_url
):
    # Import here to allow lazy evaluation of commands/git/__init__.py
    from bloom.commands.git.config import update_track
    # Ensure the track is complete
    track_dict = tracks_dict['tracks'][track]
    track_dict = update_track(track_dict)
    tracks_dict['tracks'][track] = track_dict
    # Set the release repositories' remote if given
    release_repo_url = track_dict.get('release_repo_url', None)
    if override_release_repository_push_url is not None:
        if release_repo_url is not None and release_repo_url != override_release_repository_push_url:
            warning("The 'Release Repository Push URL' is set in the track, "
                    "but is being overridden because the --override-release-repository-push-url option was used.")
        info(fmt("@{gf}@!==> @|") +
             "Setting release repository remote url to '{0}'"
             .format(override_release_repository_push_url))
        cmd = 'git remote set-url origin ' + override_release_repository_push_url
        info(fmt("@{bf}@!==> @|@!") + str(cmd))
        try:
            subprocess.check_call(cmd, shell=True)
        except subprocess.CalledProcessError:
            error("Setting the remote url failed, exiting.", exit=True)
        # Permanently override the push url before writing the track dict
        warning("The release repository push url is being set (permanently) to '{0}'"
                .format(override_release_repository_push_url))
        tracks_dict['release_repo_url'] = override_release_repository_push_url
    elif override_release_repository_url is not None:
        if release_repo_url is not None:
            warning("The 'Release Repository Push URL' is set in the track, "
                    "but is being ignored because the --override-release-repository-url option was used.")
    elif release_repo_url is not None:
        # We only get here if the release_repo_url is set and neither override option was set
        info(fmt("@{gf}@!==> @|") +
             "Setting release repository remote url to '{0}'"
             .format(release_repo_url))
        cmd = 'git remote set-url origin ' + release_repo_url
        info(fmt("@{bf}@!==> @|@!") + str(cmd))
        try:
            subprocess.check_call(cmd, shell=True)
        except subprocess.CalledProcessError:
            error("Setting the remote url failed, exiting.", exit=True)
    # Check for push permissions
    try:
        info(fmt(
            "@{gf}@!==> @|Testing for push permission on release repository"
        ))
        cmd = 'git remote -v'
        info(fmt("@{bf}@!==> @|@!") + str(cmd))
        subprocess.check_call(cmd, shell=True)
        # Dry run will authenticate, but not push
        cmd = 'git push --dry-run'
        info(fmt("@{bf}@!==> @|@!") + str(cmd))
        subprocess.check_call(cmd, shell=True)
    except subprocess.CalledProcessError:
        error("Cannot push to remote release repository.\n"
              "Hint: If you just typed in your username/password and you have two-factor authentication,"
              "see:\n  http://wiki.ros.org/bloom/Tutorials/GithubManualAuthorization", exit=True)
    # Write the track config before releasing
    write_tracks_dict_raw(tracks_dict)
    # Run the release
    info(fmt("@{gf}@!==> @|") +
         "Releasing '{0}' using release track '{1}'"
         .format(repository, track))
    cmd = 'git-bloom-release ' + str(track)
    if pretend:
        cmd += ' --pretend'
    info(fmt("@{bf}@!==> @|@!" + str(cmd)))
    try:
        subprocess.check_call(cmd, shell=True)
    except subprocess.CalledProcessError:
        error("Release failed, exiting.", exit=True)
    info(fmt(_success) +
         "Released '{0}' using release track '{1}' successfully"
         .format(repository, track))
    # Commit the summary
    update_summary(track, repository, distro)
    commit_summary()
    # Check for pushing
    if interactive:
        cmd = 'git remote -v'
        info(fmt("@{bf}@!==> @|@!") + str(cmd))
        subprocess.check_call(cmd, shell=True)
        info("Releasing complete, push to release repository?")
        if not maybe_continue():
            error("User answered no to continue prompt, aborting.",
                  exit=True)
    # Push changes to the repository
    info(fmt("@{gf}@!==> @|") +
         "Pushing changes to release repository for '{0}'"
         .format(repository))
    cmd = 'git push --all'
    if pretend:
        cmd += ' --dry-run'
    info(fmt("@{bf}@!==> @|@!" + str(cmd)))
    try:
        subprocess.check_call(cmd, shell=True)
    except subprocess.CalledProcessError:
        error("Pushing changes failed, would you like to add '--force' to 'git push --all'?")
        if not maybe_continue():
            error("Pushing changes failed, exiting.", exit=True)
        cmd += ' --force'
        info(fmt("@{bf}@!==> @|@!" + str(cmd)))
        try:
            subprocess.check_call(cmd, shell=True)
        except subprocess.CalledProcessError:
            error("Pushing changes failed, exiting.", exit=True)
    info(fmt(_success) + "Pushed changes successfully")
    # Push tags to the repository
    info(fmt("@{gf}@!==> @|") +
         "Pushing tags to release repository for '{0}'"
         .format(repository))
    cmd = 'git push --tags'
    if pretend:
        cmd += ' --dry-run'
    info(fmt("@{bf}@!==> @|@!" + str(cmd)))
    try:
        subprocess.check_call(cmd, shell=True)
    except subprocess.CalledProcessError:
        error("Pushing changes failed, would you like to add '--force' to 'git push --tags'?")
        if not maybe_continue():
            error("Pushing tags failed, exiting.", exit=True)
        cmd += ' --force'
        info(fmt("@{bf}@!==> @|@!" + str(cmd)))
        try:
            subprocess.check_call(cmd, shell=True)
        except subprocess.CalledProcessError:
            error("Pushing tags failed, exiting.", exit=True)
    info(fmt(_success) + "Pushed tags successfully")


def check_for_patches_and_ignores(release_repo_path):
    warning_messages = []
    current_branch = get_current_branch()
    # Get the list of files in the master branch of the release repository
    files = ls_tree('master')
    # Look for any ignore files
    ignore_files = []
    for file_name in files:
        if file_name.endswith('.ignored'):
            ignore_files.append(file_name)
    if ignore_files:
        warning_messages.append("There are package ignore files: {0}".format(ignore_files))
    # Check for .patch files in any patch branches
    for patch_branch in [b for b in get_branches() if b.lstrip('remotes/origin/').startswith('patches/')]:
        patch_branch = patch_branch.lstrip('remotes/origin/')
        if [f for f in ls_tree(patch_branch) if f.endswith('.patch')]:
            warning_messages.append("There are patches on the branch '{0}'.".format(patch_branch))
    # Summarize result
    if warning_messages:
        warning("")
        warning("You are creating a new track, this often means you are releasing for a new distribution.")
        warning("bloom has detected some patches and/or ignored packages from previous release tracks.")
        warning("You may wish to migrate patches or duplicate the ignored files from previous releases.")
        warning("These patches and ignored files are NOT migrated to the new track automatically.")
        warning("")
        warning("Potential items to address:")
        for msg in warning_messages:
            warning("- {0}".format(msg))
        warning("")
        warning("The release repository is located at '{0}'".format(release_repo_path))
        warning("You can modify it in a different shell and continue when finished.")
        with change_directory(release_repo_path):
            if not maybe_continue('y'):
                error("User quit.", exit=True)
        # with clause should restore the path, regardless of the user's actions
        checkout(current_branch)


def perform_release(
    repository, track, distro, new_track, interactive, pretend, pull_request_only,
    override_release_repository_url, override_release_repository_push_url
):
    # Import here to allow lazy evaluation of commands/git/__init__.py
    from bloom.commands.git.config import convert_old_bloom_conf
    from bloom.commands.git.config import edit as edit_track_cmd
    from bloom.commands.git.config import new as new_track_cmd
    release_repo = get_release_repo(repository, distro, override_release_repository_url)
    with change_directory(release_repo.get_path()):

        def validate_repository_name(repository):
            return '/' not in repository
        if not validate_repository_name(repository):
            error("Invalid repository name: {0}".format(repository), exit=True)

        # Check to see if the old bloom.conf exists
        if check_for_bloom_conf(repository):
            # Convert to a track
            info("Old bloom.conf file detected.")
            info(fmt("@{gf}@!==> @|Converting to bloom.conf to track"))
            convert_old_bloom_conf(None if new_track else distro)
        upconvert_bloom_to_config_branch()
        # Check that the track is valid
        tracks_dict = get_tracks_dict_raw()

        def create_a_new_track(track, tracks_dict):
            if not track:
                error("You must specify a track when creating a new one.", exit=True)
            if track in tracks_dict['tracks']:
                warning("Track '{0}' exists, editing...".format(track))
                edit_track_cmd(track)
                tracks_dict = get_tracks_dict_raw()
            else:
                # Create a new track called <track>,
                # copying an existing track if possible,
                # and overriding the ros_distro
                warning("Creating track '{0}'...".format(track))
                overrides = {'ros_distro': distro}
                if override_release_repository_push_url is not None:
                    overrides['release_repo_url'] = override_release_repository_push_url
                new_track_cmd(track, copy_track='', overrides=overrides)
                tracks_dict = get_tracks_dict_raw()
                check_for_patches_and_ignores(release_repo.get_path())
            return tracks_dict
        # If new_track, create the new track first
        if new_track:
            tracks_dict = create_a_new_track(track, tracks_dict)
        if track and track not in tracks_dict['tracks']:
            error("Given track '{0}' does not exist in release repository."
                  .format(track))
            info("Available tracks: " + str(tracks_dict['tracks'].keys()))
            if not track:
                error("Cannot offer to make a new track, since a track name was not provided.",
                      exit=True)
            if not maybe_continue(msg="Create a new track called '{0}' now".format(track)):
                error("User quit.", exit=True)
            tracks_dict = create_a_new_track(track, tracks_dict)
        elif not track:
            tracks = tracks_dict['tracks'].keys()
            # Error out if there are no tracks
            if len(tracks) == 0:
                error("Release repository has no tracks.")
                info("Manually clone the repository:")
                info("  git clone {0}".format(release_repo.get_url()))
                info("And then create a new track:")
                info("  git-bloom-config new <track name>")
                error("Run again after creating a track.", exit=True)
            # Error out if there is more than one track
            if len(tracks) != 1:
                error("No track specified and there is not just one track.")
                error("Please specify one of the available tracks: " +
                      str(tracks), exit=True)
            # Get the only track
            track = tracks[0]
        # Make sure the release repository and the upstream repository are different.
        track_dict = tracks_dict['tracks'][track]
        vcs_uri = track_dict.get('vcs_uri')
        if vcs_uri == release_repo.get_url():
            warning("Your RELEASE repository, '{0}', is the same as your UPSTREAM repository, '{1}'."
                    .format(release_repo.get_url(), vcs_uri))
            warning("This is not recommended, normally you have separate RELEASE and UPSTREAM repositories.")
            if not maybe_continue('n', 'Are you sure you want continue'):
                error("User quit.", exit=True)
        start_summary(track)
        if not pull_request_only:
            _perform_release(
                repository, track, distro, new_track, interactive, pretend, tracks_dict,
                override_release_repository_url, override_release_repository_push_url
            )
        if 'BLOOM_NO_ROSDISTRO_PULL_REQUEST' not in os.environ and not pretend:
            # Propose github pull request
            info(fmt("@{gf}@!==> @|") +
                 "Generating pull request to distro file located at '{0}'"
                 .format(get_distribution_file_url(distro)))
            try:
                pull_request_url = open_pull_request(
                    track, repository, distro, interactive, override_release_repository_url
                )
                if pull_request_url:
                    info(fmt(_success) + "Pull request opened at: {0}".format(pull_request_url))
                    if 'BLOOM_NO_WEBBROWSER' not in os.environ and platform.system() in ['Darwin']:
                        webbrowser.open(pull_request_url)
                else:
                    info("The release of your packages was successful, but the pull request failed.")
                    info("Please manually open a pull request by editing the file here: '{0}'"
                         .format(get_distribution_file_url(distro)))
                    info(fmt(_error) + "No pull request opened.")
            except Exception as e:
                debug(traceback.format_exc())
                error("Failed to open pull request: {0} - {1}".format(type(e).__name__, e), exit=True)


def get_argument_parser():
    parser = argparse.ArgumentParser(description="Releases a repository which already exists in the ROS distro file.")
    add = parser.add_argument
    add('repository', help="repository to run bloom on")
    add('--list-tracks', '-l', action='store_true', default=False,
        help="list available tracks for repository")
    add('--track', '-t', required=False, help="track to run; defaults to rosdistro name")
    add('--non-interactive', '-y', action='store_true', default=False)
    add('--ros-distro', '--rosdistro', '-r', required=True,
        help="determines the ROS distro file used")
    add('--new-track', '--edit-track', '-n', '-e', action='store_true', default=False,
        help="if used, a new track will be created before running bloom")
    add('--pretend', '-s', default=False, action='store_true',
        help="Pretends to push and release")
    add('--no-pull-request', default=False, action='store_true',
        help="Prevents a pull request from being opened after release")
    add('--no-web', default=False, action='store_true',
        help="prevents a web browser from being opened at the end")
    add('--pull-request-only', '-p', default=False, action='store_true',
        help="skips the release actions and only tries to open a pull request")
    add('--override-release-repository-url', default=None,
        help="override the release repository url; "
             "the 'Release Repository Push URL' track configuration is ignored")
    add('--override-release-repository-push-url', default=None,
        help="override the 'Release Repository Push URL' track configuration; "
             "can be used in conjunction with --override-release-repository-url")
    return parser

_quiet = False


def main(sysargs=None):
    parser = get_argument_parser()
    parser = add_global_arguments(parser)
    args = parser.parse_args(sysargs)
    if args.track is None:
        args.track = args.ros_distro
    handle_global_arguments(args)

    if args.list_tracks:
        list_tracks(args.repository, args.ros_distro, args.override_release_repository_url)
        return

    if args.no_pull_request:
        os.environ['BLOOM_NO_ROSDISTRO_PULL_REQUEST'] = '1'

    if args.no_web:
        os.environ['BLOOM_NO_WEBBROWSER'] = '1'

    try:
        os.environ['BLOOM_TRACK'] = args.track
        disable_git_clone(True)
        quiet_git_clone_warning(True)
        perform_release(args.repository, args.track, args.ros_distro,
                        args.new_track, not args.non_interactive, args.pretend,
                        args.pull_request_only,
                        args.override_release_repository_url,
                        args.override_release_repository_push_url)
    except (KeyboardInterrupt, EOFError) as exc:
        error("\nReceived '{0}', aborting.".format(type(exc).__name__))
