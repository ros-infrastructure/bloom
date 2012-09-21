from __future__ import print_function

import os
import sys

from .. util import execute_command
# from .. util import maybe_continue
# from .. logging import ansi
from .. logging import error
from .. logging import info
from .. logging import log_prefix
# from .. logging import info
# from .. logging import warning
# from .. git import create_branch
# from .. git import get_branches
# from .. git import get_commit_hash
# from .. git import get_current_branch
# from .. git import track_branches

# from .. patch.common import set_patches_info
# from .. patch.common import get_patches_info
# from .. patch.rebase_cmd import rebase_patches

from . branch import execute_branch

try:
    from catkin_pkg.packages import find_packages
    from catkin_pkg.packages import verify_equal_package_versions
except ImportError:
    error("catkin_pkg was not detected, please install it.",
          file=sys.stderr)
    sys.exit(1)


@log_prefix('[git-bloom-branch]: ')
def branch_packages(src, prefix, patch, interactive, directory=None):
    # Get packages
    repo_dir = directory if directory else os.getcwd()
    packages = find_packages(repo_dir)
    if packages == []:
        error("No packages found in " + repo_dir)
        return 1
    # Verify that the packages all have the same version
    version = verify_equal_package_versions(packages.values())
    # Call git-bloom-branch on each package
    info(
      "Branching these packages: " + str([p.name for p in packages.values()])
    )
    for path in packages:
        package = packages[path]
        branch = prefix + ('' if prefix and prefix.endswith('/') else '/') \
               + package.name
        info("Branching " + package.name + "_" + version + " to " + branch)
        try:
            execute_branch(src, branch, patch, interactive, path,
                           directory=directory)
        finally:
            execute_command('git checkout ' + src, cwd=directory)
