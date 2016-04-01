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

    def post_patch(self, destination):
        # Figure out the version of the given package
        if self.name is not None:
            warning("""\
Cannot automatically tag the release because this is not a catkin project.""")
            warning("""\
Please checkout the release branch and then create a tag manually with:""")
            warning("  git checkout " + destination)
            warning("  git tag -f " + destination + "/<version>")
            return
        with inbranch(destination):
            name, version, packages = get_package_data(destination)
        # Execute git tag
        execute_command('git tag -f ' + destination + '/' + version +
                        '-' + str(self.release_inc))

    def detect_branches(self):
        self.packages = None
        with inbranch(self.src):
            if self.name is not None:
                self.packages = [self.name]
                return [self.name]
            package_data = get_package_data(self.src)
            if type(package_data) not in [list, tuple]:
                return package_data
            name, version, packages = package_data
            self.packages = packages
            # Check meta packages for valid CMakeLists.txt
            if isinstance(self.packages, dict):
                for path, pkg in self.packages.items():
                    # Check for valid CMakeLists.txt if a metapackage
                    self.metapackage_check(path, pkg)
            return name if type(name) is list else [name]
