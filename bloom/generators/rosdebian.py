from __future__ import print_function

from bloom.generators.debian import DebianGenerator


class RosDebianGenerator(DebianGenerator):
    title = 'rosdebian'
    description = "Generates debians tailored for the given rosdistro"

    def prepare_arguments(self, parser):
        # Add command line arguments for this generator
        add = parser.add_argument
        add('rosdistro', help="ROS distro to target (fuerte, groovy, etc...)")
        DebianGenerator.prepare_arguments(self, parser)
