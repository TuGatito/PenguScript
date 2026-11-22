#include "demo.h"

#include <stdarg.h>

double suma(double a, double b) {
  return a + b;
}

int contar(const char *texto) {
  int total = 0;
  while (texto[total] != '\0') total++;
  return total;
}

int maximo(int a, int b) {
  return a > b ? a : b;
}

int sumar_varios(int cuantos, ...) {
  va_list args;
  va_start(args, cuantos);
  int total = 0;
  for (int index = 0; index < cuantos; index++) total += va_arg(args, int);
  va_end(args);
  return total;
}
