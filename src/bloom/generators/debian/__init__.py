# Software License Agreement (BSD License)
#
# Copyright (c) 2012, Willow Garage, Inc.
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

import pkg_resources
import copy
import datetime
import dateutil.tz
import em
import os
import re
import rospkg
import sys
import tempfile

from pprint import pprint
from subprocess import Popen, CalledProcessError

from ... util import add_global_arguments
from ... util import execute_command
from ... util import handle_global_arguments
from ... util import bailout
from ... util import ansi
# from . util import get_versions_from_upstream_tag
from ... git import checkout
from ... git import get_current_branch
from ... git import track_branches
from ... git import get_last_tag_by_date

from ... logging import error
from ... logging import info
from ... logging import warning

try:
    from vcstools import VcsClient
except ImportError:
    print("vcstools was not detected, please install it.", file=sys.stderr)
    sys.exit(1)

try:
    import rosdep2.catkin_support
    from rosdep2.platforms.debian import APT_INSTALLER
except ImportError:
    print("rosdep was not detected, please install it.", file=sys.stderr)
    sys.exit(2)

'''
The Debian binary package file names conform to the following convention:
<foo>_<VersionNumber>-<DebianRevisionNumber>_<DebianArchitecture>.deb

Distribution is an ubuntu distro
Version is the upstream version
DebianInc is some number that is incremental for package maintenance
Changes is a bulleted list of changes.
'''


def call(working_dir, command, pipe=None):
    print('+ cd %s && ' % working_dir + ' '.join(command))
    process = Popen(command, stdout=pipe, stderr=pipe, cwd=working_dir)
    output, unused_err = process.communicate()
    retcode = process.poll()
    if retcode:
        raise CalledProcessError(retcode, command)
    if pipe:
        return output


def check_local_repo_exists(repo_path):
    return os.path.exists(os.path.join(repo_path, '.git'))


def update_repo(working_dir, repo_path, repo_uri, first_release):
    if check_local_repo_exists(repo_path):
        print("please start from a bare working dir::\n\t"
              "rm -rf %s" % repo_path)
        sys.exit(1)
    if first_release:
        os.makedirs(repo_path)
        call(repo_path, ['git', 'init'])
        call(repo_path, ['git', 'remote', 'add', 'origin', repo_uri])
    else:
        command = ('gbp-clone', repo_uri)
        call(working_dir, command)

    command = ['git', 'config', '--add', 'remote.origin.push',
               '+refs/heads/*:refs/heads/*']
    call(repo_path, command)

    command = ['git', 'config', '--add', 'remote.origin.push',
               '+refs/tags/*:refs/tags/*']
    call(repo_path, command)


def generate_rosdep_db(working_dir, rosdistro):
    return rosdep2.catkin_support.get_catkin_view(rosdistro)


def make_working(working_dir):
    if not os.path.exists(working_dir):
        os.makedirs(working_dir)


def sanitize_package_name(name):
    return name.replace('_', '-')


def debianize_string(value):
    markup_remover = re.compile(r'<.*?>')
    value = markup_remover.sub('', value)
    value = re.sub('\s+', ' ', value)
    value = value.strip()
    return value


def process_stack_xml(args, cwd=None):
    """Reads in a stack.xml file and does some post processing on it"""
    cwd = cwd if cwd else '.'
    xml_path = os.path.join(cwd, 'stack.xml')
    if not os.path.exists(xml_path):
        bailout("No stack.xml file found at: {0}".format(xml_path))
    stack = rospkg.stack.parse_stack_file(xml_path)

    data = {}
    data['Name'] = stack.name
    data['Version'] = stack.version
    data['Description'] = debianize_string(stack.description)
    data['Homepage'] = stack.url

    data['Catkin-ChangelogType'] = ''
    data['Catkin-DebRulesType'] = stack.build_type
    data['Catkin-DebRulesFile'] = stack.build_type_file
    data['Catkin-CopyrightType'] = stack.copyright
    data['copyright'] = stack.copyright

    data['DebianInc'] = args.debian_revision
    if args.rosdistro == 'backports':
        data['Package'] = sanitize_package_name("%s" % (stack.name))
    else:
        data['Package'] = \
            sanitize_package_name("ros-%s-%s" % (args.rosdistro, stack.name))

    data['ROS_DISTRO'] = args.rosdistro

    # allow override of these values
    if args.rosdistro == 'backports':
        data['INSTALL_PREFIX'] = \
            args.install_prefix if args.install_prefix != None else '/usr'
    else:
        data['INSTALL_PREFIX'] = \
            args.install_prefix if args.install_prefix != None \
                                else '/opt/ros/%s' % args.rosdistro

    data['Depends'] = set([d.name for d in stack.depends])
    data['BuildDepends'] = set([d.name for d in stack.build_depends])

    maintainers = []
    for m in stack.maintainers:
        maintainer = m.name
        if m.email:
            maintainer += ' <%s>' % m.email
        maintainers.append(maintainer)
    data['Maintainer'] = ', '.join(maintainers)

    # Go over the different subfolders and find all the packages
    package_descriptions = {}

    # search for manifest in current folder and direct subfolders
    for dir_name in [cwd] + os.listdir(cwd):
        if not os.path.isdir(dir_name):
            continue
        dir_path = os.path.join('.', dir_name)
        for file_name in os.listdir(dir_path):
            if file_name == 'manifest.xml':
                # parse the manifest, in case it is not valid
                manifest = rospkg.parse_manifest_file(dir_path, file_name)
                # remove markups
                if manifest.description is None:
                    manifest.description = ''
                description = debianize_string(manifest.description)
                if dir_name == '.':
                    dir_name = stack.name
                package_descriptions[dir_name] = description
    # Enhance the description with the list of packages in the stack
    if package_descriptions:
        if data['Description']:
            data['Description'] += '\n .\n'
        data['Description'] += ' This stack contains the packages:'
        for name, description in package_descriptions.items():
            data['Description'] += '\n * %s: %s' % (name, description)

    return data


