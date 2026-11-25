#pragma once

typedef struct Punto { float x; float y; } Punto;
typedef Punto Coordenada;
typedef enum { MODO_A = 1, MODO_B = 4, MODO_C } Modo;
typedef union Dato { int entero; float real; } Dato;
typedef struct Registro {
  Punto p;
  Dato d;
  Modo m;
  unsigned int activo : 1;
  unsigned int nivel : 3;
  float pesos[2];
} Registro;

typedef void (*Aviso)(int nivel);

int probar(Punto p, Coordenada c, Modo m, Dato d, Registro r);
int avisar_si_hay(Aviso aviso);
