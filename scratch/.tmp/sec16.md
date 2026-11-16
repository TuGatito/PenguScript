<a id="sec-16-ownership"></a>
## 16. Ownership

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 3 |
| Rust | `move`, `Copy`, `Clone`, `Drop`, `std::mem` |
| Palabras mágicas | `bind`, `morph`, `@own` |
| Depende de | §5, §15 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec16_ownership.pengu` |

Cada valor tiene **un solo dueño**. El dueño es responsable de liberar el valor
cuando sale de scope. Asignar, pasar como argumento o devolver un valor no
`Copy` transfiere la propiedad (un **move**); el dueño anterior deja de ser
usable. Esta regla es la base de la seguridad de memoria sin GC.

### 16.1 Move

```pengu
rune Token
    id: Int

grimoire
    bind a = Token(id: 1)
    bind b = a          -- mueve a -> b
    print(b.id)
    -- print(a.id)     -- error: a fue movido
```

Rust generado:

```rust
struct Token {
    id: i32,
}

fn main() {
    let a = Token { id: 1 };
    let b = a;
    println!("{}", b.id);
    // println!("{}", a.id); // error: use of moved value
}
```

Un move ocurre en:

| Operación | Ejemplo | Efecto |
|---|---|---|
| binding | `bind b = a` | `a` se mueve a `b` |
| reasignación | `b = a` | `a` se mueve a `b` |
| argumento | `take(a)` | `a` se mueve al parámetro |
| retorno | `return a` | `a` se mueve al llamador |
| campo | `bind n = pair.name` | el campo se mueve; el resto queda parcial |
| colección | `vec.push(a)` | `a` se mueve al vector |
| `@own` | `value.consume()` | el receptor se mueve al método |

Después de un move, el binding original no se puede leer, escribir, prestar ni
mover otra vez (`PGS-E1601`). El compilador de Rust emite `E0382`; el front-end
de PenguScript lo traduce a `PGS-E1601` con la misma ubicación.

### 16.2 `Copy`

Los tipos `Copy` se copian bit a bit en lugar de moverse:

```pengu
grimoire
    bind a = 10
    bind b = a
    print(a + b)        -- ambos siguen siendo válidos
```

Rust generado:

```rust
fn main() {
    let a = 10;
    let b = a;
    println!("{}", a + b);
}
```

Son `Copy`:

- todos los enteros, `Bool`, `Char`, `F32`/`F64`;
- las referencias compartidas `&T` (no `&mut T`);
- las tuplas y arrays de tipos `Copy`;
- un `rune` marcado `@@derive(Copy, Clone)` si todos sus campos son `Copy`.

No son `Copy`: `String`, `Vec[T]`, `Box[T]`, `Rc[T]`, `Arc[T]`, `HashMap`, ni
ningún tipo con `Drop`. Un tipo `Copy` no puede implementar `Drop`
(`PGS-E1602`); si necesita liberar recursos, no es `Copy`.

### 16.3 `Clone` explícito

Copiar un valor no `Copy` requiere `.clone()`:

```pengu
grimoire
    bind a = String.from("pengu")
    bind b = a.clone()
    print(a)
    print(b)
```

Rust generado:

```rust
fn main() {
    let a = String::from("pengu");
    let b = a.clone();
    println!("{}", a);
    println!("{}", b);
}
```

Reglas:

1. `.clone()` es explícito; no hay copia implícita de tipos no `Copy`.
2. `clone` puede ser costoso; no se usa para evitar pensar en ownership.
3. `@@derive(Clone)` genera `Clone` para un `rune` o `enchanting`.
4. `Clone` no implica `Copy`; `Copy` sí implica `Clone` (`PGS-E1603`).
5. Clonar una referencia (`&T.clone()`) clona la referencia, no el valor; para
   clonar el valor se usa `(*r).clone()` o `r.clone()` según el tipo.

### 16.4 `Drop`

Un tipo con `Drop` ejecuta código al salir de scope:

```pengu
rune Guard
    name: String

ritual Guard
    drop = (@mut) -> Unit
        print("drop #{@.name}")
```

El codegen implementa `Drop`:

```rust
struct Guard {
    name: String,
}

impl Drop for Guard {
    fn drop(&mut self) {
        println!("drop {}", self.name);
    }
}
```

Reglas:

1. `Drop` se ejecuta exactamente una vez, cuando el dueño sale de scope.
2. `Drop` no se llama en un move; el nuevo dueño se encarga.
3. El orden exacto se especifica en §21.3.
4. `Drop` y `Copy` son incompatibles (`PGS-E1602`).
5. No se llama `drop` manualmente; para liberar antes se usa un scope o
   `std.mem.drop` (que no existe en Rust estable; se usa `drop(value)`).
6. `std.mem.forget` evita el `Drop` y filtra memoria; es explícito y raro.

### 16.5 Moves parciales

```pengu
rune Pair
    name: String
    count: Int

grimoire
    bind pair = Pair(name: "pengu", count: 1)
    bind name = pair.name      -- mueve solo el campo name
    print(name)
    print(pair.count)          -- el campo count sigue disponible
    -- print(pair)            -- error: pair está parcialmente movido
```

Rust generado:

```rust
struct Pair {
    name: String,
    count: i32,
}