def is_meta_package(package):
    metapack = [True for e in package.exports if e.tagname == 'metapackage']
    if len(metapack) > 0:
        return True
    else:
        return False


def process_package_xml(args, directory=None):
    cwd = directory if directory else '.'
    xml_path = os.path.join(cwd, 'package.xml')
    if not os.path.exists(xml_path):
        bailout("No package.xml file found at: {0}".format(xml_path))
    try:
        from catkin_pkg.package import parse_package
    except ImportError:
        error("catkin_pkg was not detected, please install it.",
              file=sys.stderr)
        sys.exit(1)
    package = parse_package(xml_path)

    data = {}
    data['Name'] = package.name
    data['Version'] = package.version
    data['Description'] = debianize_string(package.description)
    websites = [str(url) for url in package.urls if url.type == 'website']
    homepage = websites[0] if websites else ''
    if homepage == '':
        warning("No homepage set, defaulting to ''")
    data['Homepage'] = homepage

    data['Catkin-ChangelogType'] = ''
    if is_meta_package(package):
        info("Metapackage detected: " + package.name)
        data['Catkin-DebRulesType'] = 'metapackage'
    else:
        data['Catkin-DebRulesType'] = 'cmake'
    data['Catkin-DebRulesFile'] = ''
    # data['Catkin-CopyrightType'] = package.copyright
    # data['copyright'] = package.copyright

    data['DebianInc'] = args.debian_revision
    if args.rosdistro == 'backports':
        data['Package'] = sanitize_package_name("%s" % (package.name))
    else:
        data['Package'] = \
            sanitize_package_name("ros-%s-%s" % (args.rosdistro, package.name))

    data['ROS_DISTRO'] = args.rosdistro

    # allow override of these values
    if args.rosdistro == 'backports':
        data['INSTALL_PREFIX'] = \
            args.install_prefix if args.install_prefix != None else '/usr'
    else:
        data['INSTALL_PREFIX'] = \
            args.install_prefix if args.install_prefix != None \
                                else '/opt/ros/%s' % args.rosdistro

    data['Depends'] = set([d.name for d in package.run_depends])
    build_deps = (package.build_depends + package.buildtool_depends)
    data['BuildDepends'] = set([d.name for d in build_deps])

    print("BuildDepends is %s for %s, from %s" % (data['BuildDepends'], package.name, xml_path))

    maintainers = []
    for m in package.maintainers:
        maintainers.append(str(m))
    data['Maintainer'] = ', '.join(maintainers)

    # Go over the different subfolders and find all the packages
    package_descriptions = {}

    # search for manifest in current folder and direct subfolders
    for dir_name in [cwd] + os.listdir(cwd):
        if not os.path.isdir(dir_name):
            continue
        dir_path = os.path.join('.', dir_name)
        for file_name in os.listdir(dir_path):
            if file_name == 'manifest.xml':
                # parse the manifest, in case it is not valid
                manifest = rospkg.parse_manifest_file(dir_path, file_name)
                # remove markups
                if manifest.description is None:
                    manifest.description = ''
                description = debianize_string(manifest.description)
                if dir_name == '.':
                    dir_name = package.name
                package_descriptions[dir_name] = description
    # Enhance the description with the list of packages in the stack
    if package_descriptions:
        if data['Description']:
            data['Description'] += '\n .\n'
        data['Description'] += ' This stack contains the packages:'
        for name, description in package_descriptions.items():
            data['Description'] += '\n * %s: %s' % (name, description)

    return data


