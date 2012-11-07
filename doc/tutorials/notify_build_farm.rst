Notifying the buildfarm
=======================

First you should test the build.

Start by checking out from the tag of the build you are releasing::

    $ git checkout debian/ros-groovy-<package>_<version>-<debinc>_<distro>

Where:

 * <package> is your package name, like "rviz" or "interactive_markers".
 * <version> is the version you are releasing, like 1.9.2.
 * <debinc> is the debian build number, often 0.  It only increments to re-run a build.  If upstream source code has changed, the version number should increment instead and <debinc> should go back to 0.
 * <distro> is the OS distribution, like precise or quantal.

Then run the build with this command::

    $ git-buildpackage -uc -us --git-ignore-branch

If this succeeds, and you have pushed your changes and tags as previously instructed, you still need to update the file that the build farm uses to generate jobs which is currently located at `https://github.com/ros/rosdistro/blob/master/releases/groovy.yaml <https://github.com/ros/rosdistro/blob/master/releases/groovy.yaml>`_
