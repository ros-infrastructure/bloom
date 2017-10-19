Bloom generators
================

Generators read catkin/ament package manifests and generate files necessary to package releases for various target platforms.

## Build types

Prior to version 0.6.0, Bloom used a single template for all packages which supported packages built with cmake, including catkin packages.

Bloom now supports different build types by inspecting the `build_type` tag in package manifests.

Templates for a build type are stored in subdirectories of the platform's templates directory named for the build type.
As an example the templates for the `ament_cmake` build type for debian packages is stored in [bloom/generators/debian/templates/ament_cmake](debian/templates/ament_cmake).

To add support for a new build type create a new templates subdirectory for it in your target platform's `templates` directory, and add any necessary supporting code to the generator for build type specific substitutions.For examples search for "Build-type specific substitutions" in [bloom/generators/debian/generator.py](debian/generator.py).
