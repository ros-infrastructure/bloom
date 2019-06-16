import os

from ....utils.common import AssertRaisesContext
from ....utils.common import redirected_stdio

from bloom.generators.debian.generator import PackageManagerGenerator

from catkin_pkg.packages import find_packages

GENERATE_DATA_PATH = 'test_generator_data'
test_data_dir = os.path.join(os.path.dirname(__file__), GENERATE_DATA_PATH)


def get_package(pkg_name):
    packages = dict([(pkg.name, pkg) for path, pkg in find_packages(test_data_dir).items()])
    return packages[pkg_name]


def get_generator():
    gen = PackageManagerGenerator()
    gen.package_manager = 'debian'
    return gen


def test_set_default_distros():
    gen = get_generator()

    gen.rosdistro = 'dashing'
    gen.os_name = 'ubuntu'
    gen.set_default_distros()
    assert gen.distros == ['bionic']

    gen.distros = None
    gen.os_name = "debian"
    gen.os_not_required = True
    with AssertRaisesContext(SystemExit, ""):
        with redirected_stdio():
            gen.set_default_distros()
    gen.os_not_required = False
    with AssertRaisesContext(SystemExit, "No platforms defined"):
        with redirected_stdio():
            gen.set_default_distros()
