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

import datetime
import json
import os
import pkg_resources
import re
import shutil
import sys
import traceback

from dateutil import tz

from bloom.generators import BloomGenerator
from bloom.generators import resolve_dependencies
from bloom.generators import update_rosdep

from bloom.generators.common import default_fallback_resolver

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
enable_drop_first_log_prefix(True)
from bloom.logging import error
from bloom.logging import fmt
from bloom.logging import info
from bloom.logging import is_debug
from bloom.logging import warning

from bloom.commands.git.patch.common import get_patch_config
from bloom.commands.git.patch.common import set_patch_config

from bloom.packages import get_package_data

from bloom.util import execute_command
from bloom.util import get_rfc_2822_date
from bloom.util import maybe_continue

try:
    from catkin_pkg.changelog import get_changelog_from_path
    from catkin_pkg.changelog import CHANGELOG_FILENAME
except ImportError as err:
    debug(traceback.format_exc())
    error("rosdep was not detected, please install it.", exit=True)

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

TEMPLATE_EXTENSION = '.em'


def __place_template_folder(group, src, dst, gbp=False):
    template_files = pkg_resources.resource_listdir(group, src)
    # For each tempalte, place
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
                debug("Placing temaplte '{0}'".format(template_path))
                template = pkg_resources.resource_string(group, template_path)
            except IOError as err:
                error("Failed to load template "
                      "'{0}': {1}".format(template_file, str(err)), exit=True)
            if not os.path.exists(dst):
                os.makedirs(dst)
            if os.path.exists(template_dst):
                debug("Removing existing file '{0}'".format(template_dst))
                os.remove(template_dst)
            with open(template_dst, 'w') as f:
                f.write(template)


def place_template_files(path, gbp=False):
    info(fmt("@!@{bf}==>@| Placing templates files in the 'debian' folder."))
    debian_path = os.path.join(path, 'debian')
    # Create/Clean the debian folder
    if not os.path.exists(debian_path):
        os.makedirs(debian_path)
    # Place template files
    group = 'bloom.generators.debian'
    __place_template_folder(group, 'templates', debian_path, gbp)


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
        'version_lt': '<<',
        'version_lte': '<=',
        'version_eq': '=',
        'version_gte': '>=',
        'version_gt': '>>'
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
                    formatted.append("{0} ({1} {2})".format(
                        resolved_dep, versions[v], getattr(d, v)))
    return formatted


def get_changelogs(package, releaser_history=None):
    if releaser_history is None:
        warning("No historical releaser history, using current maintainer name "
                "and email for each versioned changelog entry.")
        releaser_history = {}
    if is_debug():
        import logging
        logging.basicConfig()
        import catkin_pkg
        catkin_pkg.changelog.log.setLevel(logging.DEBUG)
    package_path = os.path.abspath(os.path.dirname(package.filename))
    changelog_path = os.path.join(package_path, CHANGELOG_FILENAME)
    if os.path.exists(changelog_path):
        changelog = get_changelog_from_path(changelog_path)
        changelogs = []
        maintainer = (package.maintainers[0].name, package.maintainers[0].email)
        for version, date, changes in changelog.foreach_version(reverse=True):
            changes_str = []
            date_str = get_rfc_2822_date(date)
            for item in changes:
                changes_str.extend(['  ' + i for i in str(item).splitlines()])
            # Each entry has (version, date, changes, releaser, releaser_email)
            releaser, email = releaser_history.get(version, maintainer)
            changelogs.append((
                version, date_str, '\n'.join(changes_str), releaser, email
            ))
        return changelogs
    else:
        warning("No {0} found for package '{1}'"
                .format(CHANGELOG_FILENAME, package.name))
        return []


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
    deb_inc=0,
    peer_packages=None,
    releaser_history=None,
    fallback_resolver=None
):
    peer_packages = peer_packages or []
    data = {}
    # Name, Version, Description
    data['Name'] = package.name
    data['Version'] = package.version
    data['Description'] = debianize_string(package.description)
    # Websites
    websites = [str(url) for url in package.urls if url.type == 'website']
    homepage = websites[0] if websites else ''
    if homepage == '':
        warning("No homepage set, defaulting to ''")
    data['Homepage'] = homepage
    # Debian Increment Number
    data['DebianInc'] = deb_inc
    # Package name
    data['Package'] = sanitize_package_name(package.name)
    # Installation prefix
    data['InstallationPrefix'] = installation_prefix
    # Resolve dependencies
    depends = package.run_depends
    build_depends = package.build_depends + package.buildtool_depends
    unresolved_keys = depends + build_depends
    resolved_deps = resolve_dependencies(unresolved_keys, os_name,
                                         os_version, ros_distro,
                                         peer_packages, fallback_resolver)
    data['Depends'] = sorted(
        set(format_depends(depends, resolved_deps))
    )
    data['BuildDepends'] = sorted(
        set(format_depends(build_depends, resolved_deps))
    )
    # Set the distribution
    data['Distribution'] = os_version
    # Use the time stamp to set the date strings
    stamp = datetime.datetime.now(tz.tzlocal())
    data['Date'] = stamp.strftime('%a, %d %b %Y %T %z')
    data['YYYY'] = stamp.strftime('%Y')
    # Maintainers
    maintainers = []
    for m in package.maintainers:
        maintainers.append(str(m))
    data['Maintainer'] = maintainers[0]
    data['Maintainers'] = ', '.join(maintainers)
    # Changelog
    changelogs = get_changelogs(package, releaser_history)
    if not changelogs:
        # Ensure at least a minimal changelog
        changelogs = [(
            package.version,
            get_rfc_2822_date(datetime.datetime.now()),
            '  * Autogenerated, no CHANGELOG.rst found during generation.',
            package.maintainers[0].name,
            package.maintainers[0].email
        )]
    data['changelogs'] = changelogs
    # Summarize dependencies
    summarize_dependency_mapping(data, depends, build_depends, resolved_deps)
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
        with open(template_path, 'w') as f:
            f.write(result)
        # Copy the permissions
        shutil.copymode(item, template_path)
        processed_items.append(item)
    return processed_items


