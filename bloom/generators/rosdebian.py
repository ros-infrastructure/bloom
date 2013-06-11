from __future__ import print_function

import traceback

from bloom.generators.debian import DebianGenerator
from bloom.generators.debian.generator import generate_substitutions_from_package
from bloom.generators.debian.generate_cmd import main as debian_main

from bloom.logging import debug
from bloom.logging import error
from bloom.logging import info

try:
    from rosdep2.catkin_support import get_ubuntu_targets
except ImportError:
    debug(traceback.format_exc())
    error("rosdep was not detected, please install it.", exit=True)


class RosDebianGenerator(DebianGenerator):
    title = 'rosdebian'
    description = "Generates debians tailored for the given rosdistro"
    default_install_prefix = '/opt/ros/'

    def prepare_arguments(self, parser):
        # Add command line arguments for this generator
        add = parser.add_argument
        add('rosdistro', help="ROS distro to target (groovy, hydro, etc...)")
        return DebianGenerator.prepare_arguments(self, parser)

    def handle_arguments(self, args):
        self.rosdistro = args.rosdistro
        self.default_install_prefix += self.rosdistro
        ret = DebianGenerator.handle_arguments(self, args)
        if args.distros in [None, []]:
            args.distros = get_ubuntu_targets(self.rosdistro)
        return ret

    def summarize(self):
        ret = DebianGenerator.summarize(self)
        info("Releasing for rosdistro: " + self.rosdistro)
        return ret

    def get_subs(self, package, debian_distro):
        subs = generate_substitutions_from_package(
            package,
            self.os_name,
            debian_distro,
            self.rosdistro,
            self.install_prefix,
            self.debian_inc,
            [p.name for p in self.packages.values()]
        )
        subs['Package'] = rosify_package_name(subs['Package'], self.rosdistro)
        return subs

    def generate_branching_arguments(self, package, branch):
        deb_branch = 'debian/' + self.rosdistro + '/' + package.name
        args = [[deb_branch, branch, False]]
        n, r, b, ds = package.name, self.rosdistro, deb_branch, self.distros
        args.extend([
            ['debian/' + r + '/' + d + '/' + n, b, False] for d in ds
        ])
        return args

    def get_release_tag(self, data):
        return 'release/{0}/{1}/{2}-{3}'\
            .format(self.rosdistro, data['Name'], data['Version'], self.debian_inc)


def prepare_arguments(parser):
    add = parser.add_argument
    add('package_path', nargs='?', help="path to or containing the package.xml of a package")
    action = parser.add_mutually_exclusive_group(required=False)
    add = action.add_argument
    add('--place-template-files', action='store_true', help="places debian/* template files only")
    add('--process-template-files', action='store_true', help="processes templates in debian/* only")
    return parser


def rosify_package_name(name, rosdistro):
    return 'ros-{0}-{1}'.format(rosdistro, name)


def get_subs(pkg, os_name, os_version, ros_distro):
    subs = generate_substitutions_from_package(
        pkg,
        os_name,
        os_version,
        ros_distro
    )
    subs['Package'] = rosify_package_name(subs['Package'])
    return subs


def main(args=None):
    debian_main(args, get_subs)


# This describes this command to the loader
description = dict(
    title='rosdebian',
    description="Generates ROS style debian packaging files for a catkin package",
    main=main,
    prepare_arguments=prepare_arguments
)
