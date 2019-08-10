include(vcpkg_common_functions)

set(VCPKG_BUILD_TYPE release)

@[if GitSource == 'gitlab']@
vcpkg_from_gitlab(
@[elif GitSource == 'github']@
vcpkg_from_github(
@[elif GitSource == 'bitbucket']@
vcpkg_from_bitbucket(
@[end if]@
    OUT_SOURCE_PATH SOURCE_PATH
    REPO @(UserName)/@(RepoName)
    REF @(TagName)
)

set(ROS_BASE_PATH "C:/opt/ros/@(RosDistro)")
file(TO_NATIVE_PATH "${ROS_BASE_PATH}" ROS_BASE_PATH)

vcpkg_configure_cmake(
    SOURCE_PATH ${SOURCE_PATH}
	OPTIONS
		-DAMENT_PREFIX_PATH=${ROS_BASE_PATH}
)

vcpkg_install_cmake()
