cmake_minimum_required(VERSION 3.16)
project(SmartHomeSimulator VERSION 2.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
add_compile_options(-Wall -Wextra)
endif()

include_directories(include)
file(GLOB_RECURSE SOURCES src/*.cpp)
add_executable(simulator ${SOURCES})

option(BUILD_TESTS "Build device-simulator unit tests" OFF)

if(BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()
