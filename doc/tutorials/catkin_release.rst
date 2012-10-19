Releasing a catkin project
==========================

Assuming you have either setup a new bloom release repository (:doc:`bloom_setup`) or you have cloned an existing release repository, you are now ready to begin releasing your catkin project.

Once in your release repository, ensure that you are on the 'master' branch::

    $ git checkout master

It is always best to run from the master branch when possible.

Importing the upstream repository
---------------------------------

Preparing your upstream repository
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Before importing your upstream repository into the release repository using bloom, the upstream repository needs to be prepared. For catkin projects, this means updating the version number in the `package.xml`(s) of your project. Additionally, there needs to be a tag matching the version number exactly. For example, if you just released version 1.1.1 from 1.1.0 and you use a git repository as your upstream vcs type, then you would need to run::

    $ git tag 1.1.1 -m "Releasing version 1.1.1 of foo"

If you use a different tagging scheme, git bloom-import-upstream can handle that, see `git bloom-import-upstream -h`.

Importing the upstream repository
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The first step in the release pipeline is to import the new version from upstream into the local release repository. To do this run the `git bloom-import-upstream` command::

    $ git bloom-import-upstream
    [git-bloom-import-upstream]: Searching in upstream development branch for the name and version
    [git-bloom-import-upstream]:   Upstream url: git@github.com:bar/foo.git
    [git-bloom-import-upstream]:   Upstream type: git
    [git-bloom-import-upstream]: Checking for package.xml(s)
    [git-bloom-import-upstream]: package.xml(s) found
    [git-bloom-import-upstream]: Found upstream with version: 0.5.35
    [git-bloom-import-upstream]: Upstream contains package: foo
    [git-bloom-import-upstream]: Exporting version 0.5.35
    [git-bloom-import-upstream]: The latest upstream tag in the release repository is upstream/0.5.33
    gbp:info: Importing '/tmp/bloom_hmZ0lr/upstream-0.5.35.tar.gz' to branch 'upstream'...
    gbp:info: Source package is upstream
    gbp:info: Upstream version is 0.5.35
    gbp:info: Successfully imported version 0.5.35 of /tmp/bloom_hmZ0lr/upstream-0.5.35.tar.gz
    I'm happy.  You should be too.

The above output should be very similar to what you get.

What happens if you try again?::

    $ git bloom-import-upstream
    [git-bloom-import-upstream]: Searching in upstream development branch for the name and version
    [git-bloom-import-upstream]:   Upstream url: git@github.com:ros/catkin.git
    [git-bloom-import-upstream]:   Upstream type: git
    [git-bloom-import-upstream]: Checking for package.xml(s)
    [git-bloom-import-upstream]: package.xml(s) found
    [git-bloom-import-upstream]: Found upstream with version: 0.5.35
    [git-bloom-import-upstream]: Upstream contains package: catkin
    [git-bloom-import-upstream]: Exporting version 0.5.35
    [git-bloom-import-upstream]: The latest upstream tag in the release repository is upstream/0.5.35
    [git-bloom-import-upstream]: The upstream version, 0.5.35, is equal to a previous import version. git-buildpackage will fail, if you want to replace the existing upstream import use the '--replace' option.
    gbp:info: Importing '/tmp/bloom_mN1iDw/upstream-0.5.35.tar.gz' to branch 'upstream'...
    gbp:info: Source package is upstream
    gbp:info: Upstream version is 0.5.35
    fatal: tag 'upstream/0.5.35' already exists
    gbp:error: git returned 128
    gbp:error: Couldn't tag "upstream/0.5.35"
    gbp:error: Import of /tmp/bloom_mN1iDw/upstream-0.5.35.tar.gz failed
    [git-bloom-import-upstream]: 'execute_command' failed to call 'git import-orig /tmp/bloom_mN1iDw/upstream-0.5.35.tar.gz --no-interactive --no-merge' which had a return code (1):
    [git-bloom-import-upstream]: git-import-orig failed 'git import-orig /tmp/bloom_mN1iDw/upstream-0.5.35.tar.gz --no-interactive --no-merge'

The command failed because you have previously imported this version of the upstream. As the above warnings tell say, you can override this by using the '--replace' argument.


