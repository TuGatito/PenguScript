#include <stdio.h>
#include <stdlib.h>
int main(void) {
  size_t cap = 16, len = 0;
  int *xs = malloc(cap * sizeof *xs);
  for (int i = 0; i < 200000; i++) {
    if (len == cap) { cap *= 2; xs = realloc(xs, cap * sizeof *xs); }
    xs[len++] = i;
  }
  long total = 0;
  for (size_t i = 0; i < len; i++) total += xs[i];
  printf("%ld\n", total);
  free(xs);
  return 0;
}
