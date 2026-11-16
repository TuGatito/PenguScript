---

<a id="sec-20"></a>
## 20. Diagnósticos

El compilador emite códigos estables. Un error impide compilar; un warning no.

El catálogo tiene **141 códigos** (141 errores, 0 warnings), por debajo del límite de 150 del núcleo.

### 20.1 Formato

```text
PGS-E3001: tipos incompatibles
  --> src/main.pengu:12:9
   |
12 |     bind x: Int = "pengu"
   |                   ^^^^^^^ se esperaba `Int`
```

Cada diagnóstico incluye: código, mensaje, archivo, línea, columna, fragmento y una solución cuando existe.

### 20.2 Catálogo

| Código | Situación |
|---|---|
| `PGS-E1001` | BOM al inicio. |
| `PGS-E1002` | Tabulador en indentación. |
| `PGS-E1003` | Indentación no múltiplo de cuatro. |
| `PGS-E1004` | `DEDENT` sin nivel correspondiente. |
| `PGS-E1005` | String sin cerrar. |
| `PGS-E1006` | Char o byte char sin cerrar. |
| `PGS-E1007` | Escape desconocido. |
| `PGS-E1008` | Byte char no ASCII. |
| `PGS-E1009` | Comentario de bloque sin cerrar. |
| `PGS-E1010` | Término retirado. |
| `PGS-E1011` | Identificador Unicode inválido. |
| `PGS-E1101` | `bind`/`morph` en nivel de módulo. |
| `PGS-E1102` | Redeclaración en el mismo bloque. |
| `PGS-E1103` | Asignación a un binding inmutable. |
| `PGS-E1104` | Asignación a un campo privado. |
| `PGS-E1105` | Patrón refutable sin `else`. |
| `PGS-E1106` | `sigil` sin tipo explícito. |
| `PGS-E1107` | `sigil` con expresión no constante. |
| `PGS-E1108` | `relic` reasignado. |
| `PGS-E1201` | Método faltante en el `ritual`. |
| `PGS-E1202` | Firma incompatible con el `pact`. |
| `PGS-E1203` | `pact` con más de un superpact. |
| `PGS-E1204` | `pact` con tipo asociado. |
| `PGS-E1205` | `ritual` para tipo ajeno y pact ajeno. |
| `PGS-E1206` | Implementaciones solapadas. |
| `PGS-E1207` | Blanket impl. |
| `PGS-E1208` | `dyn`/`impl Pact` en la superficie. |
| `PGS-E1209` | `Self` fuera de un `pact`/`ritual`. |
| `PGS-E1301` | Parámetro de tipo no usado. |
| `PGS-E1302` | Bound no satisfecho. |
| `PGS-E1303` | Bound desconocido. |
| `PGS-E1304` | Turbofish con número incorrecto de tipos. |
| `PGS-E1305` | No se puede inferir el parámetro. |
| `PGS-E1306` | `where` en la superficie. |
| `PGS-E1307` | Tipo asociado en un `pact`. |
| `PGS-E1308` | Genérico en un contexto no permitido. |
| `PGS-E1401` | Tipos incompatibles en un operador. |
| `PGS-E1402` | Operador no definido para el tipo. |
| `PGS-E1403` | División por cero constante. |
| `PGS-E1404` | Cast inválido. |
| `PGS-E1405` | `?` fuera de una función que devuelve `Option`/`Result`. |
| `PGS-E1406` | Sobrecarga de un operador no permitido. |
| `PGS-E1407` | Firma de sobrecarga incorrecta. |
| `PGS-E1408` | Comparación encadenada. |
| `PGS-E1501` | `?` en función que no devuelve `Option`/`Result`. |
| `PGS-E1502` | Error de `?` incompatible. |
| `PGS-E1503` | `unwrap` en producción. |
| `PGS-E1504` | `Option`/`Result` usado como valor directo. |
| `PGS-E1505` | `Result` sin tipo de error concreto. |
| `PGS-E1506` | `panic` en una rama que debía devolver valor. |
| `PGS-E1507` | `err` sin tipo de éxito. |
| `PGS-E1508` | `none` sin tipo. |
| `PGS-E1601` | `foreign` con cuerpo. |
| `PGS-E1602` | Llamada a `foreign` fuera de `curse`. |
| `PGS-E1603` | `curse` sin comentario `-- SAFETY:`. |
| `PGS-E1604` | Tipo no representable en C. |
| `PGS-E1605` | ABI desconocido. |
| `PGS-E1606` | Exportación de función PenguScript a C. |
| `PGS-E1607` | `curse` usado fuera de FFI. |
| `PGS-E1608` | `CString` sin manejo de `NulError`. |
| `PGS-E1701` | `@@test` con parámetros. |
| `PGS-E1702` | `@@test` con retorno inválido. |
| `PGS-E1703` | `should_panic` sin mensaje. |
| `PGS-E1704` | `assert_eq` con tipos incompatibles. |
| `PGS-E1705` | Doc test que no compila. |
| `PGS-E1706` | `@@test` duplicado. |
| `PGS-E1801` | No se puede inferir la vida de una referencia. |
| `PGS-E1802` | Versión de `pengu` incompatible. |
| `PGS-E1803` | Dependencia no encontrada. |
| `PGS-E1804` | Lockfile desactualizado. |
| `PGS-E1805` | `pengu fmt` no puede formatear. |
| `PGS-E1806` | `pengu publish` sin licencia. |
| `PGS-E1810` | `Tome.toml` inválido. |
| `PGS-E2001` | No se encuentra `Tome.toml`. |
| `PGS-E2002` | Falta `main.pengu` o `lib.pengu`. |
| `PGS-E2003` | Módulo no encontrado. |
| `PGS-E2004` | `summon` de un nombre inexistente. |
| `PGS-E2005` | Import duplicado. |
| `PGS-E2006` | Item privado usado fuera del módulo. |
| `PGS-E2007` | `unveil` inválido en este contexto. |
| `PGS-E2008` | `grimoire` duplicado. |
| `PGS-E2009` | `grimoire` ausente en un binario. |
| `PGS-E2010` | `Tome.toml` inválido. |
| `PGS-E2011` | Dependencia no declarada. |
| `PGS-E2012` | Ciclo de módulos. |
| `PGS-E3001` | Tipos incompatibles. |
| `PGS-E3002` | No se puede inferir el tipo. |
| `PGS-E3003` | El tipo no existe. |
| `PGS-E3004` | Genérico sin bound requerido. |
| `PGS-E3005` | Bound no satisfecho. |
| `PGS-E3006` | Referencia en posición prohibida. |
| `PGS-E3007` | `?T` usado con un tipo que no es `Option`. |
| `PGS-E3008` | `Result` con error no concreto. |
| `PGS-E3009` | Alias recursivo. |
| `PGS-E3010` | Newtype sin campo. |
| `PGS-E3101` | Índice fuera de rango en tiempo de compilación. |
| `PGS-E3102` | `Map` con clave sin `Eq`/`Hash`. |
| `PGS-E3103` | `Set` con elemento sin `Eq`/`Hash`. |
| `PGS-E3104` | `Vec` con tipo no inferido. |
| `PGS-E3105` | Literal de mapa con entrada inválida. |
| `PGS-E3106` | `push` sobre un binding inmutable. |
| `PGS-E4101` | Uso de un valor movido. |
| `PGS-E4102` | Préstamo inmutable y mutable simultáneos. |
| `PGS-E4103` | Asignación a un binding inmutable. |
| `PGS-E4104` | Referencia que escapa del scope. |
| `PGS-E4105` | Referencia en campo, variante o retorno. |
| `PGS-E4106` | Movimiento de un valor prestado. |
| `PGS-E4107` | `Rc`/`Arc` usado sin importar. |
| `PGS-E4108` | Destrucción de un valor todavía prestado. |
| `PGS-E6001` | Condición que no es `Bool`. |
| `PGS-E6002` | Ramas de `if` con tipos incompatibles. |
| `PGS-E6003` | `else` sin `if`. |
| `PGS-E6004` | `break`/`continue` fuera de un bucle. |
| `PGS-E6005` | `break` con valor fuera de `loop`. |
| `PGS-E6006` | `return` con valor en función `Unit`. |
| `PGS-E6007` | `loop` sin `break` usado como valor. |
| `PGS-E6008` | `match` no exhaustivo. |
| `PGS-E7001` | Falta el tipo de retorno. |
| `PGS-E7002` | Retorno incompatible con la firma. |
| `PGS-E7003` | Parámetro sin tipo. |
| `PGS-E7004` | `return` en una closure. |
| `PGS-E7005` | Llamada con número de argumentos incorrecto. |
| `PGS-E7006` | Tipo de argumento incorrecto. |
| `PGS-E7007` | Función usada como valor sin tipo. |
| `PGS-E7008` | `Never` en una posición que requiere valor. |
| `PGS-E8001` | Campo duplicado. |
| `PGS-E8002` | Campo faltante en la construcción. |
| `PGS-E8003` | Campo desconocido. |
| `PGS-E8004` | Variante duplicada. |
| `PGS-E8005` | `..base` con tipo incompatible. |
| `PGS-E8006` | `@@derive` desconocido. |
| `PGS-E8007` | `@@derive` imposible para un campo. |
| `PGS-E8008` | `Option`/`Result` redeclarados. |
| `PGS-E9001` | Patrón no exhaustivo. |
| `PGS-E9002` | Brazo inalcanzable. |
| `PGS-E9003` | Patrón incompatible con el tipo. |
| `PGS-E9004` | Guard que no es `Bool`. |
| `PGS-E9005` | `bind ... else` sin divergencia. |
| `PGS-E9006` | `..` en posición inválida. |
| `PGS-E9007` | Binding duplicado en un patrón. |
| `PGS-E9008` | `else` después de un brazo exhaustivo. |

### 20.3 Reglas

- Un código no cambia de significado entre versiones menores.
- Un código retirado no se reutiliza.
- `pengu explain <código>` muestra la explicación y un ejemplo.
- Los warnings se pueden silenciar con `pengu lint --allow <código>`.

[↑ Volver al índice](#indice)
