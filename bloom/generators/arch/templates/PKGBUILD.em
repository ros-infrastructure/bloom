# Script generated with Bloom
pkgdesc="ROS - @(Description)"
@[if Homepage and Homepage != '']url='@(Homepage)'@[end if]

pkgname='@(Package)'
pkgver='@(Version)'
pkgrel='@(Pkgrel)'
arch=('any')
license=(@[for p in Licenses]'@p'@\n@[end for])

makedepends=(@[for p in BuildDepends]'@p'@\n@[end for])

depends=(@[for p in Depends]'@p'@\n@[end for])

conflicts=(@[for p in Conflicts]'@p'@\n@[end for])
replaces=(@[for p in Replaces]'@p'@\n@[end for])

_dir=@(Name)
source=()
md5sums=()

prepare() {
    cp -R $startdir/@(Name) $srcdir/@(Name)
}

build() {
  # Use ROS environment variables
  source /usr/share/ros-build-tools/clear-ros-env.sh
  [ -f /opt/ros/@(ROSDistribution)/setup.bash ] && source /opt/ros/@(ROSDistribution)/setup.bash

  # Create build directory
  [ -d ${srcdir}/build ] || mkdir ${srcdir}/build
  cd ${srcdir}/build

  # Fix Python2/Python3 conflicts
  /usr/share/ros-build-tools/fix-python-scripts.sh -v 2 ${srcdir}/${_dir}

  # Build project
  cmake ${srcdir}/${_dir} \
        -DCMAKE_BUILD_TYPE=Release \
        -DCATKIN_BUILD_BINARY_PACKAGE=ON \
        -DCMAKE_INSTALL_PREFIX=/opt/ros/@(ROSDistribution) \
        -DPYTHON_EXECUTABLE=/usr/bin/python2 \
        -DPYTHON_INCLUDE_DIR=/usr/include/python2.7 \
        -DPYTHON_LIBRARY=/usr/lib/libpython2.7.so \
        -DPYTHON_BASENAME=-python2.7 \
        -DSETUPTOOLS_DEB_LAYOUT=OFF
  make
}

package() {
  cd "${srcdir}/build"
  make DESTDIR="${pkgdir}/" install
}