def get_stack_data(args, directory=None):
    path = directory if directory else ''
    if os.path.exists(os.path.join(path, 'package.xml')):
        return process_package_xml(args, directory)
    else:
        if os.path.exists(os.path.join(path, 'stack.xml')):
            return process_stack_xml(args, directory)
        else:
            bailout("No stack.xml or package.xml found, exiting.")


def expand(fname, stack_data, dest_dir, filetype=''):
    # insert template type
    if fname == 'rules' and stack_data['Catkin-DebRulesType'] == 'custom':
        path = os.path.join(dest_dir, '..', stack_data['Catkin-DebRulesFile'])
        with open(path, 'r') as f:
            file_em = f.read()
    else:
        if filetype != '':
            ifilename = (fname + '.' + filetype + '.em')
        else:
            ifilename = fname + '.em'
        ifilename = os.path.join('resources', 'em', ifilename)
        print("Reading %s template from %s" % (fname, ifilename))
        try:
            file_em = pkg_resources.resource_string('bloom', ifilename)
        except IOError:
            warning("Could not find {0}, skipping...".format(ifilename))
            return False

    s = em.expand(file_em, **stack_data)

    ofilename = os.path.join(dest_dir, fname)
    with open(ofilename, "w") as ofilestr:
        print(s, file=ofilestr)
    if fname == 'rules':
        os.chmod(ofilename, 0755)
    return True


def find_deps(stack_data, apt_installer, rosdistro, debian_distro):
    os_name = 'ubuntu'

    deps = stack_data['Depends']
    build_deps = stack_data['BuildDepends']


    rosdep_view = rosdep2.catkin_support.get_catkin_view(rosdistro, os_name,
                                                         debian_distro,
                                                         update=False)

    ubuntu_deps = set()
    for dep in deps:
        resolved = \
            rosdep2.catkin_support.resolve_for_os(dep, rosdep_view,
                                                  apt_installer, os_name,
                                                  debian_distro)
        ubuntu_deps.update(resolved)

    ubuntu_build_deps = set()
    for dep in build_deps:
        resolved = \
            rosdep2.catkin_support.resolve_for_os(dep, rosdep_view,
                                                  apt_installer, os_name,
                                                  debian_distro)

        print("BuildDepends in is %s out is %s" % (dep, resolved))

        ubuntu_build_deps.update(resolved)

    print(stack_data['Name'], "has the following dependencies for ubuntu "
                               "%s" % debian_distro)
    print('Run dependencies:')
    pprint(ubuntu_deps)
    print('Build dependencies:')
    pprint(ubuntu_build_deps)
    return list(ubuntu_deps), list(ubuntu_build_deps)


def generate_deb(stack_data, repo_path, stamp, rosdistro, debian_distro):
    apt_installer = rosdep2.catkin_support.get_installer(APT_INSTALLER)
    depends, build_depends = find_deps(stack_data, apt_installer,
                                       rosdistro, debian_distro)
    stack_data['Depends'] = depends
    stack_data['BuildDepends'] = build_depends
    stack_data['Distribution'] = debian_distro
    stack_data['Date'] = stamp.strftime('%a, %d %b %Y %T %z')
    stack_data['YYYY'] = stamp.strftime('%Y')

    source_dir = '.'  # repo_path
    print("source_dir=%s" % source_dir)
    dest_dir = os.path.join(source_dir, 'debian')
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    #create control file:
    expand('control', stack_data, dest_dir)
    expand('changelog', stack_data, dest_dir,
           filetype=stack_data['Catkin-ChangelogType'])
    expand('rules', stack_data, dest_dir,
           filetype=stack_data['Catkin-DebRulesType'])
    # expand('copyright', stack_data, dest_dir,
           # filetype=stack_data['Catkin-CopyrightType'])
    # ofilename = os.path.join(dest_dir, 'copyright')
    # ofilestr = open(ofilename, "w")
    # print(stack_data['copyright'], file=ofilestr)
    # ofilestr.close()

    #compat to quiet warnings, 7 .. lucid
    ofilename = os.path.join(dest_dir, 'compat')
    ofilestr = open(ofilename, "w")
    print("7", file=ofilestr)
    ofilestr.close()

    #source format, 3.0 quilt
    if not os.path.exists(os.path.join(dest_dir, 'source')):
        os.makedirs(os.path.join(dest_dir, 'source'))
    ofilename = os.path.join(dest_dir, 'source/format')
    ofilestr = open(ofilename, "w")
    print("3.0 (quilt)", file=ofilestr)
    ofilestr.close()


def commit_debian(stack_data, repo_path):
    call(repo_path, ['git', 'add', 'debian'])
    message = "+ Creating debian mods for distro: %(Distribution)s, " \
              "rosdistro: %(ROS_DISTRO)s, upstream version: " \
              "%(Version)s" % stack_data
    call(repo_path, ['git', 'commit', '-m', message])


