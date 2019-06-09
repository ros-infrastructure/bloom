from __future__ import print_function

from bloom.generators.release import ReleaseGenerator

from bloom.git import inbranch

from bloom.logging import warning

from bloom.packages import get_package_data

from bloom.util import execute_command
from bloom.util import get_distro_list_prompt


class RosReleaseGenerator(ReleaseGenerator):
    title = 'rosrelease'
    description = """\
Generates a release branch for each of the packages in the source branch.
The common use case for this generator is to produce a
release/<ros_distro>/<package> branch for each package in the upstream
repository, so the source branch should be set to 'upstream' and the
prefix set to 'release'.
"""

    def prepare_arguments(self, parser):
        # Add command line arguments for this generator
        add = parser.add_argument
        add('rosdistro', help="ROS distro to target (%s, etc.)" % get_distro_list_prompt())
        return ReleaseGenerator.prepare_arguments(self, parser)

    def handle_arguments(self, args):
        self.rosdistro = args.rosdistro
        return ReleaseGenerator.handle_arguments(self, args)

    def get_branching_arguments(self):
        p, d, s, i = self.prefix, self.rosdistro, self.src, self.interactive
        self.branch_args = [
            ['/'.join([p, d, b]), s, i] for b in self.branch_list
        ]
        return self.branch_args

    def pre_rebase(self, destination):
        name = destination.split('/')[-1]
        return ReleaseGenerator.pre_rebase(
            self, destination,
            "Releasing package '{0}' for '{1}' to: '{2}'".format(
                name, self.rosdistro, destination
            )
        )
