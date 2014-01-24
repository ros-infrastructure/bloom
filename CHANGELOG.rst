0.4.7 (2014-01-24 15:50:00 -0800)
---------------------------------
- Fix bug in pull request opening with new rosdistro format

0.4.6 (2014-01-24 15:33:00 -0800)
---------------------------------
- Updates to support REP-0141 with rosdistro >= 0.3.0 and rosdep >= 0.10.25
- @ahendrix contributed an option for doing ssh key based pull request generation

0.4.5 (2014-01-22 10:58:50 -0800)
---------------------------------
- Added Python2/3 bilingual support, bloom should now install and work with Python3
- Added an assertion that the rosdistro version 1 is being used in preperation of REP-0141 roll out
- Fixed crash from unicode characters in the changelog
- Added assertions about the format of version numbers used
- Added check for git submodules, still not supported, but bloom will fail earlier with a better error
- Fixed a bug where empty folders containing a .gitignore in the upstream caused bloom to fail

0.4.4 (2013-07-22 17:50:55 -0700)
---------------------------------
- Properly handle pagination of github pages #174
- Made the pull request branch names more unique to avoid collisions in parallel releasing situations #178
- Disabled automatic opening of the webbrowser on Linux and added an option to disable it otherwise #162
- Fixed a problem where permissions where lost on templates, this applied specifically to loosing the executable flag on the debian rules file #179
- Only put the first maintainer listed in the debian/control file to prevent lintian errors #183

0.4.3 (2013-07-19 16:37:23 -0700)
---------------------------------
- Fixed a bug with creating new tracks
- Fixed a bug where the debian changelog would be wrong if a CHANGELOG.rst existed for the package, but there was no entry for this version being release
- Fixed a bug where the colorization of the diff could cause a crass to occur
- Added a versioned dependency on rosdistro-0.2.12, which addresses a rosdistro file formatting bug
- Fixed some issues with the stand alone rosdebian generator
- Temporary fix for github pagination problems

0.4.2 (2013-06-27 11:20:25 -0700)
---------------------------------
- Improved logging system slightly.
- Fixed the way logs are renamed after closing.
- Fixed a bug where names were not debian'ized for packages which rosdep could not resolve. #163
- Fixed a bug where a diff of the rosdistro file would fail when packages were being removed. #165
- Fixed a bug where upconverting repository configs could fail if a track.yaml and a bloom.conf existed. #166

0.4.1 (2013-06-25 12:17:13 -0700)
---------------------------------
- Fixed a bug which occurred on repositories with no previous releases. #158
- Fixed a bug where safety warnings were being printed when they should not have been. #159
- Fixed a bug where repositories with multiple packages did not consider peer packages when resolving rosdep keys. #160

0.4.0 (2013-06-19 17:13:36 -0700)
---------------------------------
- Automated Pull Requests have been re-enabled, but now the .netrc file is **not** used.
- REP-0132 CHANGELOG.rst files are now parsed and inserted into generated debian changes files.
- bloom now summarizes activity on the master branch, which is useful for figuring out what has been released recently.
- There is a new command bloom-generate, which allows generators to expose a stand alone generation command. For example, you can now run ``bloom-generate debian`` in a single catkin package and it will generate the needed files in the local ``debian`` folder. Addresses #121
- The command line options for ``bloom-release`` have been changed to be more explicit.
- The ``bloom`` branch is now deprecated, the ``master`` branch now holds all configurations and upstream overlay files. The ``bloom`` branch can be deleted after the automatic upgrade where bloom moves the needed files from the ``bloom`` branch to the ``master`` branch.
- Fuerte is no longer supported; this is because supporting fuerte was complicating the code base, use an older version of bloom (0.3.5) for fuerte releases.
- Packages can now be explicitly ignored by bloom by putting their names (separated by whitespace) in the <track>.ignored file in the master branch.
- Deprecated rosdep calls have been replaced with rosdistro.
- bloom now logs all output to log files in the ``~/.bloom_logs`` folder.
- Fixed several bugs:

    - Fixed use of tar as a vcs type #149
    - Fixed a bug where ``--new-track``'s changes would not take affect #147
    - bloom now allows a debian folder to already exist, overlaying other generated files #146
    - bloom now allows for an alternative release repository url which is used for pushing #137

0.3.5 (2013-04-17 11:03:50 -0700)
---------------------------------
- Temporarily disable automated pull requests while the new rosdistro format is being deployed.
- bloom now suggests likely alternatives when a repository is not found in the release file.

