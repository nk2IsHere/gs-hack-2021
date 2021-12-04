// Server side C/C++ program to demonstrate Socket programming
#include <unistd.h>
#include <stdio.h>
#include <sys/socket.h>
#include <stdlib.h>
#include <netinet/in.h>
#include <string.h>
#include <iostream>
#include "tcpconnect.h"

#pragma clang diagnostic push
#pragma ide diagnostic ignored "EndlessLoop"
#define PORT "578"

uint64_t fib(long long n)
{
  if (n <= 1)
    return n;
  return fib(n-1) + fib(n-2);
}


int main(int argc, char **argv) {
    int sockfd = tcpconnect_start_multiple(PORT); /* ./server 5555 */
    int acceptsock = 0;
    while (true) {
        acceptsock = tcpconnect_accept_single(sockfd);
//        pid_t pid = fork();
        char buf[64];
        ssize_t len = read(acceptsock, buf, 63);
        if(len > 0) {
            buf[len] = 0;

            long long int v = std::stoll(buf);

            std::cout << "fib[" << v << "]: ";
            auto s = std::to_string(fib(v));
            std::cout << s << "\n";
            write(acceptsock, s.c_str(), s.length());
            close(acceptsock);
        }
//        if(pid == 0)
//            return 0;
    }
}

#pragma clang diagnostic pop