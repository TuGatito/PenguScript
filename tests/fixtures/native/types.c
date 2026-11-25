#include "types.h"

int probar(Punto p, Coordenada c, Modo m, Dato d, Registro r) {
  return (int)(p.x + p.y + c.x + m + d.entero + r.nivel + r.pesos[1]);
}

int avisar_si_hay(Aviso aviso) { return aviso == 0 ? 0 : 1; }
