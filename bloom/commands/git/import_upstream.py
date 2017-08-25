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
import os
import shutil
import sys
import tarfile
import tempfile

from pkg_resources import parse_version

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

from bloom.config import BLOOM_CONFIG_BRANCH

from bloom.git import branch_exists
from bloom.git import create_branch
from bloom.git import create_tag
from bloom.git import delete_remote_tag
from bloom.git import delete_tag
from bloom.git import ensure_clean_working_env
from bloom.git import ensure_git_root
from bloom.git import get_last_tag_by_version
from bloom.git import GitClone
from bloom.git import has_changes
from bloom.git import inbranch
from bloom.git import ls_tree
from bloom.git import show
from bloom.git import tag_exists
from bloom.git import track_branches

from bloom.logging import debug
from bloom.logging import error
from bloom.logging import fmt
from bloom.logging import info
from bloom.logging import warning

from bloom.packages import get_package_data

from bloom.util import add_global_arguments
from bloom.util import execute_command
from bloom.util import get_git_clone_state
from bloom.util import handle_global_arguments
from bloom.util import load_url_to_file_handle


def version_check(version):
    last_tag = get_last_tag_by_version()
    if not last_tag:
        return
    last_tag_version = last_tag.split('/')[-1]
    info(fmt("The latest upstream tag in the release repository is '@!{0}@|'."
         .format(last_tag)))
    # Ensure the new version is greater than the last tag
    if parse_version(version) < parse_version(last_tag_version):
        warning("""\
Version discrepancy:
The upstream version '{0}' isn't newer than upstream version '{1}'.
""".format(version, last_tag_version))


def import_tarball(tarball_path, target_branch, version, name):
    if tarball_path.endswith('.zip'):
        error("Zip archives are not yet supported.", exit=True)
    # Create the tarfile handle
    targz = tarfile.open(tarball_path, 'r:gz')
    with inbranch(target_branch):
        # Prepare list of members to extract, ignoring some
        ignores = ('.git', '.gitignore', '.svn', '.hgignore', '.hg', 'CVS')
        members = targz.getmembers()
        members = [m for m in members if m.name.split('/')[-1] not in ignores]

        # Clear out the local branch
        items = []
        for item in os.listdir(os.getcwd()):
            if item in ['.git', '..', '.']:
                continue
            items.append(item)
        if len(items) > 0:
            execute_command('git rm -rf ' + ' '.join(['"%s"' % i for i in items if i]))
        # Clear out any untracked files
        execute_command('git clean -fdx')

        # Extract the tarball into the clean branch
        targz.extractall(os.getcwd(), members)

        # Check for folder nesting (mostly hg)
        items = []
        for item in os.listdir(os.getcwd()):
            if not item.startswith('.'):
                items.append(item)
        tarball_prefix = os.path.basename(tarball_path)[:-len('.tag.gz')]
        if [tarball_prefix] == items:
            debug('Removing nested tarball folder: ' + str(tarball_prefix))
            tarball_prefix_path = os.path.join(os.getcwd(), tarball_prefix)
            for item in os.listdir(tarball_prefix_path):
                if item in ['.', '..']:
                    continue
                item_path = os.path.join(os.getcwd(), tarball_prefix, item)
                debug(
                    'moving ' + str(item_path) + ' to ' +
                    str(os.path.join(os.getcwd(), item))
                )
                shutil.move(item_path, os.path.join(os.getcwd(), item))
            shutil.rmtree(tarball_prefix_path)
        else:
            debug('No nested tarball folder found.')

        # Commit changes to the repository
        items = []
        for item in os.listdir(os.getcwd()):
            if item in ['.git', '..', '.']:
                continue
            items.append(item)
        if len(items) > 0:
            execute_command('git add ' + ' '.join(['"%s"' % i for i in items if i]))
        # Remove any straggling untracked files
        execute_command('git clean -dXf')
        # Only if we have local changes commit
        # (not true if the upstream didn't change any files)
        if has_changes():
            msg = "Imported upstream version '{0}' of '{1}'"
            msg = msg.format(version, name or 'upstream')
            cmd = 'git commit -m "{0}"'.format(msg)
            execute_command(cmd)
    # with inbranch(target_branch):