def process_template_files(path, subs):
    info(fmt("@!@{bf}==>@| In place processing templates in 'debian' folder."))
    debian_dir = os.path.join(path, 'debian')
    if not os.path.exists(debian_dir):
        sys.exit("No debian directory found at '{0}', cannot process templates."
                 .format(debian_dir))
    return __process_template_folder(debian_dir, subs)


def match_branches_with_prefix(prefix, get_branches):
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
    return list(set(branches))


def get_package_from_branch(branch):
    with inbranch(branch):
        try:
            package_data = get_package_data(branch)
        except SystemExit:
            return None
        if type(package_data) not in [list, tuple]:
            # It is a ret code
            DebianGenerator.exit(package_data)
    names, version, packages = package_data
    if type(names) is list and len(names) > 1:
        DebianGenerator.exit(
            "Debian generator does not support generating "
            "from branches with multiple packages in them, use "
            "the release generator first to split packages into "
            "individual branches.")
    if type(packages) is dict:
        return packages.values()[0]


def debianize_string(value):
    markup_remover = re.compile(r'<.*?>')
    value = markup_remover.sub('', value)
    value = re.sub('\s+', ' ', value)
    value = value.strip()
    return value


def sanitize_package_name(name):
    return name.replace('_', '-')


class DebianGenerator(BloomGenerator):
    title = 'debian'
    description = "Generates debians from the catkin meta data"
    has_run_rosdep = False
    default_install_prefix = '/usr'
    rosdistro = os.environ.get('ROS_DISTRO', 'groovy')

    def prepare_arguments(self, parser):
        # Add command line arguments for this generator
        add = parser.add_argument
        add('-i', '--debian-inc', help="debian increment number", default='0')
        add('-p', '--prefix', required=True,
            help="branch prefix to match, and from which create debians"
                 " hint: if you want to match 'release/foo' use 'release'")
        add('--distros', nargs='+', required=False, default=[],
            help='A list of debian (ubuntu) distros to generate for')
        add('--install-prefix', default=None,
            help="overrides the default installation prefix (/usr)")
        add('--os-name', default='ubuntu',
            help="overrides os_name, set to 'ubuntu' by default")

    def handle_arguments(self, args):
        self.interactive = args.interactive
        self.debian_inc = args.debian_inc
        self.os_name = args.os_name
        self.distros = args.distros
        if self.distros in [None, []]:
            index = rosdistro.get_index(rosdistro.get_index_url())
            release_file = rosdistro.get_release_file(index, self.rosdistro)
            if self.os_name not in release_file.platforms:
                error("No platforms defined for os '{0}' in release file for the '{1}' distro."
                      .format(self.os_name, self.rosdistro), exit=True)
            self.distros = release_file.platforms[self.os_name]
        self.install_prefix = args.install_prefix
        if args.install_prefix is None:
            self.install_prefix = self.default_install_prefix
        self.prefix = args.prefix
        self.branches = match_branches_with_prefix(self.prefix, get_branches)
        if len(self.branches) == 0:
            error(
                "No packages found, check your --prefix or --src arguments.",
                exit=True
            )
        self.packages = {}
        self.tag_names = {}
        self.names = []
        self.branch_args = []
        self.debian_branches = []
        for branch in self.branches:
            package = get_package_from_branch(branch)
            if package is None:
                # This is an ignored package
                continue
            self.packages[package.name] = package
            self.names.append(package.name)
            args = self.generate_branching_arguments(package, branch)
            # First branch is debian/[<rosdistro>/]<package>
            self.debian_branches.append(args[0][0])
            self.branch_args.extend(args)

    def summarize(self):
        info("Generating source debs for the packages: " + str(self.names))
        info("Debian Incremental Version: " + str(self.debian_inc))
        info("Debian Distributions: " + str(self.distros))

    def get_branching_arguments(self):
        return self.branch_args

    def update_rosdep(self):
        update_rosdep()
        self.has_run_rosdep = True

    def pre_branch(self, destination, source):
        if destination in self.debian_branches:
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
        # Handle differently if this is a debian vs distro branch
        if destination in self.debian_branches:
            info("Placing debian template files into '{0}' branch."
                 .format(destination))
            # Then this is a debian branch
            # Place the raw template files
            self.place_template_files()
        else:
            # This is a distro specific debian branch
            # Determine the current package being generated
            distro = destination.split('/')[-2]
            # Create debians for each distro
            with inbranch(destination):
                data = self.generate_debian(package, distro)
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
        if destination in self.debian_branches:
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
            ansi('boldoff') + "' debian for package"
            " '" + ansi('boldon') + package.name + ansi('boldoff') + "'" +
            " at version '" + ansi('boldon') + package.version +
            "-" + str(self.debian_inc) + ansi('boldoff') + "'" +
            ansi('reset'),
            use_prefix=False
        )
        info(ansi(color) + "####\n" + ansi('reset'), use_prefix=False)

    def store_original_config(self, config, patches_branch):
        with inbranch(patches_branch):
            with open('debian.store', 'w+') as f:
                f.write(json.dumps(config))
            execute_command('git add debian.store')
            if has_changes():
                execute_command('git commit -m "Store original patch config"')

    def load_original_config(self, patches_branch):
        config_store = show(patches_branch, 'debian.store')
        if config_store is None:
            return config_store
        return json.loads(config_store)

    def place_template_files(self, debian_dir='debian'):
        # Create/Clean the debian folder
        if os.path.exists(debian_dir):
            if self.interactive:
                warning("Debian directory exists: " + debian_dir)
                warning("Do you wish to overwrite it?")
                if not maybe_continue('y'):
                    error("Answered no to continue, aborting.", exit=True)
            else:
                warning("Overwriting Debian directory: " + debian_dir)
            execute_command('git rm -rf ' + debian_dir)
            execute_command('git commit -m "Clearing previous debian folder"')
            if os.path.exists(debian_dir):
                shutil.rmtree(debian_dir)
        # Use generic place template files command
        place_template_files('.', gbp=True)
        # Commit results
        execute_command('git add ' + debian_dir)
        execute_command('git commit -m "Placing debian template files"')

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

    def get_subs(self, package, debian_distro, releaser_history=None):
        return generate_substitutions_from_package(
            package,
            self.os_name,
            debian_distro,
            self.rosdistro,
            self.install_prefix,
            self.debian_inc,
            [p.name for p in self.packages.values()],
            releaser_history=releaser_history,
            fallback_resolver=missing_dep_resolver
        )

    def generate_debian(self, package, debian_distro):
        info("Generating debian for {0}...".format(debian_distro))
        # Try to retrieve the releaser_history
        releaser_history = self.get_releaser_history()
        # Generate substitution values
        subs = self.get_subs(package, debian_distro, releaser_history)
        # Use subs to create and store releaser history
        releaser_history = [(v, (n, e)) for v, _, _, n, e in subs['changelogs']]
        self.set_releaser_history(dict(releaser_history))
        # Handle gbp.conf
        subs['release_tag'] = self.get_release_tag(subs)
        # Template files
        template_files = process_template_files('.', subs)
        # Remove any residual template files
        execute_command('git rm -rf ' + ' '.join(template_files))
        # Add changes to the debian folder
        execute_command('git add debian')
        # Commit changes
        execute_command('git commit -m "Generated debian files for ' +
                        debian_distro + '"')
        # Return the subs for other use
        return subs

    def get_release_tag(self, data):
        return 'release/{0}/{1}-{2}'.format(data['Name'], data['Version'],
                                            self.debian_inc)

    def generate_tag_name(self, data):
        tag_name = '{Package}_{Version}-{DebianInc}_{Distribution}'
        tag_name = 'debian/' + tag_name.format(**data)
        return tag_name

    def generate_branching_arguments(self, package, branch):
        n = package.name
        # Debian branch
        deb_branch = 'debian/' + n
        # Branch first to the debian branch
        args = [[deb_branch, branch, False]]
        # Then for each debian distro, branch from the base debian branch
        args.extend([
            ['debian/' + d + '/' + n, deb_branch, False] for d in self.distros
        ])
        return args

    def summarize_package(self, package, distro, color='bluef'):
        info(ansi(color) + "\n####" + ansi('reset'), use_prefix=False)
        info(
            ansi(color) + "#### Generating '" + ansi('boldon') + distro +
            ansi('boldoff') + "' debian for package"
            " '" + ansi('boldon') + package.name + ansi('boldoff') + "'" +
            " at version '" + ansi('boldon') + package.version +
            "-" + str(self.debian_inc) + ansi('boldoff') + "'" +
            ansi('reset'),
            use_prefix=False
        )
        info(ansi(color) + "####" + ansi('reset'), use_prefix=False)
