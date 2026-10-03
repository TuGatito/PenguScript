#include <stdio.h>
#include <string.h>
int main(void) {
  long acc = 0;
  for (int i = 0; i < 50000; i++) {
    char buf[32];
    int n = snprintf(buf, sizeof buf, "item-%d", i);
    acc += n;
  }
  printf("%ld\n", acc);
  return 0;
}