def get_argument_parser():
    """Creates and returns the argument parser"""
    import argparse
    parser = argparse.ArgumentParser(description="""\
Creates or updates a git-buildpackage repository using a catkin project.\
""")
    parser.add_argument('--working', help='A scratch build path. Defaults to '
                                          'a temporary directory.')
    parser.add_argument('--debian-revision', dest='debian_revision',
                        help='Bump the changelog debian number.'
                             ' Please enter a monotonically increasing number '
                             'from the last upload.',
                        default=0)
    parser.add_argument('--install-prefix', dest='install_prefix',
                        help='The installation prefix')
    parser.add_argument('--distros', nargs='+',
                        help='A list of debian distros.',
                        default=[])
    parser.add_argument('--do-not-update-rosdep',
                        help="If specified, rosdep will not be updated before "
                             "generating the debian stuff",
                        action='store_false', default=True)
    parser.add_argument('--upstream-tag', '-t',
                        help='tag to create debians from', default=None)

    #ros specific stuff.
    parser.add_argument('rosdistro',
                        help="The ros distro. Like 'electric', 'fuerte', "
                             "or 'groovy'. If this is set to backports then "
                             "the resulting packages will not have the "
                             "ros-<rosdistro>- prefix.")
    return parser


def execute_bloom_generate_debian(args, bloom_repo):
    """Executes the generation of the debian.  Assumes in bloom git repo."""
    if args.upstream_tag is not None:
        last_tag = args.upstream_tag
    else:
        last_tag = get_last_tag_by_date()
        if not last_tag:
            bailout("There are no upstream versions imported into this repo."
                    "Run this first:\n\tgit bloom-import-upstream")
        print("The latest upstream tag in the release repo is "
              "{0}{1}{2}".format(ansi('boldon'), last_tag, ansi('reset')))

    # major, minor, patch = get_versions_from_upstream_tag(last_tag)
    # version_str = '.'.join([major, minor, patch])
    # print("Upstream version is: {0}{1}{2}"
          # "".format(ansi('boldon'), version_str, ansi('reset')))

    # Make sure we are on the correct upstream branch
    bloom_repo.update(last_tag)

    stamp = datetime.datetime.now(dateutil.tz.tzlocal())
    stack_data = get_stack_data(args)
    working = args.working if args.working else tempfile.mkdtemp()
    make_working(working)

    debian_distros = args.distros
    if not debian_distros:
        debian_distros = \
            rosdep2.catkin_support.get_ubuntu_targets(args.rosdistro)

    try:
        for debian_distro in debian_distros:
            # XXX TODO: Why is this copy needed, should it be deepcopy,
            # is it related to the lack of packages in deb descriptions?
            data = copy.copy(stack_data)
            generate_deb(data, ".", stamp, args.rosdistro, debian_distro)
            commit_debian(data, ".")
            tag_name = 'debian/' \
                '%(Package)s_%(Version)s-%(DebianInc)s_%(Distribution)s' % data
            print("tag: %s" % tag_name)
            call(".", ['git', 'tag', '-f', tag_name, '-m',
                 'Debian release %(Version)s' % data])
    except rosdep2.catkin_support.ValidationFailed as e:
        print(e.args[0], file=sys.stderr)
        return 1
    except (KeyError, rosdep2.ResolutionError) as e:
        rosdep_key = str(e)
        if not isinstance(e, KeyError):
            rosdep_key = e.rosdep_key
        print("""\
Cannot resolve dependency [{0}].

If [{0}] is catkin project, make sure it has been added to the gbpdistro file.

If [{0}] is a system dependency, make sure there is a \
rosdep.yaml entry for it in your sources.
""".format(rosdep_key), file=sys.stderr)
        return 1
    return 0


def main(sysargs=None):
    # Parse the commandline arguments
    parser = get_argument_parser()
    parser = add_global_arguments(parser)
    args = parser.parse_args(sysargs)
    handle_global_arguments(args)

    # Ensure we are in a git repository
    if execute_command('git status') != 0:
        parser.print_help()
        bailout("This is not a valid git repository.")

    # Track all the branches
    track_branches()

    if execute_command('git show-ref refs/heads/bloom') != 0:
        bailout("This does not appear to be a bloom release repo. "
                "Please initialize it first using:\n\n"
                "  git bloom-set-upstream <UPSTREAM_VCS_URL> <VCS_TYPE> "
                "[<VCS_BRANCH>]")

    current_branch = get_current_branch()
    bloom_repo = VcsClient('git', os.getcwd())
    result = 0
    try:
        # update rosdep is needed
        if args.do_not_update_rosdep:
            info("Updating rosdep")
            rosdep2.catkin_support.update_rosdep()
        # do it
        result = execute_bloom_generate_debian(args, bloom_repo)
    finally:
        if current_branch:
            checkout(current_branch)
    return result
