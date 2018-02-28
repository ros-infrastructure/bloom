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
import datetime
import io
import json
import os
import pkg_resources
import re
import shutil
import sys
import traceback
import textwrap

# Python 2/3 support.
try:
    from configparser import SafeConfigParser
except ImportError:
    from ConfigParser import SafeConfigParser
from dateutil import tz
from distutils.version import LooseVersion
from time import strptime

from bloom.generators import BloomGenerator
from bloom.generators import GeneratorError
from bloom.generators import resolve_dependencies
from bloom.generators import update_rosdep

from bloom.generators.common import default_fallback_resolver
from bloom.generators.common import invalidate_view_cache
from bloom.generators.common import resolve_rosdep_key

from bloom.git import inbranch
from bloom.git import get_branches
from bloom.git import get_commit_hash
from bloom.git import get_current_branch
from bloom.git import has_changes
from bloom.git import show
from bloom.git import tag_exists

from bloom.logging import ansi
from bloom.logging import debug
from bloom.logging import enable_drop_first_log_prefix
from bloom.logging import error
from bloom.logging import fmt
from bloom.logging import info
from bloom.logging import warning

from bloom.commands.git.patch.common import get_patch_config
from bloom.commands.git.patch.common import set_patch_config

from bloom.packages import get_package_data

from bloom.util import code
from bloom.util import execute_command
from bloom.util import maybe_continue

try:
    import rosdistro
except ImportError as err:
    debug(traceback.format_exc())
    error("rosdistro was not detected, please install it.", exit=True)

try:
    import em
except ImportError:
    debug(traceback.format_exc())
    error("empy was not detected, please install it.", exit=True)

# Drop the first log prefix for this command
enable_drop_first_log_prefix(True)

TEMPLATE_EXTENSION = '.em'


def __place_template_folder(group, src, dst, gbp=False):
    template_files = pkg_resources.resource_listdir(group, src)
    # For each template, place
    for template_file in template_files:
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
                debug("Removing existing file '{0}'".format(template_dst))
                os.remove(template_dst)
            with open(template_dst, 'w') as f:
                if not isinstance(template, str):
                    template = template.decode('utf-8')
                f.write(template)
            shutil.copystat(template_abs_path, template_dst)


def place_template_files(path, build_type, gbp=False):
    info(fmt("@!@{bf}==>@| Placing templates files in the 'rpm' folder."))
    rpm_path = os.path.join(path, 'rpm')
    # Create/Clean the rpm folder
    if not os.path.exists(rpm_path):
        os.makedirs(rpm_path)
    # Place template files
    group = 'bloom.generators.rpm'
    templates = os.path.join('templates', build_type)
    __place_template_folder(group, templates, rpm_path, gbp)


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


def format_depends(depends, resolved_deps):
    versions = {
        'version_lt': '<',
        'version_lte': '<=',
        'version_eq': '=',
        'version_gte': '>=',
        'version_gt': '>'
    }
    formatted = []
    for d in depends:
        for resolved_dep in resolved_deps[d.name]:
            version_depends = [k
                               for k in versions.keys()
                               if getattr(d, k, None) is not None]
            if not version_depends:
                formatted.append(resolved_dep)
            else:
                for v in version_depends:
                    formatted.append("{0} {1} {2}".format(
                        resolved_dep, versions[v], getattr(d, v)))
    return formatted


def missing_dep_resolver(key, peer_packages):
    if key in peer_packages:
        return [sanitize_package_name(key)]
    return default_fallback_resolver(key, peer_packages)


