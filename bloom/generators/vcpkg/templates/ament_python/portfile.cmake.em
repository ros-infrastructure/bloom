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

find_package(PythonInterp 3)

if (${PYTHONINTERP_FOUND})
    set(SETUP_INSTALL_PREFIX "${CURRENT_PACKAGES_DIR}")
    set(SETUP_INSTALL_PYTHONPATH "${SETUP_INSTALL_PREFIX}/Lib/site-packages")
    file(TO_NATIVE_PATH "${SETUP_INSTALL_PREFIX}" SETUP_INSTALL_PREFIX)
    file(TO_NATIVE_PATH "${SETUP_INSTALL_PYTHONPATH}" SETUP_INSTALL_PYTHONPATH)

    file(MAKE_DIRECTORY ${SETUP_INSTALL_PYTHONPATH})
    set(INSTALL_CMD
        # if we want to use install --prefix, we must use following line to set PYTHONPATH
        ${CMAKE_COMMAND} -E env PYTHONPATH=${SETUP_INSTALL_PYTHONPATH}
        ${PYTHON_EXECUTABLE}
        setup.py
        egg_info --egg-base .
        build --build-base build
        install --prefix ${SETUP_INSTALL_PREFIX}
        --record install.log
        --single-version-externally-managed
        )

    execute_process(
        COMMAND ${INSTALL_CMD}
        WORKING_DIRECTORY ${SOURCE_PATH}
    )
else()
    message(FATAL_ERROR "Python executable not fould, stop building")
endif()