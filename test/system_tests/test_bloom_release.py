from ..utils.common import user

def test_bloom_release_dash_h():
    assert 0 == user('bloom-release -h'), "Exited with non-zero status."