def handle_tree(tree, directory, root_path, version):
    for path, kind in tree.items():
        if kind == 'directory':
            # Path relative to start path
            rel_path = os.path.join(directory, path)
            # If it is a file, error
            if os.path.isfile(rel_path):
                error("In patches path '{0}' is a directory".format(rel_path) +
                      ", but it exists in the upstream branch as a file.",
                      exit=True)
            # If it is not already a directory, create it
            if not os.path.isdir(rel_path):
                info("  Createing directory... '{0}'".format(rel_path))
                os.mkdir(rel_path)
            # Recurse on the directory
            handle_tree(ls_tree(BLOOM_CONFIG_BRANCH, os.path.join(root_path, rel_path)),
                        rel_path, root_path, version)
        if kind == 'file':
            # Path relative to start path
            rel_path = os.path.join(directory, path)
            # If the local version is a directory, error
            if os.path.isdir(rel_path):
                error("In patches path '{0}' is a file, ".format(rel_path) +
                      "but it exists in the upstream branch as a directory.",
                      exit=True)
            # If the file already exists, warn
            if os.path.isfile(rel_path):
                warning("  File '{0}' already exists, overwriting..."
                        .format(rel_path))
                execute_command('git rm {0}'.format(rel_path), shell=True)
            # If package.xml tempalte in version, else grab data
            if path in ['stack.xml']:
                warning("  Skipping '{0}' templating, fuerte not supported"
                        .format(rel_path))
            if path in ['package.xml']:
                info("  Templating '{0}' into upstream branch..."
                     .format(rel_path))
                file_data = show(BLOOM_CONFIG_BRANCH, os.path.join(root_path, rel_path))
                file_data = file_data.replace(':{version}', version)
            else:
                info("  Overlaying '{0}' into upstream branch..."
                     .format(rel_path))
                file_data = show(BLOOM_CONFIG_BRANCH, os.path.join(root_path, rel_path))
            # Write file
            with open(rel_path, 'wb') as f:
                # Python 2 will treat this as an ascii string but
                # Python 3 will not re-decode a utf-8 string.
                if sys.version_info.major == 2:
                    file_data = file_data.decode('utf-8').encode('utf-8')
                else:
                    file_data = file_data.encode('utf-8')
                f.write(file_data)
            # Add it with git
            execute_command('git add {0}'.format(rel_path), shell=True)


def import_patches(patches_path, patches_path_dict, target_branch, version):
    info("Overlaying files from patched folder '{0}' on the '{2}' branch into the '{1}' branch..."
         .format(patches_path, target_branch, BLOOM_CONFIG_BRANCH))
    with inbranch(target_branch):
        handle_tree(patches_path_dict, '', patches_path, version)
        cmd = ('git commit --allow-empty -m "Overlaid patches from \'{0}\'"'
               .format(patches_path))
        execute_command(cmd, shell=True)


