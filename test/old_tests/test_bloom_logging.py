def test_ANSI_colors():
    from bloom.logging import ansi, enable_ANSI_colors, disable_ANSI_colors
    
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