0.3.4 (2013-04-09 16:36:55 -0700)
---------------------------------
- Fixed a bug in the update notifier where the first run after updating still reports that bloom is out of date. #129
- bloom-release now respects global arguments like --version and --debug
- Improved messages around the cloning/pushing back of the working copy which takes a long time on large repos.
- Improved pull request failure message, indicating that the release was successful, but the pr was not. #131
- Fixed versioned dependencies in debians and setup.py. #130
- Fixed a bug with empty ~/.netrc files. #131
- General improvements with the automated pull request mechanism. #135
- Checks for valid metapackages using catkin_pkg now, adds version dependency of catkin_pkg at 0.1.11. #134

0.3.3 (2013-04-01 14:04:00 -0700)
---------------------------------
- bloom no longer allows users to release metapackages which do not have a CMakeLists.txt. See: `REP-0127 <http://ros.org/reps/rep-0127.html#metapackage>`_
- Fixed a bug related to gathering of package meta data on hg and svn repositories. #111
- Fixed a bug in git-bloom-patch which prevented users from running it directly. #110
- Fixed a bug where patches would not get applied after exporting them manually. #107
- Worked around a bug in vcstools which would not allow hg repositories to checkout to existing, empty directories. #112
- All git-bloom-* scripts now assert that they are in the root of a git repository. #113
- Added PEP8 check to the automated tests.
- bloom-release will now offer the user a git push --force if non-force fails.
- Added git-bloom-config [copy|rename] commands.
- Fixed a bug in the bloom.git.checkout api where it would return 0 on success, but should return True. #122
- bloom-release will now prompt the user for the release repository url if it is not in the rosdistro file. #125
- bloom-release will now offer to automatically open a pull-request for the user, if the user's .netrc file is setup for github. #126

0.3.2 (2013-03-06 17:49:51 -0800)
---------------------------------
- Fixed a bug in vcs url templating.
- Improved the performance of git-bloom-config.
- Added an --unsafe global option which will disable some of the safety mechanisms in bloom, making releasing about twice as fast but at the expense of errors putting the local release repository in an inconsistent state. Use with caution.
- Added support for templating stack.xml files like package.xml files in the import-upstream step.
- Fixed a bug where bloom failed if you call it and you were not on a branch
- Added global arguments to some commands which were still lacking them
- Fixed a bug where bloom would create None/<version> tags (these should be deleted manually if found)
- Got the automated tests fixed and running in travis again
- Added emoji icons for OS X users with lion or greater

0.3.1 (2013-02-26 18:00:47 -0800)
---------------------------------
- Fixed handling of non-standard archive names in git-bloom-import-upstream.
  This was a bug where if the archive only had the name of the package then it would fail to be processed by import-upstream.
- Fixed an issue when blooming from svn upstream.
  This issue was caused by improperly handling the release_tag configuration when dealing with svn

0.3.0 (2013-02-26 14:04:21 -0800)
---------------------------------
- Generators can now be added using the distribute entry_points machanism
- There is now a debian/<rosdistro>/<package_name> branch before forking into debian/<rosdistro>/<debian_distro>/<package_name>
  The debian/<rosdistro> branch now contains the untemplated debain files, so that they can be patched before being templated.
- Users are now dropped into a shell when patch merging fails, allowing them to resolve the problem and continue.
- New generator rosrelease, makes the release tag release/<rosdistro>/<package_name> instead of release/<package_name>
- Bloom now checks to see if it is the latest version available and warns if it is not
- Configurations are now stored in "tracks" so that there can be multiple release configurations in each release repository
- New command bloom-export-upstream, this command creates an archive (tar.gz) of upstream given a uri, type, and reference to archive
- Refactored git-bloom-import-upstream, this command only takes an archive (tar.gz) now
- Configurations are now stored on the bloom branch in YAML
- git-bloom-release now takes only one argument, the release track to execute
- Files can be automatically overlaid onto upstream using a patches folder in the bloom branch
  This allows you to put a package.xml onto upstream without a patch in the release branch.
- package.xml files overlaid onto upstream branch from the patches folder in the bloom branch are templated on the version
- Release tags now contain release increment numbers, similar to the debian increment numbers, e.g. release/groovy/foo/0.1.0 is now release/groovy/foo/0.1.0-0
- New command bloom-release <repository> [<track>], which will release a repository end-to-end
  It will fetch the release repository using info from the ROS distro file, run bloom, then push the results


