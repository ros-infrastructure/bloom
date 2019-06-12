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

import json

import pkg_resources
import sys
import traceback

from bloom.git import inbranch
from bloom.git import get_branches
from bloom.git import get_commit_hash
from bloom.git import get_current_branch
from bloom.git import has_changes
from bloom.git import show
from bloom.git import tag_exists

from bloom.logging import ansi
from bloom.logging import debug
from bloom.logging import error
from bloom.logging import info
from bloom.logging import warning

from bloom.commands.git.patch.common import get_patch_config
from bloom.commands.git.patch.common import set_patch_config

from bloom.packages import get_package_data

from bloom.rosdistro_api import get_distribution_type

from bloom.util import code
from bloom.util import execute_command
from bloom.util import maybe_continue
from bloom.util import print_exc

try:
    from rosdep2 import create_default_installer_context
    from rosdep2.catkin_support import get_catkin_view
    from rosdep2.lookup import ResolutionError
    import rosdep2.catkin_support
except ImportError:
    debug(traceback.format_exc())
    error("rosdep was not detected, please install it.", exit=True)

try:
    import rosdistro
except ImportError:
    debug(traceback.format_exc())
    error("rosdistro was not detected, please install it.", exit=True)

BLOOM_GROUP = 'bloom.generators'
DEFAULT_ROS_DISTRO = 'indigo'


def list_generators():
    generators = []
    for entry_point in pkg_resources.iter_entry_points(group=BLOOM_GROUP):
        generators.append(entry_point.name)
    return generators


def load_generator(generator_name):
    for entry_point in pkg_resources.iter_entry_points(group=BLOOM_GROUP):
        if entry_point.name == generator_name:
            return entry_point.load()

view_cache = {}


def get_view(os_name, os_version, ros_distro):
    global view_cache
    key = os_name + os_version + ros_distro
    if key not in view_cache:
        value = get_catkin_view(ros_distro, os_name, os_version, False)
        view_cache[key] = value
    return view_cache[key]


def invalidate_view_cache():
    global view_cache
    view_cache = {}


def update_rosdep():
    info("Running 'rosdep update'...")
    try:
        rosdep2.catkin_support.update_rosdep()
    except:
        print_exc(traceback.format_exc())
        error("Failed to update rosdep, did you run 'rosdep init' first?",
              exit=True)


def resolve_more_for_os(rosdep_key, view, installer, os_name, os_version):
    """
    Resolve rosdep key to dependencies and installer key.
    (This was copied from rosdep2.catkin_support)

    :param os_name: OS name, e.g. 'ubuntu'
    :returns: resolved key, resolved installer key, and default installer key

    :raises: :exc:`rosdep2.ResolutionError`
    """
    d = view.lookup(rosdep_key)
    ctx = create_default_installer_context()
    os_installers = ctx.get_os_installer_keys(os_name)
    default_os_installer = ctx.get_default_os_installer_key(os_name)
    inst_key, rule = d.get_rule_for_platform(os_name, os_version,
                                             os_installers,
                                             default_os_installer)
    assert inst_key in os_installers
    return installer.resolve(rule), inst_key, default_os_installer


def package_conditional_context(ros_distro):
    distribution_type = get_distribution_type(ros_distro)
    if distribution_type == 'ros1':
        ros_version = '1'
    elif distribution_type == 'ros2':
        ros_version = '2'
    else:
        error("Bloom cannot cope with distribution_type '{0}'".format(
            distribution_type), exit=True)
    return {
            'ROS_VERSION': ros_version,
            'ROS_DISTRO': ros_distro,
            }


