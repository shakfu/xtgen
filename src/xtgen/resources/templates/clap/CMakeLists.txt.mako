<%
mfr = (e.namespace + "xxxx")[:4]
mfr = mfr[0].upper() + mfr[1:]
sub = (e.name + "xxxx")[:4]
# A generator (no audio input) is a music device: clap-wrapper v0.16 builds no 'augn'.
au_type = "aumu" if e.dsp and not e.dsp.n_inputs else "aufx"
%>\
# ${e.name}: CLAP plugin, wrapped as VST3 (and AUv2 on macOS) by clap-wrapper.
#
#   cmake -B build -DCMAKE_BUILD_TYPE=Release
#   cmake --build build --target ${e.name}_all
#
# The first configure downloads CLAP, clap-wrapper and the VST3/AU SDKs.

cmake_minimum_required(VERSION 3.21)
project(${e.name} VERSION 0.1.0 LANGUAGES C CXX)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# AUv2 four-character codes. Replace with codes registered for your product.
set(AUV2_MANUFACTURER_CODE "${mfr}")
set(AUV2_SUBTYPE_CODE "${sub}")

set(CLAP_WRAPPER_DOWNLOAD_DEPENDENCIES TRUE CACHE BOOL "Download VST3 and AU SDKs")

include(FetchContent)
FetchContent_Declare(clap
    GIT_REPOSITORY https://github.com/free-audio/clap.git
    GIT_TAG 1.2.10)
FetchContent_Declare(clap-wrapper
    GIT_REPOSITORY https://github.com/free-audio/clap-wrapper.git
    GIT_TAG v0.16.0)
FetchContent_MakeAvailable(clap clap-wrapper)

add_library(${e.name}-impl STATIC ${e.name}.c${f" {e.dsp.prefix}.c" if e.dsp else ""})
target_link_libraries(${e.name}-impl PUBLIC clap)

set(PLUGIN_FORMATS CLAP VST3)
if (APPLE)
    list(APPEND PLUGIN_FORMATS AUV2)
endif()

make_clapfirst_plugins(
    TARGET_NAME ${e.name}
    IMPL_TARGET ${e.name}-impl
    OUTPUT_NAME "${e.name}"
    ENTRY_SOURCE "${e.name}_entry.cpp"
    BUNDLE_IDENTIFIER "${e.namespace}.${e.name}"
    BUNDLE_VERSION ${"${PROJECT_VERSION}"}
    COPY_AFTER_BUILD FALSE
    PLUGIN_FORMATS ${"${PLUGIN_FORMATS}"}
    ASSET_OUTPUT_DIRECTORY ${"${CMAKE_BINARY_DIR}"}/${e.name}_assets
    AUV2_MANUFACTURER_NAME "${e.meta['author']}"
    AUV2_MANUFACTURER_CODE ${"${AUV2_MANUFACTURER_CODE}"}
    AUV2_SUBTYPE_CODE ${"${AUV2_SUBTYPE_CODE}"}
    AUV2_INSTRUMENT_TYPE "${au_type}"
)
