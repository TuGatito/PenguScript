#include <sys/types.h>
typedef long long intptr_t;
typedef unsigned long long uintptr_t;
int close(int fd);
ssize_t read(int fd, void *buf, size_t count);
ssize_t write(int fd, const void *buf, size_t count);
off_t lseek(int fd, off_t offset, int whence);
int unlink(const char *pathname);
int usleep(unsigned int usec);
unsigned int sleep(unsigned int seconds);
