import os

from collections import namedtuple
from distutils.dir_util import copy_tree

from ....utils.common import AssertRaisesContext
from ....utils.common import bloom_answer
from ....utils.common import change_directory
from ....utils.common import redirected_stdio
from ....utils.common import temporary_directory
from ....utils.common import user

from bloom.generators.common import PackageManagerGenerator

from bloom.util import code

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


def listdir(dirname):
    # list files in one direcotory, including its subdirectory's file
    files = []
    for f in os.listdir(dirname):
        if os.path.isfile(os.path.join(dirname, f)):
            files.append(os.path.join(dirname, f))
        else:
            for sub_f in os.listdir(os.path.join(dirname, f)):
                files.append(os.path.join(dirname, f, sub_f))
    return files


def test_place_template_files():
    pkg_name = 'test_pkg'
    pkg = get_package(pkg_name)
    gen = get_generator()
    gen.interactive = False
    build_type = pkg.get_build_type()

    # Test normal place template files
    with redirected_stdio():
        with temporary_directory():
            user('git init .')
            gen.place_template_files(build_type)
            placed_files = listdir('debian')
            template_file_list = [
                'debian/source/format.em',
                'debian/source/options.em',
                'debian/changelog.em',
                'debian/compat.em',
                'debian/control.em',
                'debian/copyright.em',
                'debian/gbp.conf.em',
                'debian/rules.em',
            ]
            for f in template_file_list:
                assert f in placed_files, "{0} not placed".format(f)

    # Test if package system directory exists
    test_dir_exist_func_list = [
        dir_exist_with_interactive,
        dir_exist_with_clean,
        dir_exist_default,
    ]
    TestPlaceTemplateFileStruct = namedtuple(
        'TestPlaceTemplateFileStruct',
        'generator build_type old_dir, directory,'
        'original_template_files_dict,'
        'original_normal_files'
    )
    dir_target = os.path.join(os.path.dirname(__file__), GENERATE_DATA_PATH, pkg_name)
    with change_directory(dir_target):
        old_dir = os.getcwd()
        original_files = listdir('debian')
        original_template_files_dict = dict([(f, open(f).read())
                                             for f in original_files if f.endswith('.em')])
        original_normal_files = [f for f in original_files if not f.endswith('.em')]
        for f in test_dir_exist_func_list:
            with temporary_directory() as directory:
                user('git init .')
                copy_tree(old_dir, directory)
                user('git add .')
                user('git commit --allow-empty -m "Initial commit"')
                data = TestPlaceTemplateFileStruct(gen, build_type, old_dir,directory,
                                                   original_template_files_dict,
                                                   original_normal_files)
                f(data)


def dir_exist_with_interactive(data):
    gen = data.generator
    gen.interactive = True

    with AssertRaisesContext(SystemExit, "Answered no to continue"):
        with redirected_stdio():
            with bloom_answer(['n']):
                gen.place_template_files(data.build_type)

    with redirected_stdio():
        with bloom_answer(['y']):
            gen.place_template_files(data.build_type)
            placed_files_dict = dict([(f, open(f).read()) for f in listdir('debian')])
            # overwrite the template files should not remove the origianl debian files
            for f in data.original_normal_files:
                assert f in placed_files_dict.keys()
            for f, content in data.original_template_files_dict.items():
                assert f in placed_files_dict.keys()
                # Your gbp.conf.em will be changed if you answer yes to overwrite
                if f == 'gbp.conf.em':
                    assert content != placed_files_dict[f]

    gen.interactive = False


def dir_exist_with_clean(data):
    gen = data.generator
    CLEAR_TEMPLATE_ENV_PARAMETER = 'BLOOM_CLEAR_TEMPLATE_ON_GENERATION'
    os.environ.setdefault(CLEAR_TEMPLATE_ENV_PARAMETER, "1")

    with redirected_stdio():
        gen.place_template_files(data.build_type)
        placed_files = listdir('debian')
        for f in data.original_normal_files:
            assert f not in placed_files

    os.environ.pop(CLEAR_TEMPLATE_ENV_PARAMETER)


def dir_exist_default(data):
    gen = data.generator
    with redirected_stdio():
        gen.place_template_files(data.build_type)
        placed_files_dict = dict([(f, open(f).read()) for f in listdir('debian')])
        # default doesn't influence your file under debian directory
        for f, content in data.original_template_files_dict.items():
            assert f in placed_files_dict.keys()
            assert content == placed_files_dict[f]
        for f in data.original_normal_files:
            assert f in placed_files_dict.keys()


def test_bad_dependency():
    bad_pkg_name = 'bad_dependency_pkg'
    bad_pkg = get_package(bad_pkg_name)
    pkg_bad_dict = {bad_pkg_name: bad_pkg}

    gen = get_generator()
    gen.packages = pkg_bad_dict
    gen.rosdistro = 'kinetic'
    gen.os_name = 'ubuntu'
    gen.distros = ['xenial']
    with bloom_answer(['n']):
        with AssertRaisesContext(SystemExit, str(code.GENERATOR_NO_ROSDEP_KEY_FOR_DISTRO)):
            with redirected_stdio():
                gen.check_all_keys_are_valid("")


def format_depends(depends, resolved_deps):
    formatted = []
    for d in depends:
        formatted.append("{0}".format(d))
    return formatted


def format_description(value):
    return value


class OneGenerator(PackageManagerGenerator):
    package_manager = "test"
    @staticmethod
    def get_subs_hook(subs, package, rosdistro, releaser_history=None):
        subs['Name'] = 'test_pkg improved'
        subs['specific_part'] = 'none'
        return subs


def test_get_substitute():
    pkg_name = 'test_pkg'
    pkg = get_package(pkg_name)
    pkg_dict = {pkg_name: pkg}

    gen = OneGenerator()
    gen.packages = pkg_dict
    gen.os_name = "ubuntu"
    gen.os_version = "xenial"
    gen.rosdistro = "kinetic"
    gen.install_prefix = gen.default_install_prefix
    gen.inc = "1"

    with redirected_stdio():
        subs = gen.get_subs(pkg, gen.os_version, format_description, format_depends)

    assert 'test_pkg improved' == subs['Name']
    assert '0.1.0' == subs['Version']
    assert 'The test_pkg package' == subs['Description']
    assert '1' == subs['Inc']
    assert 'test-pkg' == subs['Package']
    assert ['roscpp', 'rospy'] == subs['Depends']
    assert gen.os_version == subs['Distribution']
    assert "nobody1 <nobody1@todo.todo>" == subs['Maintainer']
    assert "nobody1 <nobody1@todo.todo>, nobody2 <nobody2@todo.todo>" == subs['Maintainers']
    assert 'none' == subs['specific_part']
