Release
-------

Catkin uses a git backend (essentially defined workflows built on
git-buildpackage) to manage releases and packaging of projects, called ``bloom``.
Packaging, in the current context refers to the eventual creation of
binary debians.

There are a few use cases of packaging that it should handle with varying amounts manual labor.


#. 3rdparty releases
#. native Catkin releases
#. Existing debian packages

For 1 and 2, the packages that will be created by bloom and the build
farm will be installed to a :term:`FHS` that is determined by the
``CMAKE_INSTALL_PREFIX`` variable.  For ROS, this is
``/opt/ros/DISTRO`` where ``DISTRO`` is a ros distribution.  This is
the assumed case if you are making releases with bloom.  However,
there should be no reason that debians can not be manufactured that
install to ``/``.

For 3, these packages are ingested using a dput of either source or
binary debians and the build system will not change the package in any
way. This form of release is highly discouraged except for libraries
that are very stable.

.. toctree::
   :maxdepth: 1

   bloom-release
   thirdparty


Installation
============

The recommended way to install bloom is using apt with the ROS repository [TODO LINK]

    sudo apt-get install python-bloom

For other platforms, or are not using the ROS repositories bloom is available through pypi.python.org

    sudo pip install -U bloom

Note that pip will not notify you of new updates.  