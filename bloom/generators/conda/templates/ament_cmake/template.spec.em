package:
  name: @(Package)
  version: @(Version)
source:
  path: @(Package)/src/work

build:
  script:
    sel(win): bld_ament_cmake.bat
    sel(unix): build_ament_cmake.sh
  number: @(CONDAInc)
about:
  @[if Homepage and Homepage != '']home: @(Homepage)@\n@[end if]@
  license: @(License)
  summary: ROS @(Name) package

extra:
  recipe-maintainers:
    - ros-forge

requirements:
  build:
    - "{{ compiler('cxx') }}"
    - "{{ compiler('c') }}"
    - ninja
    - sel(unix): make
    - sel(osx): tapi
    - cmake
    - sel(build_platform != target_platform): python
    - sel(build_platform != target_platform): cross-python_{{ target_platform }}
    - sel(build_platform != target_platform): cython
  host:
    - python
    @[for p in Depends]    - @p@\n@[end for]@
    @[for p in BuildDepends]    - @p@\n@[end for]@
  run:
    - python
    @[for p in Depends]    - @p@\n@[end for]@
    - sel(osx and x86_64): __osx >={{ MACOSX_DEPLOYMENT_TARGET|default('10.14') }}