def resolve_rosdep_key(
    key,
    os_name,
    os_version,
    ros_distro=None,
    ignored=None,
    retry=True
):
    ignored = ignored or []
    ctx = create_default_installer_context()
    try:
        installer_key = ctx.get_default_os_installer_key(os_name)
    except KeyError:
        BloomGenerator.exit("Could not determine the installer for '{0}'"
                            .format(os_name))
    installer = ctx.get_installer(installer_key)
    ros_distro = ros_distro or DEFAULT_ROS_DISTRO
    view = get_view(os_name, os_version, ros_distro)
    try:
        return resolve_more_for_os(key, view, installer, os_name, os_version)
    except (KeyError, ResolutionError) as exc:
        debug(traceback.format_exc())
        if key in ignored:
            return None, None, None
        if isinstance(exc, KeyError):
            error("Could not resolve rosdep key '{0}'".format(key))
            returncode = code.GENERATOR_NO_SUCH_ROSDEP_KEY
        else:
            error("Could not resolve rosdep key '{0}' for distro '{1}':"
                  .format(key, os_version))
            info(str(exc), use_prefix=False)
            returncode = code.GENERATOR_NO_ROSDEP_KEY_FOR_DISTRO
        if retry:
            error("Try to resolve the problem with rosdep and then continue.")
            if maybe_continue():
                update_rosdep()
                invalidate_view_cache()
                return resolve_rosdep_key(key, os_name, os_version, ros_distro,
                                          ignored, retry=True)
        BloomGenerator.exit("Failed to resolve rosdep key '{0}', aborting."
                            .format(key), returncode=returncode)


def default_fallback_resolver(key, peer_packages):
    BloomGenerator.exit("Failed to resolve rosdep key '{0}', aborting."
                        .format(key), returncode=code.GENERATOR_NO_SUCH_ROSDEP_KEY)


def resolve_dependencies(
    keys,
    os_name,
    os_version,
    ros_distro=None,
    peer_packages=None,
    fallback_resolver=None
):
    ros_distro = ros_distro or DEFAULT_ROS_DISTRO
    peer_packages = peer_packages or []
    fallback_resolver = fallback_resolver or default_fallback_resolver

    resolved_keys = {}
    keys = [k.name for k in keys]
    for key in keys:
        resolved_key, installer_key, default_installer_key = \
            resolve_rosdep_key(key, os_name, os_version, ros_distro,
                               peer_packages, retry=True)
        # Do not compare the installer key here since this is a general purpose function
        # They installer is verified in the OS specific generator, when the keys are pre-checked.
        if resolved_key is None:
            resolved_key = fallback_resolver(key, peer_packages, os_name, os_version, ros_distro)
        resolved_keys[key] = resolved_key
    return resolved_keys


def match_branches_with_prefix(prefix, get_branches, prune=False):
    debug("match_branches_with_prefix(" + str(prefix) + ", " +
          str(get_branches()) + ")")
    branches = []
    # Match branches
    existing_branches = get_branches()
    for branch in existing_branches:
        if branch.startswith('remotes/origin/'):
            branch = branch.split('/', 2)[-1]
        if branch.startswith(prefix):
            branches.append(branch)
    branches = list(set(branches))
    if prune:
        # Prune listed branches by packages in latest upstream
        with inbranch('upstream'):
            pkg_names, version, pkgs_dict = get_package_data('upstream')
            for branch in branches:
                if branch.split(prefix)[-1].strip('/') not in pkg_names:
                    branches.remove(branch)
    return branches


class GeneratorError(Exception):
    def __init__(self, msg, returncode=code.UNKNOWN):
        super(GeneratorError, self).__init__("Error running generator: " + msg)
        self.returncode = returncode

    @staticmethod
    def excepthook(etype, value, traceback):
        GeneratorError.sysexcepthook(etype, value, traceback)
        if isinstance(value, GeneratorError):
            sys.exit(value.returncode)

    sys.excepthook, sysexcepthook = excepthook.__func__, staticmethod(sys.excepthook)


