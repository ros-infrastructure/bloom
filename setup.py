#!/usr/bin/env python

from distutils.core import setup


setup(name='bloom',
      version='0.0.1',
      packages=['bloom'],
      package_dir = {'':'src'},
      #scripts = ['scripts/rosversion'], TODO Update!!!
      author = "Ken Conley", 
      author_email = "kwc@willowgarage.com",
      url = "http://www.ros.org/wiki/bloom",
      download_url = "http://pr.willowgarage.com/downloads/bloom/", 
      keywords = ["ROS"],
      classifiers = [
        "Programming Language :: Python", 
        "License :: OSI Approved :: BSD License" ],
      description = "A tool for facilitating gitbuildpackage releases", 
      long_description = """\
A package to facilitate releasing into gitbuildpackage repositories.  
""",
      license = "BSD"
      )
