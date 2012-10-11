import os



def test_get_parser():
    from bloom.branch.branch_main import get_parser
    parser = get_parser()
    args = parser.parse_args(['release/ros-fuerte-foo'])
    assert args.prefix == 'release/ros-fuerte-foo'
    assert args.src == None
    assert args.patch == True
    args = parser.parse_args(
        ['--src', 'release/foo', '--no-patch',
         'release/ros-fuerte-foo']
    )
    assert args.prefix == 'release/ros-fuerte-foo'
    assert args.src == 'release/foo'
    assert args.patch == False
    args = parser.parse_args(
        ['-s', 'release/foo', '-n', 'release/ros-fuerte-foo']
    )
    assert args.prefix == 'release/ros-fuerte-foo'
    assert args.src == 'release/foo'
    assert args.patch == False