class BloomGenerator(object):
    """
    Abstract generator class, from which all bloom generators inherit.
    """
    generator_type = None
    title = 'no title'
    description = None
    help = None

    @classmethod
    def exit(cls, msg, returncode=code.UNKNOWN):
        raise GeneratorError(msg, returncode)

    def prepare_arguments(self, parser):
        """
        Argument preparation hook, should be implemented in child class

        :param parser: argparse.ArgumentParser on which to call add_argument()
        """
        pass

    def handle_arguments(self, args):
        """
        Hook to handle parsed arguments from argparse
        """
        debug("BloomGenerator.handle_arguments: got args -> " + str(args))

    def summarize(self):
        """
        Summarize the command, consider listing configurations here
        """
        info("Running " + self.title + " generator")

    def get_branching_arguments(self):
        """
        Return a list of tuples, each representing parameters for branching.

        Override this to return something other than [] if this generator
        needs to produce branches.

        The tuples can either be singular (destination,), or contain two
        elements (destination, source). Optionally, a third tuple element
        can be a bool indicating if git-bloom-branch should be interactive:
        (destination, source, interactive)

        :returns: list of tuples containing arguments for git-bloom-branch
        """
        return []

    def pre_modify(self):
        """
        Hook for last minute checks

        This is the last call before the generator is expected to start
        performing modifications to the repository.

        :returns: return code, return 0 or None for OK, anything else on error
        """
        return 0

    def pre_branch(self, destination, source):
        """
        Pre-branching hook

        :param destination: destination branch name
        :param source: source branch name

        :returns: return code, return 0 or None for OK, anythign else on error
        """
        return 0

    def post_branch(self, destination, source):
        """
        Post-branching hook

        :param destination: destination branch name
        :param source: source branch name

        :returns: return code, return 0 or None for OK, anythign else on error
        """
        return 0

    def pre_export_patches(self, branch_name):
        """
        Pre-patch-export hook

        :param branch_name: name of the branch patches are being exported from

        :returns: return code, return 0 or None for OK, anythign else on error
        """
        return 0

    def post_export_patches(self, branch_name):
        """
        Post-patch-export hook

        :param branch_name: name of the branch patches are being exported from

        :returns: return code, return 0 or None for OK, anythign else on error
        """
        return 0

    def pre_rebase(self, branch_name):
        """
        Pre-rebase hook

        :param branch_name: name of the branch rebase is being done on

        :returns: return code, return 0 or None for OK, anythign else on error
        """
        return 0

    def post_rebase(self, branch_name):
        """
        Post-rebase hook

        :param branch_name: name of the branch rebase is being done on

        :returns: return code, return 0 or None for OK, anythign else on error
        """
        return 0

    def pre_patch(self, branch_name):
        """
        Pre-patching hook

        :param branch_name: name of the branch being patched

        :returns: return code, return 0 or None for OK, anythign else on error
        """
        return 0

    def post_patch(self, branch_name):
        """
        Post-patching hook

        :param branch_name: name of the branch being patched

        :returns: return code, return 0 or None for OK, anythign else on error
        """
        return 0


