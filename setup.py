#!/usr/bin/env python

from setuptools import setup

setup(name='bloom',
      version='0.1.8',
      packages=[
         'bloom',
         'bloom.branch',
         'bloom.generators',
         'bloom.generators.debian',
         'bloom.patch',
         'bloom.release'
      ],
      package_dir={'': 'src'},
      scripts=[
         'bin/git-bloom-branch',
         'bin/git-bloom-config',
         'bin/git-bloom-generate-debian',
         'bin/git-bloom-generate-debian-all',
         'bin/git-bloom-import-upstream',
         'bin/git-bloom-packageme',
         'bin/git-bloom-patch',
         'bin/git-bloom-release',
         'bin/git-bloom-set-upstream',
      ],
      package_data={'bloom': ['resources/em/*.em']},
      install_requires=['empy', 'pyyaml', 'argparse', 'rosdep', 'rospkg',
                        'vcstools', 'catkin_pkg'],
      author='Tully Foote, William Woodall',
      author_email='tfoote@willowgarage.com, wwoodall@willowgarage.com',
      maintainer='William Woodall',
      maintainer_email='wwoodall@gmail.com',
      url='http://www.ros.org/wiki/bloom',
      download_url='http://pr.willowgarage.com/downloads/bloom/',
      keywords=['ROS'],
      classifiers=['Programming Language :: Python',
                   'License :: OSI Approved :: BSD License'],
      description='A tool for facilitating git-buildpackage releases',
      long_description='''\
A package to facilitate releasing into gitbuildpackage repositories.\
''',
      license='BSD'
      )
