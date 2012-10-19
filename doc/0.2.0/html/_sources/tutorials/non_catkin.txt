Releasing a non-caktin project
==============================

.. todo:: Update this to bloom 0.2.x

When import a non catkin project from upstream, you must specify the upstream version manually using the '--upstream-version' argument and the upstream tag to export from using the '--upstream-tag' argument. For example::

    $ git bloom-import-upstream --upstream-version 1.1.1 --upstream-tag foo-1.1.1

If you are using svn in a non standard layout, you can specify the exact url to use like this:

    $ git bloom-import-upstream --upstream-version 1.1.1 --explicit-svn-url https://svn.foo.com/svn/foo/some/weird/path/foo-1.1.1

Once you have imported the upstream, you will need to manually branch to the release stage::

    $ git bloom-branch --src upstream --package-name foo release

Note: this workflow will probably change in the next version of bloom to make it more streamlined and compatable with catkin projects.

The above command created a new branch called 'release/foo'. You should change to the branch::

    $ git checkout release/foo

And add a minimal catkin package.xml file. The generate debian phase requires a catkin package.xml file or legacy stack.xml file to produce debians. There is a convenience command::

    $ git bloom-packageme foo 1.1.1

Which will create a template package.xml in the current directory for a package foo at version 1.1.1. Once you have completed your package.xml file, commit it to this branch::

    $ git add package.xml
    $ git commit -m "Added a package.xml file"

Now you need to 'export' this patch so that it will persist through new upstream versions (though you likely have to edit it for each version)::

    $ git bloom-patch export

You should run that command any time you make a commit on one of the patch branches (release/foo is a patch branch).

Next, you need to tag this release for the build farm (this is automatic when you have an upstream catkin project)::

    $ git tag release/foo/1.1.1

Now you are ready to generate the debians::

    $ git bloom-generate-debian-all groovy release

If this is successful you won't get a nice little message like git bloom-release gives you, but as long as the return code was 0 you can push just like you would with catkin branches::

    $ git push --all && git push --tags

Now, if you want your packages built and released by the build farm see: :doc:`notify_build_farm`
