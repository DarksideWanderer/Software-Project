find_package(GTest REQUIRED)
find_package(Threads REQUIRED)

add_executable(simulator_tests
    test_core.cpp
)

target_include_directories(simulator_tests PRIVATE
    ${CMAKE_SOURCE_DIR}/include
)

target_link_libraries(simulator_tests PRIVATE
    GTest::GTest
    Threads::Threads
)

add_test(NAME SimulatorCoreTests COMMAND simulator_tests)
