<a id="sec-62-precedencia"></a>
## 62. Precedencia y asociatividad

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 10 |
| Rust | — |
| Palabras mágicas | — |
| Depende de | §11, §13, §14 |
| Ejemplos ejecutables | `no` |

### 62.1 Tabla normativa

De mayor a menor precedencia. La columna “Asoc.” indica asociatividad;
“no asoc.” exige paréntesis si se encadena.

| Nivel | Operadores | Asoc. | Notas |
|---:|---|---|---|
| 1 | `.` `()` `[]` `?` turbofish | izquierda | postfix; `?` solo en `!T` |
| 2 | `awaken` | prefijo | solo en `dream` |
| 3 | `-` `+` `!` `*` `&` `&mut` | prefijo | unarios |
| 4 | `as` | izquierda | casts encadenados |
| 5 | `*` `/` `%` | izquierda | aritmética |
| 6 | `+` `-` | izquierda | aritmética |
| 7 | `<<` `>>` | izquierda | shifts |
| 8 | `&` | izquierda | bitwise and |
| 9 | `^` | izquierda | bitwise xor |
| 10 | `\|` | izquierda | bitwise or |
| 11 | `..` `..=` | no asoc. | rangos; extremo derecho opcional |
| 12 | `==` `!=` `<` `<=` `>` `>=` `is` `isnt` `in` | no asoc. | comparaciones |
| 13 | `not` | prefijo | negación lógica |
| 14 | `and` | izquierda | cortocircuito |
| 15 | `or` | izquierda | cortocircuito |
| 16 | `=` `+=` `-=` `*=` `/=` `%=` `&=` `\|=` `^=` `<<=` `>>=` | derecha | sentencia; valor `Unit` |

### 62.2 Reglas de parseo

1. `a + b * c` = `a + (b * c)`.
2. `a as T + b` = `(a as T) + b`.
3. `-a as T` = `(-a) as T`; para `-(a as T)` se usan paréntesis.
4. `a..b + 1` = `a..(b + 1)`, porque `+` tiene más precedencia que `..`.
5. `a..=b` y `a..` son rangos; `..b` no es válido en expresión (solo patrón).
6. `a == b == c` es error `PGS-E6201`; usar `(a == b) and (b == c)`.
7. `a < b < c` es error `PGS-E6201`.
8. `a is b`/`a isnt b` son `==`/`!=`; misma precedencia que comparaciones.
9. `x in xs` es membresía; `not x in xs` se parsea `not (x in xs)`.
10. `a and b or c` = `(a and b) or c`.
11. `a or b and c` = `a or (b and c)`.
12. `a = b = c` es error `PGS-E6202`; la asignación no encadena.
13. `a += b + c` = `a += (b + c)`.
14. `*p = x` requiere `curse`; el parser no cambia la precedencia.
15. `&mut x` es un prefijo único; no se parsea como `& (mut x)`.
16. `foo[Int](x)` es turbofish; `foo[0]` es indexación. El parser decide por
    el tipo del argumento entre corchetes: tipos conocidos -> turbofish;
    expresión -> índice. Si es ambiguo, se exige `foo::[Int](x)`? No existe:
    se usa `foo[Int](x)` con `Int` resuelto como tipo y `foo[0]` como índice.
17. `foo.bar[T](x)` es método genérico; `foo.bar[0]` es índice del campo.
18. `a?.b` = `(a?).b`; `a?` se evalúa antes del campo.
19. `a.b?` = `(a.b)?`.
20. `awaken f()` = `awaken (f())`; `awaken` no se mezcla con `?` sin paréntesis.

### 62.3 Ambigüedades resueltas

| Caso | Resolución |
|---|---|
| `foo[Int](x)` | turbofish si `Int` es un tipo en scope; si no, error |
| `foo[0]` | indexación; `0` es expresión |
| `foo[T]` sin `(` | indexación por valor `T` o tipo? Se prefiere indexación; para tipo se usa `foo[T]()` |
| `a < b > c` | error de comparación encadenada |
| `a..b` | rango; no es acceso a campo |
| `x @ pat` | binding de patrón, no receptor |
| `@` al inicio de línea | receptor en método; en patrón, binding |
| `-x.abs()` | `-(x.abs())` |
| `not a == b` | `not (a == b)` |
| `a as T?` | `(a as T)?` |
| `a? as T` | `(a?) as T` |
| `..=` sin izquierda | solo válido en patrón |
| `a..` | rango abierto; válido en expresión |
| `a..=..` | error `PGS-E6203` |

### 62.4 Tabla de resultados

| Expresión | Parseo |
|---|---|
| `1 + 2 * 3` | `1 + (2 * 3)` |
| `1 << 2 + 3` | `1 << (2 + 3)` porque `+` (6) tiene más precedencia que `<<` (7) |
| `1 & 2 == 0` | `(1 & 2) == 0` |
| `not a and b` | `(not a) and b` |
| `a or b and c` | `a or (b and c)` |
| `a..b + 1` | `a..(b + 1)` |
| `a + b..c` | `(a + b)..c` |
| `a as Int + 1` | `(a as Int) + 1` |
| `-a * b` | `(-a) * b` |
| `!a and b` | `(!a) and b` |
| `a?.b` | `(a?).b` |
| `a.b?` | `(a.b)?` |
| `awaken f()?` | `(awaken f())?` |
| `x in xs and y` | `(x in xs) and y` |

### 62.5 Criterios de aceptación

- [x] Hay una fila por nivel de precedencia.
- [x] La asociatividad está especificada.
- [x] Las comparaciones encadenadas se rechazan.
- [x] La asignación no encadena.
- [x] `as`, `?`, rangos y `awaken` tienen reglas explícitas.
- [x] Las ambigüedades de `[]` se resuelven.

[↑ Volver al índice](#indice)
