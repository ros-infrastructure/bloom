0.3.0
-----
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


