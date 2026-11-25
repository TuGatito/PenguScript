#pragma once

#define CONTEO 7
#define NEGATIVO (-3)
#define GRANDE 5000000000LL
#define PI_F 3.14159265358979323846f
#define ESCALA 2.5f
#define MEDIO_PI (PI_F / 2.0f)
#define SALUDO "hola"
#define INICIAL 'p'
#define DOBLE(x) ((x) * 2)
#define _PLATAFORMA 1
#define flags 3

typedef struct Color {
  unsigned char r;
  unsigned char g;
  unsigned char b;
  unsigned char a;
} Color;

#define ROJO CLITERAL(Color){255, 0, 0, 255}

typedef enum { TIPO_A = 1, TIPO_B = 2 } Tipo;
#define TIPO_POR_DEFECTO TIPO_A

int probar(void);
