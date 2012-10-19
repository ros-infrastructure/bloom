from __future__ import print_function

import sys

from bloom.generators.debian import DebianGenerator
from bloom.generators.debian import sanitize_package_name

from bloom.logging import error
from bloom.logging import info

from bloom.util import code

try:
    from rosdep2.catkin_support import get_ubuntu_targets
except ImportError:
    error("rosdep was not detected, please install it.")
    sys.exit(code.ROSDEP_NOT_FOUND)


class RosDebianGenerator(DebianGenerator):
    title = 'rosdebian'
    description = "Generates debians tailored for the given rosdistro"
    default_install_prefix = '/opt/ros/'

    def prepare_arguments(self, parser):
        # Add command line arguments for this generator
        add = parser.add_argument
        add('rosdistro', help="ROS distro to target (fuerte, groovy, etc...)")
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

    def get_stackage_name(self, stackage):
        name = 'ros-{0}-{1}'.format(self.rosdistro, str(stackage.name))
        return sanitize_package_name(name)

    def generate_tag_name(self, data):
        tag_name = '{Package}_{Version}-{DebianInc}_{Distribution}'
        tag_name = 'debian/' + tag_name.format(**data)
        return tag_name

    def generate_branching_arguments(self, stackage, branch):
        n, r, b, ds = stackage.name, self.rosdistro, branch, self.distros
        return [['debian/' + r + '/' + d + '/' + n, b, False] for d in ds]
