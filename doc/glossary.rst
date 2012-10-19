Glossary
--------

.. glossary::

    bloom.conf
        A file that lives on a special orphan branch `bloom` in a :term:`release repository` which contains bloom meta-information (like upstream repository location and type) and is used when making releases with bloom.

    wet
        A catkin-ized package.

    dry
        A non-catkin, rosbuild based software :term:`package` or stack.

    FHS
        The Linux `Filesystem Hierarchy Standard <http://en.wikipedia.org/wiki/Filesystem_Hierarchy_Standard>`_

    release repository
        A git repository that bloom operates on, which is loosely based on :term:`git-buildpackage`. This repository contains snapshots of released upstream source trees, any patches needed to release the upstream project, and git tags which point to source trees setup for building platform specific packages (like debian source debs).

    git-buildpackage
        Suite to help with Debian packages in Git repositories.

    package
        A single software unit. In catkin a package is any folder containing a valid package.xml file. An upstream repository can have many packages, but a package must be completely contained in one repository.

    stack
        A term used by the ROS Fuerte version of catkin and the legacy rosbuild system. In the context of these systems, a stack is a software release unit with consists of zero to many ROS packages, which are the software build units, i.e. you release stacks, you build ROS packages.

    project
        CMake's notion of a buildable subdirectory: it contains a ``CMakeLists.txt`` that calls CMake's ``project()`` macro.


