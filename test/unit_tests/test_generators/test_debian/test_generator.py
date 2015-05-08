import os

from ....utils.common import redirected_stdio

from bloom.generators.debian.generator import em
from bloom.generators.debian.generator import get_changelogs
from bloom.generators.debian.generator import format_description

from catkin_pkg.packages import find_packages

test_data_dir = os.path.join(os.path.dirname(__file__), 'test_generator_data')


def test_get_changelogs():
    with redirected_stdio():
        packages = dict([(pkg.name, pkg) for path, pkg in find_packages(test_data_dir).items()])
        assert 'bad_changelog_pkg' in packages
        get_changelogs(packages['bad_changelog_pkg'])


def test_unicode_templating():
    with redirected_stdio():
        packages = dict([(pkg.name, pkg) for path, pkg in find_packages(test_data_dir).items()])
        assert 'bad_changelog_pkg' in packages
        chlogs = get_changelogs(packages['bad_changelog_pkg'])
        template = "@(changelog)"
        em.expand(template, {'changelog': chlogs[0][2]})


def test_format_description():
    assert '' == format_description('')
    assert '.' == format_description('.')
    assert 'Word.' == format_description('Word.')
    assert 'Word' == format_description('Word')
    assert '.' == format_description(' .')
    assert '.' == format_description(' . ')
    assert 'Word.\n Other words.' == format_description('Word. Other words.')
    assert 'The first sentence, or synopsis.\n The second sentence. Part of the long description, but all in a single paragraph.' == format_description('The first sentence, or synopsis. The second sentence. Part of the long description, but all in a single paragraph.')
    assert '..' == format_description('..')
    assert 'The my_package package' == format_description('The my_package package')
    assert 'First sentence with a version nr: 2.4.5, some other text.\n And then some other text.' == format_description('First sentence with a version nr: 2.4.5, some other text. And then some other text.')
    assert 'More punctuation! This will split here.\n And the rest.' == format_description('More punctuation! This will split here. And the rest.')
    assert 'v1.2.3 with v5.3.7 and ! Split after this.\n Long description here.' == format_description('v1.2.3 with v5.3.7 and ! Split after this. Long description here.\n\n')
    # no whitespace between <p>'s, no split
    assert 'some embedded html markup.the other sentence.' == format_description('<h1>some embedded</h1>\n<p>html markup.</p><p>the other sentence.</p>')
