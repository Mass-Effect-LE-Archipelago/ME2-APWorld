cmake_minimum_required(VERSION 3.20)
project(APAsiLoader LANGUAGES C CXX RC)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")  # static CRT: no runtime to install

add_library(bink2w64 SHARED loader.cpp hook.cpp hde/hde64.c version.rc)
target_compile_definitions(bink2w64 PRIVATE WIN32_LEAN_AND_MEAN NOMINMAX UNICODE _UNICODE)
target_compile_options(bink2w64 PRIVATE /W4 /permissive-)

# Offline test (see README): a fake MassEffect2.exe host loads the loader, which attaches test.asi.
add_executable(MassEffect2 test/host.cpp)
add_library(loadertest SHARED test/plugin.cpp)
set_target_properties(loadertest PROPERTIES OUTPUT_NAME test SUFFIX .asi)
