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

import collections
import json
import io
import os
import pkg_resources
import shutil
import sys
import traceback

from bloom.commands.git.patch.common import get_patch_config
from bloom.commands.git.patch.common import set_patch_config

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
from bloom.logging import fmt
from bloom.logging import info
from bloom.logging import warning

from bloom.packages import get_package_data

from bloom.rosdistro_api import get_distribution_type

from bloom.util import code
from bloom.util import execute_command
from bloom.util import maybe_continue
from bloom.util import print_exc

try:
    from configparser import SafeConfigParser
except ImportError:
    from ConfigParser import SafeConfigParser

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

try:
    import em
except ImportError:
    debug(traceback.format_exc())
    error("empy was not detected, please install it.", exit=True)

# Fix unicode bug in empy
# This should be removed once upstream empy is fixed
# See: https://github.com/ros-infrastructure/bloom/issues/196
try:
    em.str = unicode
    em.Stream.write_old = em.Stream.write
    em.Stream.write = lambda self, data: em.Stream.write_old(self, data.encode('utf8'))
except NameError:
    pass
# End fix

BLOOM_GROUP = 'bloom.generators'
DEFAULT_ROS_DISTRO = 'indigo'
TEMPLATE_EXTENSION = '.em'


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


def generate_substitutions_from_package(
    package,
    os_name,
    os_version,
    ros_distro,
    format_description,
    format_depends,
    installation_prefix='/usr',
    inc=0,
    peer_packages=None,
    fallback_resolver=None,
    native=False
):
    peer_packages = peer_packages or []
    data = {}
    # Name, Version, Description
    data['Name'] = package.name
    data['Version'] = package.version
    data['Description'] = format_description(package.description)
    # Websites
    websites = [str(url) for url in package.urls if url.type == 'website']
    homepage = websites[0] if websites else ''
    if homepage == '':
        warning("No homepage set, defaulting to ''")
    data['Homepage'] = homepage
    # Increment Number
    data['Inc'] = '' if native else '-{0}'.format(inc)
    # Package name
    data['Package'] = sanitize_package_name(package.name)
    # Installation prefix
    data['InstallationPrefix'] = installation_prefix
    # Resolve dependencies
    package.evaluate_conditions(package_conditional_context(ros_distro))
    depends = [
        dep for dep in (package.run_depends + package.buildtool_export_depends)
        if dep.evaluated_condition]
    build_depends = [
        dep for dep in (package.build_depends + package.buildtool_depends + package.test_depends)
        if dep.evaluated_condition]

    unresolved_keys = [
        dep for dep in (depends + build_depends + package.replaces + package.conflicts)
        if dep.evaluated_condition]
    # The installer key is not considered here, but it is checked when the keys are checked before this
    resolved_deps = resolve_dependencies(unresolved_keys, os_name,
                                         os_version, ros_distro,
                                         peer_packages + [d.name for d in package.replaces + package.conflicts],
                                         fallback_resolver)
    data['Depends'] = sorted(
        set(format_depends(depends, resolved_deps))
    )
    data['BuildDepends'] = sorted(
        set(format_depends(build_depends, resolved_deps))
    )
    data['Replaces'] = sorted(
        set(format_depends(package.replaces, resolved_deps))
    )
    data['Conflicts'] = sorted(
        set(format_depends(package.conflicts, resolved_deps))
    )

    # Build-type specific substitutions.
    build_type = package.get_build_type()
    if build_type == 'catkin':
        pass
    elif build_type == 'cmake':
        pass
    elif build_type == 'ament_cmake':
        pass
    elif build_type == 'ament_python':
        # Don't set the install-scripts flag if it's already set in setup.cfg.
        package_path = os.path.abspath(os.path.dirname(package.filename))
        setup_cfg_path = os.path.join(package_path, 'setup.cfg')
        data['pass_install_scripts'] = True
        if os.path.isfile(setup_cfg_path):
            setup_cfg = SafeConfigParser()
            setup_cfg.read([setup_cfg_path])
            if (
                    setup_cfg.has_option('install', 'install-scripts') or
                    setup_cfg.has_option('install', 'install_scripts')
            ):
                data['pass_install_scripts'] = False
    else:
        error("Build type '{}' is not supported by this version of bloom.".
              format(build_type), exit=True)

    # Set the distribution
    data['Distribution'] = os_version
    # Maintainers
    maintainers = []
    for m in package.maintainers:
        maintainers.append(str(m))
    data['Maintainer'] = maintainers[0]
    data['Maintainers'] = ', '.join(maintainers)

    # Summarize dependencies
    summarize_dependency_mapping(data, depends, build_depends, resolved_deps)

    return data


