cmake_minimum_required(VERSION 3.16)
project(ZeroAI-Desk-CPP LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

list(APPEND CMAKE_PREFIX_PATH "C:/Qt6/6.8.0/msvc2022_64")

find_package(Qt6 COMPONENTS Core Gui Widgets Network Svg REQUIRED)

add_executable(ZeroAI-Desk-CPP WIN32
    src_cpp/main.cpp
    src_cpp/MainWindow.h
    src_cpp/MainWindow.cpp
    src_cpp/OllamaClient.h
    src_cpp/OllamaClient.cpp
)

target_link_libraries(ZeroAI-Desk-CPP PRIVATE
    Qt6::Core
    Qt6::Gui
    Qt6::Widgets
    Qt6::Network
    Qt6::Svg
)

if(MSVC)
    target_compile_options(ZeroAI-Desk-CPP PRIVATE /W4 /EHsc /utf-8)
endif()