fn main() {
    let pair = Pair {
        name: String::from("pengu"),
        count: 1,
    };
    let name = pair.name;
    println!("{}", name);
    println!("{}", pair.count);
    // println!("{:?}", pair); // error: use of partially moved value
}
```

Reglas:

1. Se puede mover un campo de un `rune` que no implementa `Drop`.
2. Después del move parcial, el `rune` completo no se puede usar, pero los
   campos no movidos sí.
3. Un tipo con `Drop` no permite moves parciales (`PGS-E1604`).
4. Para conservar el `rune` completo, se presta el campo (`&pair.name`) o se
   clona.
5. Un `enchanting` con datos solo se mueve completo; el pattern matching puede
   mover campos en §30.

### 16.6 Ownership en funciones y retornos

Pasar un valor a una función lo mueve si el parámetro no es una referencia:

```pengu
take = (text: String) -> Unit
    print(text)

grimoire
    bind text = String.from("pengu")
    take(text)
    -- print(text) -- error: text fue movido
```

Rust generado:

```rust
fn take(text: String) {
    println!("{}", text);
}

fn main() {
    let text = String::from("pengu");
    take(text);
    // println!("{}", text); // error: use of moved value
}
```

Para conservar el valor se presta:

```pengu
borrow = (text: &Str) -> Unit
    print(text)

grimoire
    bind text = String.from("pengu")
    borrow(&text)
    print(text)
```

Rust generado:

```rust
fn borrow(text: &str) {
    println!("{}", text);
}

fn main() {
    let text = String::from("pengu");
    borrow(&text);
    println!("{}", text);
}
```

Devolver un valor transfiere ownership al llamador:

```pengu
make = () -> String
    String.from("pengu")

grimoire
    bind text = make()
    print(text)
```

Rust generado:

```rust
fn make() -> String {
    String::from("pengu")
}

fn main() {
    let text = make();
    println!("{}", text);
}
```

### 16.7 Ownership en colecciones

Meter un valor en un `Vec` lo mueve:

```pengu
grimoire
    morph names: Vec[String] = Vec.new()
    bind name = String.from("pengu")
    names.push(name)
    -- print(name) -- error: name fue movido al vector
    print(names.len())
```

Rust generado:

```rust
fn main() {
    let mut names: Vec<String> = Vec::new();
    let name = String::from("pengu");
    names.push(name);
    // println!("{}", name); // error: use of moved value
    println!("{}", names.len());
}
```

Sacar un valor del vector también lo mueve:

```pengu
bind first = names.remove(0)
```

`names[0]` indexa por referencia; para mover se usa `remove` o
`into_iter`. Los detalles están en §23.

### 16.8 `std.mem`: take, replace, swap, forget

```pengu
grimoire
    morph slot = String.from("old")
    bind taken = std.mem.take(&mut slot)
    bind replaced = std.mem.replace(&mut slot, String.from("new"))
    std.mem.swap(&mut slot, &mut taken)
    std.mem.forget(replaced)
    print(slot)
    print(taken)
```

Rust generado:

```rust
fn main() {
    let mut slot = String::from("old");
    let mut taken = std::mem::take(&mut slot);
    let replaced = std::mem::replace(&mut slot, String::from("new"));
    std::mem::swap(&mut slot, &mut taken);
    std::mem::forget(replaced);
    println!("{}", slot);
    println!("{}", taken);
}
```

| Operación | Efecto | Requiere |
|---|---|---|
| `std.mem.take(&mut x)` | deja `Default::default()` en `x` y devuelve el valor | `T: Default` |
| `std.mem.replace(&mut x, new)` | deja `new` y devuelve el valor anterior | — |
| `std.mem.swap(&mut a, &mut b)` | intercambia dos valores | mismos tipos |
| `std.mem.forget(x)` | consume `x` sin ejecutar `Drop` | — |

`forget` filtra memoria y recursos; solo se usa en código de bajo nivel
justificado. Un `Rc`/`Arc` con `forget` puede filtrar el contador.

### 16.9 Errores típicos del borrow checker

```text
error[E0382]: use of moved value: `a`
  --> src/main.rs:5:11
   |
 4 |     let b = a;
   |             - value moved here
 5 |     println!("{}", a.id);
   |                    ^ value used here after move
   |
   = note: move occurs because `a` has type `Token`, which does not implement the `Copy` trait
```

Soluciones, en orden de preferencia:

1. Prestar en lugar de mover: `print(&a)`.
2. Reordenar para usar `a` antes del move.
3. Clonar explícitamente: `a.clone()`.
4. Devolver el valor desde la función para transferir ownership al llamador.

### 16.10 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E1601` | uso después de move | prestar, reordenar o clonar |
| `PGS-E1602` | `Copy` + `Drop` | quitar `Copy` o `Drop` |
| `PGS-E1603` | `Copy` sin `Clone` | derivar `Clone` |
| `PGS-E1604` | move parcial de tipo con `Drop` | mover el valor completo o prestar |
| `PGS-E1605` | move de un valor prestado | terminar el préstamo o clonar |
| `PGS-E1606` | uso de un `rune` parcialmente movido | usar los campos no movidos |
| `PGS-W1601` | `clone` innecesario | prestar en su lugar |

### 16.11 Criterios de aceptación

- [x] Move, `Copy` y `Clone` están diferenciados.
- [x] `Drop` y la prohibición de `Copy + Drop` están definidos.
- [x] Los moves parciales y sus límites están especificados.
- [x] Ownership en funciones, retornos y colecciones está cubierto.
- [x] `std.mem.take/replace/swap/forget` están definidos.
- [x] Hay un ejemplo de error del borrow checker y sus soluciones.
- [x] El ejemplo tiene Rust compilable.

[↑ Volver al índice](#indice)