def __place_template_folder(group, src, dst, gbp=False):
    template_files = pkg_resources.resource_listdir(group, src)
    # For each template, place
    for template_file in template_files:
        if not gbp and os.path.basename(template_file) == 'gbp.conf.em':
            debug("Skipping template '{0}'".format(template_file))
            continue
        template_path = os.path.join(src, template_file)
        template_dst = os.path.join(dst, template_file)
        if pkg_resources.resource_isdir(group, template_path):
            debug("Recursing on folder '{0}'".format(template_path))
            __place_template_folder(group, template_path, template_dst, gbp)
        else:
            try:
                debug("Placing template '{0}'".format(template_path))
                template = pkg_resources.resource_string(group, template_path)
                template_abs_path = pkg_resources.resource_filename(group, template_path)
            except IOError as err:
                error("Failed to load template "
                      "'{0}': {1}".format(template_file, str(err)), exit=True)
            if not os.path.exists(dst):
                os.makedirs(dst)
            if os.path.exists(template_dst):
                debug("Not overwriting existing file '{0}'".format(template_dst))
            else:
                with io.open(template_dst, 'w', encoding='utf-8') as f:
                    if not isinstance(template, str):
                        template = template.decode('utf-8')
                    # Python 2 API needs a `unicode` not a utf-8 string.
                    elif sys.version_info.major == 2:
                        template = template.decode('utf-8')
                    f.write(template)
                shutil.copystat(template_abs_path, template_dst)


def convertToUnicode(obj):
    if sys.version_info.major == 2:
        if isinstance(obj, str):
            return unicode(obj.decode('utf8'))
        elif isinstance(obj, unicode):
            return obj
    else:
        if isinstance(obj, bytes):
            return str(obj.decode('utf8'))
        elif isinstance(obj, str):
            return obj
    if isinstance(obj, list):
        for i, val in enumerate(obj):
            obj[i] = convertToUnicode(val)
        return obj
    elif isinstance(obj, type(None)):
        return None
    elif isinstance(obj, tuple):
        obj_tmp = list(obj)
        for i, val in enumerate(obj_tmp):
            obj_tmp[i] = convertToUnicode(obj_tmp[i])
        return tuple(obj_tmp)
    elif isinstance(obj, int):
        return obj
    raise RuntimeError('need to deal with type %s' % (str(type(obj))))


def place_template_files(path, build_type, package_manager, gbp=False):
    info(fmt("@!@{bf}==>@| Placing templates files in the '" + package_manager + "' folder."))
    dir_path = os.path.join(path, package_manager)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    # Place template files
    group = 'bloom.generators.' + package_manager
    templates = os.path.join('templates', build_type)
    __place_template_folder(group, templates, dir_path, gbp)


def summarize_dependency_mapping(data, deps, build_deps, resolved_deps):
    if len(deps) == 0 and len(build_deps) == 0:
        return
    info("Package '" + data['Package'] + "' has dependencies:")
    header = "  " + ansi('boldoff') + ansi('ulon') + \
             "rosdep key           => " + data['Distribution'] + \
             " key" + ansi('reset')
    template = "  " + ansi('cyanf') + "{0:<20} " + ansi('purplef') + \
               "=> " + ansi('cyanf') + "{1}" + ansi('reset')
    if len(deps) != 0:
        info(ansi('purplef') + "Run Dependencies:" +
             ansi('reset'))
        info(header)
        for key in [d.name for d in deps]:
            info(template.format(key, resolved_deps[key]))
    if len(build_deps) != 0:
        info(ansi('purplef') +
             "Build and Build Tool Dependencies:" + ansi('reset'))
        info(header)
        for key in [d.name for d in build_deps]:
            info(template.format(key, resolved_deps[key]))


