Releasing a non-caktin project
==============================

When importing a non-catkin project, which is to say a project which does not have catkin package.xml files in the source tree, from upstream you will need to call the ``git bloom-import-upstream`` with custom arguments.  Additionally, the upstream projects often have not been prepared according to the :ref:`catkin conventions <prepare_your_upstream_repository>`. This is fine, but might require additional information to be passed to ``git bloom-import-upstream``, as it cannot make educated guesses about your upstream repository layout.

To import any non-catkin project you must specify the upstream version manually using the ``--upstream-version`` argument and the upstream tag to export from using the ``--upstream-tag`` argument. For example::

    git-bloom-import-upstream --upstream-version 1.1.1 --upstream-tag foo-1.1.1

If you are using svn in a non standard layout, you can specify the exact url to use like this:

    git bloom-import-upstream --upstream-version 1.1.1 --explicit-svn-url https://svn.foo.com/svn/foo/some/weird/path/foo-1.1.1

Once you have imported the upstream, you will need to manually run the two standard generators, starting with the release generator::

    git-bloom-generate release --src upstream --package-name foo

Once the release generator is done it will have created the branch ``release/foo``. Since the rosdebian generator heavily depends on a catkin package.xml file you will need to add that as a patch, so checkout to the release branch::

    git checkout release/foo

Now you will want to create a catkin package.xml file in the root of this branch and fill it out with information that is used during the platform generation step. You can use this example template as a starting place, but in the future there should be a catkin command to help generate this::

    <?xml version="1.0"?>
    <package>
      <name>@name</name>
      <version@version_abi>@version</version>
      <description>@description</description>

      <!-- multiple maintainer tags allowed, one name per tag-->
      <!-- <maintainer email="jane.doe@@example.com">Jane Doe</maintainer> -->
      <!-- Commonly used license strings:
      BSD, MIT, Boost Software License, GPLv2, GPLv3, LGPLv2.1, LGPLv3-->
      <!-- <license>LICENSE HERE</license> -->
      <!-- url type could be one of website (default), bugtracker and repository -->
      <!-- <url type="website">http://wiki.ros.org/@name</url> -->
      <!-- multiple authors tags allowed, one name per tag-->
      <!-- <author email="jane.doe@@example.com">Jane Doe</author> -->
      <!--Any system dependency or dependency to catkin packages. Examples:-->
      <!--<build_depend>genmsg</build_depend> for libraries for compiling-->
      <!--<buildtool_depend>cmake</buildtool_depend> for build tools-->
      <!--<run_depend>python-yaml</run_depend> for packages used at runtime-->
      <!--<test_depend>gtest</test_depend> for packages needed for testing-->
      <export>
        <!-- This section contains any information that other tools require-->
        <!-- <architecture_independent/> -->
        <!-- <meta_package/> -->
      </export>
    </package>

Which will create a template package.xml in the current directory for a package foo at version 1.1.1. Once you have completed your package.xml file, commit it to this branch::

    git add package.xml
    git commit -m "Added a package.xml file"

Next, you need to tag this release for the build farm (this is automatic when you have an upstream catkin project)::

    git tag release/foo/1.1.1

Now you are ready to generate the debians::

    git-bloom-generate rosdebian --prefix release groovy

If this is successful you won't get a nice little message like git bloom-release gives you, but as long as the return code was 0 you can push just like you would with catkin branches::

    $ git push --all && git push --tags

Now, if you want your packages built and released by the build farm see: :doc:`notify_build_farm`
