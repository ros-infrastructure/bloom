import os

from ..utils.common import AssertRaisesContext
from ..utils.common import redirected_stdio

from bloom.config import validate_track_versions

test_data_dir = os.path.join(os.path.dirname(__file__), 'test_packages_data')


def test_validate_track_versions():
    tracks_dict = {
        'tracks': {
            'foo': {
                'version': 'v1.2.7-rc1'
            }
        }
    }
    with AssertRaisesContext(ValueError, "it must be formatted as 'MAJOR.MINOR.PATCH'"):
        with redirected_stdio():
            validate_track_versions(tracks_dict)
    tracks_dict['tracks']['foo']['version'] = '1.2.7'
    validate_track_versions(tracks_dict)
