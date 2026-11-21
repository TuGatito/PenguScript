#include "demo.h"

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
