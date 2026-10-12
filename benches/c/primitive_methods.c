/* Baseline for `primitive_methods.pengu`: the identical algorithm with the
 * method call spelled as the plain C function it monomorphizes to. */
#include <stdio.h>

static int int_abs(int self) {
  if (self < 0) return 0 - self;
  return self;
}

int main(void) {
  long total = 0;
  for (int i = 0; i < 2000000; i++) {
    int v = 0 - i;
    total += int_abs(v) % 1000;
  }
  printf("%ld\n", total);
  return 0;
}
