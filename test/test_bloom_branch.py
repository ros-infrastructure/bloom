import os

from export_bloom_from_src import get_path_and_pythonpath
# Setup environment for running commands
path, ppath = get_path_and_pythonpath()
os.putenv('PATH', path)
os.putenv('PYTHONPATH', ppath)


def test_get_parser():
    from bloom.branch import get_parser
    parser = get_parser()
    args = parser.parse_args(['release/ros-fuerte-foo'])
    assert args.dst == 'release/ros-fuerte-foo'
    assert args.src == None
    assert args.patch == True
    args = parser.parse_args(
        ['--src', 'release/foo', '--no-patch',
         'release/ros-fuerte-foo']
    )
    assert args.dst == 'release/ros-fuerte-foo'
    assert args.src == 'release/foo'
    assert args.patch == False
    args = parser.parse_args(
        ['-s', 'release/foo', '-n', 'release/ros-fuerte-foo']
    )
    assert args.dst == 'release/ros-fuerte-foo'
    assert args.src == 'release/foo'
    assert args.patch == False