def generate_substitutions_from_package(
    package,
    os_name,
    os_version,
    ros_distro,
    installation_prefix='/usr',
    rpm_inc=0,
    peer_packages=None,
    releaser_history=None,
    fallback_resolver=None
):
    peer_packages = peer_packages or []
    data = {}
    # Name, Version, Description
    data['Name'] = package.name
    data['Version'] = package.version
    data['Description'] = rpmify_string(package.description)
    # License
    if not package.licenses or not package.licenses[0]:
        error("No license set for package '{0}', aborting.".format(package.name), exit=True)
    data['License'] = package.licenses[0]
    # Websites
    websites = [str(url) for url in package.urls if url.type == 'website']
    data['Homepage'] = websites[0] if websites else ''
    if data['Homepage'] == '':
        warning("No homepage set")
    # RPM Increment Number
    data['RPMInc'] = rpm_inc
    # Package name
    data['Package'] = sanitize_package_name(package.name)
    # Installation prefix
    data['InstallationPrefix'] = installation_prefix
    # Resolve dependencies
    depends = package.run_depends + package.buildtool_export_depends
    build_depends = package.build_depends + package.buildtool_depends + package.test_depends
    unresolved_keys = depends + build_depends + package.replaces + package.conflicts
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
        error(
            "Build type '{}' is not supported by this version of bloom.".
            format(build_type), exit=True)
    elif build_type == 'ament_python':
        error(
            "Build type '{}' is not supported by this version of bloom.".
            format(build_type), exit=True)
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
        error(
            "Build type '{}' is not supported by this version of bloom.".
            format(build_type), exit=True)

    # Set the distribution
    data['Distribution'] = os_version
    # Use the time stamp to set the date strings
    stamp = datetime.datetime.now(tz.tzlocal())
    data['Date'] = stamp.strftime('%a %b %d %Y')
    # Maintainers
    maintainers = []
    for m in package.maintainers:
        maintainers.append(str(m))
    data['Maintainer'] = maintainers[0]
    data['Maintainers'] = ', '.join(maintainers)
    # Changelog
    if releaser_history:
        sorted_releaser_history = sorted(releaser_history,
                                         key=lambda k: LooseVersion(k), reverse=True)
        sorted_releaser_history = sorted(sorted_releaser_history,
                                         key=lambda k: strptime(releaser_history.get(k)[0], '%a %b %d %Y'),
                                         reverse=True)
        changelogs = [(v, releaser_history[v]) for v in sorted_releaser_history]
    else:
        # Ensure at least a minimal changelog
        changelogs = []
    if package.version + '-' + str(rpm_inc) not in [x[0] for x in changelogs]:
        changelogs.insert(0, (
            package.version + '-' + str(rpm_inc), (
                data['Date'],
                package.maintainers[0].name,
                package.maintainers[0].email
            )
        ))
    exported_tags = [e.tagname for e in package.exports]
    data['NoArch'] = 'metapackage' in exported_tags or 'architecture_independent' in exported_tags
    data['changelogs'] = changelogs
    # Summarize dependencies
    summarize_dependency_mapping(data, depends, build_depends, resolved_deps)

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
        elif isinstance(obj, int):
            return obj
        raise RuntimeError('need to deal with type %s' % (str(type(obj))))

    for item in data.items():
        data[item[0]] = convertToUnicode(item[1])

    return data


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
        # Write the result
        with io.open(template_path, 'w', encoding='utf-8') as f:
            if sys.version_info.major == 2:
                result = result.decode('utf-8')
            f.write(result)
        # Copy the permissions
        shutil.copymode(item, template_path)
        processed_items.append(item)
    return processed_items


def process_template_files(path, subs):
    info(fmt("@!@{bf}==>@| In place processing templates in 'rpm' folder."))
    rpm_dir = os.path.join(path, 'rpm')
    if not os.path.exists(rpm_dir):
        sys.exit("No rpm directory found at '{0}', cannot process templates."
                 .format(rpm_dir))
    return __process_template_folder(rpm_dir, subs)


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


def get_package_from_branch(branch):
    with inbranch(branch):
        try:
            package_data = get_package_data(branch)
        except SystemExit:
            return None
        if type(package_data) not in [list, tuple]:
            # It is a ret code
            RpmGenerator.exit(package_data)
    names, version, packages = package_data
    if type(names) is list and len(names) > 1:
        RpmGenerator.exit(
            "RPM generator does not support generating "
            "from branches with multiple packages in them, use "
            "the release generator first to split packages into "
            "individual branches.")
    if type(packages) is dict:
        return list(packages.values())[0]


def rpmify_string(value):
    markup_remover = re.compile(r'<.*?>')
    value = markup_remover.sub('', value)
    value = re.sub('\s+', ' ', value)
    value = '\n'.join([v.strip() for v in
                      textwrap.TextWrapper(width=80, break_long_words=False, replace_whitespace=False).wrap(value)])
    return value


def sanitize_package_name(name):
    return name.replace('_', '-')


