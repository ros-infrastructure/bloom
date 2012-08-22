import os
import shutil


def test_create_temporary_directory():
    from bloom.util import create_temporary_directory

    tmp_dir = create_temporary_directory()
    assert os.path.exists(tmp_dir)
    shutil.rmtree(tmp_dir)

    if os.path.exists('/tmp'):
        os.mkdir('/tmp/test-bloom-util')
        tmp_dir = create_temporary_directory('/tmp/test-bloom-util')
        assert os.path.exists(tmp_dir)
        shutil.rmtree('/tmp/test-bloom-util')


def test_ANSI_colors():
    from bloom.util import ansi, enable_ANSI_colors, disable_ANSI_colors

    control_str = '\033[1m\033[3m\033[31mBold and Italic and Red \033[0mPlain'
    control_str_disable = 'Bold and Italic and Red Plain'

    test_str = ansi('boldon') + ansi('italicson') + ansi('redf') \
             + 'Bold and Italic and Red ' + ansi('reset') + 'Plain'
    assert control_str == test_str, \
           '{0} == {1}'.format(control_str, test_str)

    disable_ANSI_colors()
    test_str = ansi('boldon') + ansi('italicson') + ansi('redf') \
             + 'Bold and Italic and Red ' + ansi('reset') + 'Plain'
    assert control_str_disable == test_str, \
           '{0} == {1}'.format(control_str_disable, test_str)

    enable_ANSI_colors()
    test_str = ansi('boldon') + ansi('italicson') + ansi('redf') \
             + 'Bold and Italic and Red ' + ansi('reset') + 'Plain'
    assert control_str == test_str, \
           '{0} == {1}'.format(control_str, test_str)