def import_upstream(tarball_path, patches_path, version, name, replace):
    # Check for a url and download it
    url = urlparse(tarball_path)
    if url.scheme:  # Some scheme like http, https, or file...
        tmp_dir = tempfile.mkdtemp()
        try:
            info("Fetching file from url: '{0}'".format(tarball_path))
            req = load_url_to_file_handle(tarball_path)
            tarball_path = os.path.join(tmp_dir, os.path.basename(url.path))
            with open(tarball_path, 'wb') as f:
                chunk_size = 16 * 1024
                while True:
                    chunk = req.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
            return import_upstream(tarball_path, patches_path, version, name, replace)
        finally:
            shutil.rmtree(tmp_dir)

    # If there is not tarball at the given path, fail
    if not os.path.exists(tarball_path):
        error("Specified archive does not exists: '{0}'".format(tarball_path),
              exit=True)

    # If either version or name are not provided, guess from archive name
    if not version or not name:
        # Parse tarball name
        tarball_file = os.path.basename(tarball_path)
        ending = None
        if tarball_file.endswith('.tar.gz'):
            ending = '.tar.gz'
        elif tarball_file.endswith('.zip'):
            ending = '.zip'
        else:
            error("Cannot detect type of archive: '{0}'"
                  .format(tarball_file), exit=True)
        tarball_file = tarball_file[:-len(ending)]
        split_tarball_file = tarball_file.split('-')
        if len(split_tarball_file) < 2 and not version or len(split_tarball_file) < 1:
            error("Cannot detect name and/or version from archive: '{0}'"
                  .format(tarball_file), exit=True)
    if not name and len(split_tarball_file) == 1:
        name = split_tarball_file[0]
    elif not name and len(split_tarball_file) == 1:
        name = '-'.join(split_tarball_file[:-1])
    if not version and len(split_tarball_file) < 2:
        error("Cannot detect version from archive: '{0}'"
              .format(tarball_file) + " and the version was not spcified.",
              exit=True)
    version = version if version else split_tarball_file[-1]

    # Check if the patches_path (if given) exists
    patches_path_dict = None
    if patches_path:
        patches_path_dict = ls_tree(BLOOM_CONFIG_BRANCH, patches_path)
        if not patches_path_dict:
            error("Given patches path '{0}' does not exist in bloom branch."
                  .format(patches_path), exit=True)

    # Do version checking
    version_check(version)

    # Check for existing tags
    upstream_tag = 'upstream/{0}'.format(version)
    if tag_exists(upstream_tag):
        if not replace:
            error("Tag '{0}' already exists, use --replace to override it."
                  .format(upstream_tag), exit=True)
        warning("Removing tag: '{0}'".format(upstream_tag))
        delete_tag(upstream_tag)
        if not get_git_clone_state():
            delete_remote_tag(upstream_tag)
    name_tag = '{0}/{1}'.format(name or 'upstream', version)
    if name_tag != upstream_tag and tag_exists(name_tag):
        if not replace:
            error("Tag '{0}' already exists, use --replace to override it."
                  .format(name_tag), exit=True)
        warning("Removing tag: '{0}'".format(name_tag))
        delete_tag(name_tag)
        if not get_git_clone_state():
            delete_remote_tag(name_tag)

    # If there is not upstream branch, create one
    if not branch_exists('upstream'):
        info("Creating upstream branch.")
        create_branch('upstream', orphaned=True)
    else:
        track_branches(['upstream'])

    # Import the given tarball
    info("Importing archive into upstream branch...")
    import_tarball(tarball_path, 'upstream', version, name)

    # Handle patches_path
    if patches_path:
        import_patches(patches_path, patches_path_dict, 'upstream', version)

    # Create tags
    with inbranch('upstream'):
        # Assert packages in upstream are the correct version
        _, actual_version, _ = get_package_data('upstream')
        if actual_version != version:
            error("The package(s) in upstream are version '{0}', but the version to be released is '{1}', aborting."
                  .format(actual_version, version), exit=True)
        # Create the tag
        info("Creating tag: '{0}'".format(upstream_tag))
        create_tag(upstream_tag)
        if name_tag != upstream_tag:
            info("Creating tag: '{0}'".format(name_tag))
            create_tag(name_tag)


def get_argument_parser():
    parser = argparse.ArgumentParser(description="""\
Imports a given archive into the release repository's upstream branch.
The upstream is cleared of all files, then the archive is extracted
into the upstream branch. If a patches_path is given then the contents
of that folder are overlaid onto the upstream branch, and any
package.xml files are templated on the version. The patches_path must
exist in the bloom branch of the local repository. Then the
'upstream-<version>' tag is created. If a repository name is given
(or guessed from the archive), a '<name>-<version>' tag is also created.
This command must be run in a clean git environment, i.e. no untracked
or uncommitted local changes.
""")
    add = parser.add_argument
    add('archive_path', help="path or url to the archive to be imported")
    add('patches_path', nargs='?', default='',
        help="relative path in the '{0}' branch to a folder to be"
             .format(BLOOM_CONFIG_BRANCH) +
             " overlaid after import of upstream sources (optional)")
    add('-v', '--release-version',
        help="version being imported (defaults to guessing from archive name)")
    add('-n', '--name',
        help="name of the repository being imported "
             "(defaults to guessing from archive name)")
    add('-r', '--replace', action="store_true",
        help="""\
allows replacement of an existing upstream import of the same version
""")
    return parser


def main(sysargs=None):
    from bloom.config import upconvert_bloom_to_config_branch
    upconvert_bloom_to_config_branch()

    parser = get_argument_parser()
    parser = add_global_arguments(parser)
    args = parser.parse_args(sysargs)
    handle_global_arguments(args)

    # Check that the current directory is a serviceable git/bloom repo
    try:
        ensure_clean_working_env()
        ensure_git_root()
    except SystemExit:
        parser.print_usage()
        raise

    git_clone = GitClone()
    with git_clone:
        import_upstream(
            args.archive_path,
            args.patches_path,
            args.release_version,
            args.name,
            args.replace)
    git_clone.commit()

    info("I'm happy.  You should be too.")