class RpmGenerator(BloomGenerator):
    title = 'rpm'
    description = "Generates RPMs from the catkin meta data"
    has_run_rosdep = False
    default_install_prefix = '/usr'
    rosdistro = os.environ.get('ROS_DISTRO', 'indigo')

    def prepare_arguments(self, parser):
        # Add command line arguments for this generator
        add = parser.add_argument
        add('-i', '--rpm-inc', help="RPM increment number", default='0')
        add('-p', '--prefix', required=True,
            help="branch prefix to match, and from which create RPMs"
                 " hint: if you want to match 'release/foo' use 'release'")
        add('-a', '--match-all', default=False, action="store_true",
            help="match all branches with the given prefix, "
                 "even if not in current upstream")
        add('--distros', nargs='+', required=False, default=[],
            help='A list of RPM (fedora) distros to generate for')
        add('--install-prefix', default=None,
            help="overrides the default installation prefix (/usr)")
        add('--os-name', default='fedora',
            help="overrides os_name, set to 'fedora' by default")

    def handle_arguments(self, args):
        self.interactive = args.interactive
        self.rpm_inc = args.rpm_inc
        self.os_name = args.os_name
        self.distros = args.distros
        if self.distros in [None, []]:
            index = rosdistro.get_index(rosdistro.get_index_url())
            distribution_file = rosdistro.get_distribution_file(index, self.rosdistro)
            if self.os_name not in distribution_file.release_platforms:
                warning("No platforms defined for os '{0}' in release file for the '{1}' distro."
                        "\nNot performing RPM generation."
                        .format(self.os_name, self.rosdistro))
                sys.exit(0)
            self.distros = distribution_file.release_platforms[self.os_name]
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
        self.rpm_branches = []
        for branch in self.branches:
            package = get_package_from_branch(branch)
            if package is None:
                # This is an ignored package
                continue
            self.packages[package.name] = package
            self.names.append(package.name)
            args = self.generate_branching_arguments(package, branch)
            # First branch is rpm/[<rosdistro>/]<package>
            self.rpm_branches.append(args[0][0])
            self.branch_args.extend(args)

    def summarize(self):
        info("Generating source RPMs for the packages: " + str(self.names))
        info("RPM Incremental Version: " + str(self.rpm_inc))
        info("RPM Distributions: " + str(self.distros))

    def get_branching_arguments(self):
        return self.branch_args

    def update_rosdep(self):
        update_rosdep()
        self.has_run_rosdep = True

    def _check_all_keys_are_valid(self, peer_packages):
        keys_to_resolve = []
        key_to_packages_which_depends_on = collections.defaultdict(list)
        keys_to_ignore = set()
        for package in self.packages.values():
            depends = package.run_depends + package.buildtool_export_depends
            build_depends = package.build_depends + package.buildtool_depends + package.test_depends
            unresolved_keys = depends + build_depends + package.replaces + package.conflicts
            keys_to_ignore = keys_to_ignore.union(package.replaces + package.conflicts)
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
                        BloomGenerator.exit(
                            "The RPM generator does not support dependencies "
                            "which are installed with the '{0}' installer."
                            .format(installer_key),
                            returncode=code.GENERATOR_INVALID_INSTALLER_KEY)
                except (GeneratorError, RuntimeError) as e:
                    print(fmt("Failed to resolve @{cf}@!{key}@| on @{bf}{os_name}@|:@{cf}@!{os_version}@| with: {e}")
                          .format(**locals()))
                    print(fmt("@{cf}@!{0}@| is depended on by these packages: ").format(key) +
                          str(list(set(key_to_packages_which_depends_on[key]))))
                    print(fmt("@{kf}@!<== @{rf}@!Failed@|"))
                    all_keys_valid = False
        return all_keys_valid

    def pre_modify(self):
        info("\nPre-verifying RPM dependency keys...")
        # Run rosdep update is needed
        if not self.has_run_rosdep:
            self.update_rosdep()

        peer_packages = [p.name for p in self.packages.values()]

        while not self._check_all_keys_are_valid(peer_packages):
            error("Some of the dependencies for packages in this repository could not be resolved by rosdep.")
            error("You can try to address the issues which appear above and try again if you wish, "
                  "or continue without releasing into RPM-based distributions (e.g. Fedora 24).")
            try:
                if not maybe_continue(msg="Would you like to try again?"):
                    error("User aborted after rosdep keys were not resolved.")
                    sys.exit(code.GENERATOR_NO_ROSDEP_KEY_FOR_DISTRO)
            except (KeyboardInterrupt, EOFError):
                error("\nUser quit.", exit=True)
            update_rosdep()
            invalidate_view_cache()

        info("All keys are " + ansi('greenf') + "OK" + ansi('reset') + "\n")

        for package in self.packages.values():
            if not package.licenses or not package.licenses[0]:
                error("No license set for package '{0}', aborting.".format(package.name), exit=True)

    def pre_branch(self, destination, source):
        if destination in self.rpm_branches:
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
        # Handle differently if this is an rpm vs distro branch
        if destination in self.rpm_branches:
            info("Placing RPM template files into '{0}' branch."
                 .format(destination))
            # Then this is an rpm branch
            # Place the raw template files
            self.place_template_files(package.get_build_type())
        else:
            # This is a distro specific rpm branch
            # Determine the current package being generated
            distro = destination.split('/')[-2]
            # Create RPMs for each distro
            with inbranch(destination):
                data = self.generate_rpm(package, distro)
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
        if destination in self.rpm_branches:
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
            ansi('boldoff') + "' RPM for package"
            " '" + ansi('boldon') + package.name + ansi('boldoff') + "'" +
            " at version '" + ansi('boldon') + package.version +
            "-" + str(self.rpm_inc) + ansi('boldoff') + "'" +
            ansi('reset'),
            use_prefix=False
        )
        info(ansi(color) + "####\n" + ansi('reset'), use_prefix=False)

    def store_original_config(self, config, patches_branch):
        with inbranch(patches_branch):
            with open('rpm.store', 'w+') as f:
                f.write(json.dumps(config))
            execute_command('git add rpm.store')
            if has_changes():
                execute_command('git commit -m "Store original patch config"')

    def load_original_config(self, patches_branch):
        config_store = show(patches_branch, 'rpm.store')
        if config_store is None:
            return config_store
        return json.loads(config_store)

    def place_template_files(self, build_type, rpm_dir='rpm'):
        # Create/Clean the rpm folder
        if os.path.exists(rpm_dir):
            if self.interactive:
                warning("rpm directory exists: " + rpm_dir)
                warning("Do you wish to overwrite it?")
                if not maybe_continue('y'):
                    error("Answered no to continue, aborting.", exit=True)
            else:
                warning("Overwriting rpm directory: " + rpm_dir)
            execute_command('git rm -rf ' + rpm_dir)
            execute_command('git commit -m "Clearing previous rpm folder"')
            if os.path.exists(rpm_dir):
                shutil.rmtree(rpm_dir)
        # Use generic place template files command
        place_template_files('.', build_type, gbp=True)
        # Commit results
        execute_command('git add ' + rpm_dir)
        execute_command('git commit -m "Placing rpm template files"')

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

    def get_subs(self, package, rpm_distro, releaser_history=None):
        return generate_substitutions_from_package(
            package,
            self.os_name,
            rpm_distro,
            self.rosdistro,
            self.install_prefix,
            self.rpm_inc,
            [p.name for p in self.packages.values()],
            releaser_history=releaser_history,
            fallback_resolver=missing_dep_resolver
        )

    def generate_rpm(self, package, rpm_distro, rpm_dir='rpm'):
        info("Generating RPM for {0}...".format(rpm_distro))
        # Try to retrieve the releaser_history
        releaser_history = self.get_releaser_history()
        # Generate substitution values
        subs = self.get_subs(package, rpm_distro, releaser_history)
        # Use subs to create and store releaser history
        self.set_releaser_history(dict(subs['changelogs']))
        # Template files
        template_files = process_template_files('.', subs)
        # Remove any residual template files
        execute_command('git rm -rf ' + ' '.join(template_files))
        # Add changes to the rpm folder
        execute_command('git add ' + rpm_dir)
        # Commit changes
        execute_command('git commit -m "Generated RPM files for ' +
                        rpm_distro + '"')
        # Rename the template spec file
        execute_command('git mv ' + rpm_dir + '/template.spec ' + rpm_dir + '/' + subs['Package'] + '.spec')
        # Commit changes
        execute_command('git commit -m "Renamed RPM spec file for ' +
                        rpm_distro + '"')
        # Return the subs for other use
        return subs

    def generate_tag_name(self, data):
        tag_name = '{Package}-{Version}-{RPMInc}_{Distribution}'
        tag_name = 'rpm/' + tag_name.format(**data)
        return tag_name

    def generate_branching_arguments(self, package, branch):
        n = package.name
        # rpm branch
        rpm_branch = 'rpm/' + n
        # Branch first to the rpm branch
        args = [[rpm_branch, branch, False]]
        # Then for each RPM distro, branch from the base rpm branch
        args.extend([
            ['rpm/' + d + '/' + n, rpm_branch, False] for d in self.distros
        ])
        return args

    def summarize_package(self, package, distro, color='bluef'):
        info(ansi(color) + "\n####" + ansi('reset'), use_prefix=False)
        info(
            ansi(color) + "#### Generating '" + ansi('boldon') + distro +
            ansi('boldoff') + "' RPM for package"
            " '" + ansi('boldon') + package.name + ansi('boldoff') + "'" +
            " at version '" + ansi('boldon') + package.version +
            "-" + str(self.rpm_inc) + ansi('boldoff') + "'" +
            ansi('reset'),
            use_prefix=False
        )
        info(ansi(color) + "####" + ansi('reset'), use_prefix=False)
