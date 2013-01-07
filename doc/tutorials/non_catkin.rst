Releasing a non-caktin project
==============================

When releasing a non-catkin project, which is to say a project which does not have a catkin package.xml in the upstream repository, using bloom you will need to call the ``git bloom-import-upstream`` with custom arguments.  Additionally, the upstream projects often have not been prepared according to the :ref:`catkin conventions <prepare_your_upstream_repository>`. This is fine, but might require additional information to be passed to ``git bloom-import-upstream``, as it cannot make educated guesses about your upstream repository layout.

To import any non-catkin project you must specify the upstream version manually using the ``--upstream-version`` argument and the upstream tag to export from using the ``--upstream-tag`` argument. For example::

    git-bloom-import-upstream --upstream-version 1.1.1 --upstream-tag foo-1.1.1

If you are using svn in a non standard layout, you can specify the exact url to use like this:

    git bloom-import-upstream --upstream-version 1.1.1 --explicit-svn-url https://svn.foo.com/svn/foo/some/weird/path/foo-1.1.1

Once you have imported the upstream, you will need to manually run the two standard generators, starting with the release generator::

    git-bloom-generate release --src upstream --package-name foo

You'll get this warning::

  Cannot automatically tag the release because this is not a catkin project.  Please checkout the release branch and then create a tag manually with:
  git checkout release/foo
  git tag -f release/foo/<version>

Do what the warning says.

Once the release generator is done it will have created the branch ``release/foo``. Since the rosdebian generator heavily depends on a catkin package.xml file you will need to add that as a patch, so checkout to the release branch::

    git checkout release/foo

Now you will want to create a catkin package.xml file in the root of this branch and fill it out with information that is used during the platform generation step.

You can use the ``catkin_create_pkg`` command to generate a package.xml::

    catkin_create_pkg foo -V 1.1.1

This will create a <package_name> folder with a CMakeLists.txt and a package.xml.  We only need the package.xml::

    mv foo/package.xml ./
    rm -rf foo

Now you should edit the package.xml and once you have completed your package.xml file, commit it to this branch::

    git add package.xml
    git commit -m "Added a package.xml file"

Next, you need to tag this release for the build farm (this is automatic when you have an upstream catkin project)::

    git tag release/foo/1.1.1

Now you are ready to generate the debians::

    git-bloom-generate rosdebian --prefix release groovy

If this is successful you won't get a nice little message like git bloom-release gives you, but as long as the return code was 0 you can push just like you would with catkin branches::

    $ git push --all && git push --tags

Now, if you want your packages built and released by the build farm see: :doc:`notify_build_farm`