def __process_template_folder(path, subs):
    items = os.listdir(path)
    processed_items = []
    for item in list(items):
        item = os.path.abspath(os.path.join(path, item))
        if os.path.basename(item) in ['.', '..', '.git', '.svn']:
            continue
        if os.path.isdir(item):
            sub_items = __process_template_folder(item, subs)
            processed_items.extend([os.path.join(item, s) for s in sub_items])
        if not item.endswith(TEMPLATE_EXTENSION):
            continue
        with open(item, 'r') as f:
            template = f.read()
        # Remove extension
        template_path = item[:-len(TEMPLATE_EXTENSION)]
        # Expand template
        info("Expanding '{0}' -> '{1}'".format(
            os.path.relpath(item),
            os.path.relpath(template_path)))
        result = em.expand(template, **subs)
        # Don't write an empty file
        if len(result) == 0 and \
                os.path.basename(template_path) in ['copyright']:
            processed_items.append(item)
            continue
        # Write the result
        with io.open(template_path, 'w', encoding='utf-8') as f:
            if sys.version_info.major == 2:
                result = result.decode('utf-8')
            f.write(result)
        # Copy the permissions
        shutil.copymode(item, template_path)
        processed_items.append(item)
    return processed_items


def process_template_files(path, subs, pacakge_manager):
    info(fmt("@!@{bf}==>@| In place processing templates files in '" + pacakge_manager + "' folder."))
    dir_path = os.path.join(path, pacakge_manager)
    if not os.path.exists(dir_path):
        sys.exit("No {0} directory found at '{1}', cannot process templates."
                 .format(pacakge_manager, dir_path))
    return __process_template_folder(dir_path, subs)


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


def rosify_package_name(name, rosdistro):
    return 'ros-{0}-{1}'.format(rosdistro, name)


def sanitize_package_name(name):
    return name.replace('_', '-')


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


