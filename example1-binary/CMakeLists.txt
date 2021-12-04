cmake_minimum_required(VERSION 3.20)
project(example1)

set(CMAKE_CXX_STANDARD 14)

add_executable(example1 main.cpp tcpconnect.cpp tcpconnect.h)
