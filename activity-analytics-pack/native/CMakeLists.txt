cmake_minimum_required(VERSION 3.15)
project(monitor LANGUAGES CXX)


set(CMAKE_CONFIGURATION_TYPES Release)

add_executable(monitor
    monitor.cpp
    monitor_hook.cpp
)

target_compile_features(monitor PRIVATE cxx_std_17)
target_link_libraries(monitor PRIVATE psapi ole32)


set_target_properties(monitor PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/x64
)
