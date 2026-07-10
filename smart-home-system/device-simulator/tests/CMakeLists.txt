/**
 * device-simulator CMakeLists.txt for GTest
 *
 * 用法:
 *   cd device-simulator
 *   mkdir -p build && cd build
 *   cmake .. -DBUILD_TESTS=ON
 *   make && ./tests/simulator_tests
 */

# 在主 CMakeLists.txt 中添加:
#
# option(BUILD_TESTS "Build unit tests" OFF)
#
# if(BUILD_TESTS)
#     enable_testing()
#     find_package(GTest REQUIRED)
#     add_subdirectory(tests)
# endif()
#
# --- tests/CMakeLists.txt ---
#
# add_executable(simulator_tests
#     test_core.cpp
#     ../src/main.cpp  # 或链接设备库
# )
# target_link_libraries(simulator_tests
#     GTest::GTest
#     GTest::Main
#     pthread
# )
# target_include_directories(simulator_tests PRIVATE
#     ${CMAKE_SOURCE_DIR}/include
# )
# add_test(NAME SimulatorCoreTests COMMAND simulator_tests)