class PackageManagerGenerator(BloomGenerator):
    package_manager = 'none'
    has_run_rosdep = False
    default_install_prefix = '/usr'
    rosdistro = os.environ.get('ROS_DISTRO', 'indigo')

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
                .format(self.package_manager))
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
        self.package_manager_branches = []
        for branch in self.branches:
            package = self.get_package_from_branch(branch)
            if package is None:
                # This is an ignored package
                continue
            self.packages[package.name] = package
            self.names.append(package.name)
            args = self.generate_branching_arguments(package, branch)
            # First branch is package_manager/[<rosdistro>/]<package>
            self.package_manager_branches.append(args[0][0])
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

    def _check_all_keys_are_valid(self, peer_packages, rosdistro):
        keys_to_resolve = []
        key_to_packages_which_depends_on = collections.defaultdict(list)
        keys_to_ignore = set()
        for package in self.packages.values():
            package.evaluate_conditions(package_conditional_context(rosdistro))
            depends = [
                dep for dep in (package.run_depends + package.buildtool_export_depends)
                if dep.evaluated_condition]
            build_depends = [
                dep for dep in (package.build_depends + package.buildtool_depends + package.test_depends)
                if dep.evaluated_condition]
            unresolved_keys = [
                dep for dep in (depends + build_depends + package.replaces + package.conflicts)
                if dep.evaluated_condition]
            keys_to_ignore = {
                    dep for dep in keys_to_ignore.union(package.replaces + package.conflicts)
                    if dep.evaluated_condition}
            keys = [d.name for d in unresolved_keys]
            keys_to_resolve.extend(keys)
            for key in keys:
                key_to_packages_which_depends_on[key].append(package.name)

        os_name = self.os_name
        rosdistro = self.rosdistro
        all_keys_valid = True
        for key in sorted(set(keys_to_resolve)):
            for os_version in self.distros:
                try:
                    extended_peer_packages = peer_packages + [d.name for d in keys_to_ignore]
                    rule, installer_key, default_installer_key = \
                        resolve_rosdep_key(key, os_name, os_version, rosdistro, extended_peer_packages,
                                           retry=False)
                    if rule is None:
                        continue
                    if installer_key != default_installer_key:
                        error("Key '{0}' resolved to '{1}' with installer '{2}', "
                              "which does not match the default installer '{3}'."
                              .format(key, rule, installer_key, default_installer_key))
                        self.exit(
                            "The {0} generator does not support dependencies "
                            "which are installed with the '{1}' installer."
                            .format(self.package_manager, installer_key),
                            returncode=code.GENERATOR_INVALID_INSTALLER_KEY)
                except (GeneratorError, RuntimeError) as e:
                    print(fmt("Failed to resolve @{cf}@!{key}@| on @{bf}{os_name}@|:@{cf}@!{os_version}@| with: {e}")
                          .format(**locals()))
                    print(fmt("@{cf}@!{0}@| is depended on by these packages: ").format(key) +
                          str(list(set(key_to_packages_which_depends_on[key]))))
                    print(fmt("@{kf}@!<== @{rf}@!Failed@|"))
                    all_keys_valid = False
        return all_keys_valid

    def _pre_modify(self, key_unvalid_error_msg):
        info("\nPre-verifying {0} dependency keys...".format(self.package_manager))
        # Run rosdep update is needed
        if not self.has_run_rosdep:
            self.update_rosdep()

        peer_packages = [p.name for p in self.packages.values()]

        while not self._check_all_keys_are_valid(peer_packages, self.rosdistro):
            error(key_unvalid_error_msg)
            try:
                if not maybe_continue(msg="Would you like to try again?"):
                    error("User aborted after rosdep keys were not resolved.")
                    sys.exit(code.GENERATOR_NO_ROSDEP_KEY_FOR_DISTRO)
            except (KeyboardInterrupt, EOFError):
                error("\nUser quit.", exit=True)
            update_rosdep()
            invalidate_view_cache()

        info("All keys are " + ansi('greenf') + "OK" + ansi('reset') + "\n")

    def pre_branch(self, destination, source):
        if destination in self.package_manager_branches:
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
        if destination in self.package_manager_branches:
            info("Placing {0} template files into '{1}' branch."
                 .format(self.package_manager, destination))
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
        if destination in self.package_manager_branches:
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
            ansi('boldoff') + "' {0} for package".format(self.package_manager) +
            " '" + ansi('boldon') + package.name + ansi('boldoff') + "'" +
            " at version '" + ansi('boldon') + package.version +
            "-" + str(self.inc) + ansi('boldoff') + "'" +
            ansi('reset'),
            use_prefix=False
        )
        info(ansi(color) + "####\n" + ansi('reset'), use_prefix=False)

    def store_original_config(self, config, patches_branch):
        with inbranch(patches_branch):
            with open('{0}.store'.format(self.package_manager), 'w+') as f:
                f.write(json.dumps(config))
            execute_command('git add {0}.store'.format(self.package_manager))
            if has_changes():
                execute_command('git commit -m "Store original patch config"')

    def load_original_config(self, patches_branch):
        config_store = show(patches_branch, '{0}.store'.format(self.package_manager))
        if config_store is None:
            return config_store
        return json.loads(config_store)

    def get_releaser_history(self):
        # Assumes that this is called in the target branch
        patches_branch = 'patches/' + get_current_branch()
        raw = show(patches_branch, 'releaser_history.json')
        return None if raw is None else json.loads(raw)

    def set_releaser_history(self, history):
        # Assumes that this is called in the target branch
        patches_branch = 'patches/' + get_current_branch()
        debug("Writing release history to '{0}' branch".format(patches_branch))
        with inbranch(patches_branch):
            with open('releaser_history.json', 'w') as f:
                f.write(json.dumps(history))
            execute_command('git add releaser_history.json')
            if has_changes():
                execute_command('git commit -m "Store releaser history"')

    @staticmethod
    def missing_dep_resolver(key, peer_packages, os_name, os_version, ros_distro):
        """
        This should be a staticmethod since we will use it when we call
        `generate_substitutions_from_package` in `get_subs`
        Notice that os_name, os_version, ros_distro maybe useful when we
        want to add new resolver in the future
        """
        if key in peer_packages:
            return [sanitize_package_name(key)]
        return default_fallback_resolver(key, peer_packages)

    def place_template_files(self, build_type, dir_path=None):
        # Create/Clean the package system folder
        if dir_path is None:
            dir_path = os.path.join(".", self.package_manager)
        if os.path.exists(dir_path):
            if self.interactive:
                warning("{0} directory exists: {1}".format(self.package_manager, dir_path))
                warning("Do you wish to overwrite it?")
                if not maybe_continue('y'):
                    error("Answered no to continue, aborting.", exit=True)
            elif 'BLOOM_CLEAR_TEMPLATE_ON_GENERATION' in os.environ:
                warning("Overwriting {0} directory: {1}".format(self.package_manager, dir_path))
                execute_command('git rm -rf ' + dir_path)
                execute_command('git commit -m "Clearing previous {0} folder"'
                                .format(self.package_manager))
                if os.path.exists(dir_path):
                    shutil.rmtree(dir_path)
            else:
                warning("Not overwriting {0} directory.".format(self.package_manager))
        # Use generic place template files command
        place_template_files('.', build_type, self.package_manager, gbp=True)
        # Commit results
        execute_command('git add ' + dir_path)
        _, has_files, _ = execute_command('git diff --cached --name-only', return_io=True)
        if has_files:
            execute_command('git commit -m "Placing {0} template files"'.format(self.package_manager))

    def get_subs(self, package, os_version, format_description, format_depends, releaser_history=None):
        # This is the common part for generate templacte substitute, then successor of
        # the generator will add its specic content via define its get_subs_hook function
        subs = generate_substitutions_from_package(
            package,
            self.os_name,
            os_version,
            self.rosdistro,
            format_description,
            format_depends,
            self.install_prefix,
            self.inc,
            [p.name for p in self.packages.values()],
            fallback_resolver=self.missing_dep_resolver
        )
        subs['release_tag'] = 'release/{0}/{1}-{2}'.format(subs['Name'], subs['Version'], self.inc)
        subs = self.get_subs_hook(subs, package, self.rosdistro, releaser_history=releaser_history)
        for item in subs.items():
            subs[item[0]] = convertToUnicode(item[1])
        return subs

    def summarize_package(self, package, distro, color='bluef'):
        info(ansi(color) + "\n####" + ansi('reset'), use_prefix=False)
        info(
            ansi(color) + "#### Generating '" + ansi('boldon') + distro +
            ansi('boldoff') + "' {0} for package".format(self.package_manager) +
            " '" + ansi('boldon') + package.name + ansi('boldoff') + "'" +
            " at version '" + ansi('boldon') + package.version +
            "-" + str(self.inc) + ansi('boldoff') + "'" +
            ansi('reset'),
            use_prefix=False
        )
        info(ansi(color) + "####" + ansi('reset'), use_prefix=False)

    def generate_branching_arguments(self, package, branch):
        """
        The default branch for placing package system release data

        :param package: the package metadata extract from package.xml
        :param branch: every branch match the prefix in command line input

        :return: list of (destination, source, interactive)
        """
        n = package.name
        # package branch
        package_branch = self.package_manager + '/' + n
        # Branch first to the package branch
        args = [[package_branch, branch, False]]
        # Then for each os distro, branch from the base package branch
        args.extend([
            [self.package_manager + '/' + d + '/' + n, package_branch, False]
            for d in self.distros
        ])
        return args

    def generate_package(self, package, os_version):
        """
        Assume we have the templactes file in <package_manager> directory
        The overriten function should generate the package, including
        1. use the result of get_subs to replace template content
        2. set the newest release history
        3. some git commit operation

        :param package: the substitute for in place of the templacte content
        :param os_version: the specific operate system version

        :returns: substitutes for other use
        """
        raise NotImplemented

    @staticmethod
    def get_subs_hook(subs, package, rosdistro, releaser_history=None):
        """
        The specific package system related substitute operation

        :param subs: the substitute for in place of the template content
        :param package: the substitute for in place of the templacte content
        :param rosdistro: the ros version
        :param releaser_history: the substitute for in place of the templacte content

        :returns: the improved subs
        """
        return subs

    def generate_tag_name(self, subs):
        """
        Generate tag name based on the substitute, this method need be overwriten

        :param subs: the substitute for in place of the templacte content

        :returns: tag name
        """
        raise NotImplemented
