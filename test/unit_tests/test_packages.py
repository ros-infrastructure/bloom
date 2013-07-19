import os

from ..utils.common import AssertRaisesContext
from ..utils.common import redirected_stdio

from bloom.packages import get_package_data

test_data_dir = os.path.join(os.path.dirname(__file__), 'test_packages_data')


def test_get_package_data_fails_on_uppercase():
    with AssertRaisesContext(SystemExit, "Invalid package names, aborting."):
        with redirected_stdio():
            get_package_data(directory=test_data_dir)