class PackageSystemGenerator(BloomGenerator):
    package_system = 'none'
    has_run_rosdep = False

    def prepare_arguments(self, parser):
        # The common command line arguments for every package system
        add = parser.add_argument
        add('-i', '--inc', help="increment number", default='0')
        add('-p', '--prefix', required=True,
            help="branch prefix to match, and from which create packages"
                 " hint: if you want to match 'release/foo' use 'release'")
        add('-a', '--match-all', default=False, action="store_true",
            help="match all branches with the given prefix, "
                 "even if not in current upstream")
        add('--distros', nargs='+', required=False, default=[],
            help='A list of os distros to generate for certain package system')
        add('--install-prefix', default=None,
            help="overrides the default installation prefix (/usr)")

    def get_package_from_branch(self, branch):
        with inbranch(branch):
            try:
                package_data = get_package_data(branch)
            except SystemExit:
                return None
            if type(package_data) not in [list, tuple]:
                # It is a ret code
                self.exit(package_data)
        names, version, packages = package_data
        if type(names) is list and len(names) > 1:
            self.exit(
                "{0} generator does not support generating "
                "from branches with multiple packages in them, use "
                "the release generator first to split packages into "
                "individual branches."
                .format(self.package_system))
        if type(packages) is dict:
            return list(packages.values())[0]

    def get_default_distros(self):
        index = rosdistro.get_index(rosdistro.get_index_url())
        distribution_file = rosdistro.get_distribution_file(index, self.rosdistro)
        if self.os_name not in distribution_file.release_platforms:
            if hasattr(self, "os_not_required") and self.os_not_required:
                warning("No platforms defined for os '{0}' in release file for the "
                        "'{1}' distro. This os was not required; continuing without error."
                        .format(self.os_name, self.rosdistro))
                sys.exit(0)
            error("No platforms defined for os '{0}' in release file for the '{1}' distro."
                  .format(self.os_name, self.rosdistro), exit=True)
        self.distros = distribution_file.release_platforms[self.os_name]

    def handle_arguments(self, args):
        self.interactive = args.interactive
        self.inc = args.inc
        self.os_name = args.os_name
        self.distros = args.distros
        if self.distros in [None, []]:
            self.get_default_distros()
        self.install_prefix = args.install_prefix
        if args.install_prefix is None:
            self.install_prefix = self.default_install_prefix
        self.prefix = args.prefix
        self.branches = match_branches_with_prefix(self.prefix, get_branches, prune=not args.match_all)
        if len(self.branches) == 0:
            error(
                "No packages found, check your --prefix or --src arguments.",
                exit=True
            )
        self.packages = {}
        self.tag_names = {}
        self.names = []
        self.branch_args = []
        self.package_system_branches = []
        for branch in self.branches:
            package = self.get_package_from_branch(branch)
            if package is None:
                # This is an ignored package
                continue
            self.packages[package.name] = package
            self.names.append(package.name)
            args = self.generate_branching_arguments(package, branch)
            # First branch is package_system/[<rosdistro>/]<package>
            self.package_system_branches.append(args[0][0])
            self.branch_args.extend(args)

    def summarize(self):
        info("Generating {0} source for the packages: {1}".format(self.os_name, str(self.names)))
        info("Incremental Version: " + str(self.inc))
        info("Distributions: " + str(self.distros))

    def get_branching_arguments(self):
        return self.branch_args

    def update_rosdep(self):
        update_rosdep()
        self.has_run_rosdep = True

    def pre_branch(self, destination, source):
        if destination in self.package_system_branches:
            return
        # Run rosdep update is needed
        if not self.has_run_rosdep:
            self.update_rosdep()
        # Determine the current package being generated
        name = destination.split('/')[-1]
        distro = destination.split('/')[-2]
        # Retrieve the package
        package = self.packages[name]
        # Report on this package
        self.summarize_package(package, distro)

    def pre_rebase(self, destination):
        # Get the stored configs is any
        patches_branch = 'patches/' + destination
        config = self.load_original_config(patches_branch)
        if config is not None:
            curr_config = get_patch_config(patches_branch)
            if curr_config['parent'] == config['parent']:
                set_patch_config(patches_branch, config)

    def post_rebase(self, destination):
        name = destination.split('/')[-1]
        # Retrieve the package
        package = self.packages[name]
        # Handle differently if this is a package system vs distro branch
        if destination in self.package_system_branches:
            info("Placing {0} template files into '{1}' branch."
                 .format(self.package_system, destination))
            # Then this is a package system branch
            # Place the raw template files
            self.place_template_files(package.get_build_type())
        else:
            # This is a distro specific package system branch
            # Determine the current package being generated
            distro = destination.split('/')[-2]
            # Create package for each distro
            with inbranch(destination):
                data = self.generate_package(package, distro)
                # Create the tag name for later
                self.tag_names[destination] = self.generate_tag_name(data)
        # Update the patch configs
        patches_branch = 'patches/' + destination
        config = get_patch_config(patches_branch)
        # Store it
        self.store_original_config(config, patches_branch)
        # Modify the base so import/export patch works
        current_branch = get_current_branch()
        if current_branch is None:
            error("Could not determine current branch.", exit=True)
        config['base'] = get_commit_hash(current_branch)
        # Set it
        set_patch_config(patches_branch, config)

    def post_patch(self, destination, color='bluef'):
        if destination in self.package_system_branches:
            return
        # Tag after patches have been applied
        with inbranch(destination):
            # Tag
            tag_name = self.tag_names[destination]
            if tag_exists(tag_name):
                if self.interactive:
                    warning("Tag exists: " + tag_name)
                    warning("Do you wish to overwrite it?")
                    if not maybe_continue('y'):
                        error("Answered no to continue, aborting.", exit=True)
                else:
                    warning("Overwriting tag: " + tag_name)
            else:
                info("Creating tag: " + tag_name)
            execute_command('git tag -f ' + tag_name)
        # Report of success
        name = destination.split('/')[-1]
        package = self.packages[name]
        distro = destination.split('/')[-2]
        info(ansi(color) + "####" + ansi('reset'), use_prefix=False)
        info(
            ansi(color) + "#### " + ansi('greenf') + "Successfully" +
            ansi(color) + " generated '" + ansi('boldon') + distro +
            ansi('boldoff') + "' {0} for package".format(self.package_system) +
            " '" + ansi('boldon') + package.name + ansi('boldoff') + "'" +
            " at version '" + ansi('boldon') + package.version +
            "-" + str(self.inc) + ansi('boldoff') + "'" +
            ansi('reset'),
            use_prefix=False
        )
        info(ansi(color) + "####\n" + ansi('reset'), use_prefix=False)

    def store_original_config(self, config, patches_branch):
        with inbranch(patches_branch):
            with open('{0}.store'.format(self.package_system), 'w+') as f:
                f.write(json.dumps(config))
            execute_command('git add {0}.store'.format(self.package_system))
            if has_changes():
                execute_command('git commit -m "Store original patch config"')

    def load_original_config(self, patches_branch):
        config_store = show(patches_branch, '{0}.store'.format(self.package_system))
        if config_store is None:
            return config_store
        return json.loads(config_store)

    def generate_branching_arguments(self, package, branch):
        """
        The default branch for placing package system release data

        :param package: the package metadata extract from package.xml
        :param branch: every branch match the prefix in command line input

        :return: list of (destination, source, interactive)
        """
        n = package.name
        # package branch
        package_branch = self.package_system + '/' + n
        # Branch first to the package branch
        args = [[package_branch, branch, False]]
        # Then for each os distro, branch from the base package branch
        args.extend([
            [self.package_system + '/' + d + '/' + n, package_branch, False]
            for d in self.distros
        ])
        return args

    def summarize_package(self, package, distro, color='bluef'):
        info(ansi(color) + "\n####" + ansi('reset'), use_prefix=False)
        info(
            ansi(color) + "#### Generating '" + ansi('boldon') + distro +
            ansi('boldoff') + "' {0} for package".format(self.package_system) +
            " '" + ansi('boldon') + package.name + ansi('boldoff') + "'" +
            " at version '" + ansi('boldon') + package.version +
            "-" + str(self.inc) + ansi('boldoff') + "'" +
            ansi('reset'),
            use_prefix=False
        )
        info(ansi(color) + "####" + ansi('reset'), use_prefix=False)

    def generate_package(self, package, os_version):
        """
        Assume we have the templactes file in <package_system> directory
        The overriten function should generate the package, including
        1. use the result of get_subs to replace template content
        2. set the newest release history
        3. some git commit operation

        :param package: the substitute for in place of the templacte content
        :param os_version: the specific operate system version

        :returns: substitutes for other use
        """
        raise NotImplemented

    def generate_tag_name(self, subs):
        """
        Generate tag name based on the substitute, this method need be overwriten

        :param subs: the substitute for in place of the templacte content

        :returns: tag name
        """
        raise NotImplemented
