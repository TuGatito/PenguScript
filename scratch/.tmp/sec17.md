<a id="sec-17-borrowing"></a>
## 17. Borrowing

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 3 |
| Rust | `&`, `&mut`, NLL, reborrow |
| Palabras mágicas | `&`, `&mut`, `@` |
| Depende de | §16, §18 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec17_borrowing.pengu` |

Un **préstamo** (borrow) permite usar un valor sin transferir su ownership. Hay
dos clases:

| Forma | Tipo | Acceso | Se escribe |
|---|---|---|---|
| compartido | `&T` | lectura | `&value` |
| mutable | `&mut T` | lectura y escritura | `&mut value` |

La regla central: **o muchos préstamos compartidos, o exactamente un préstamo
mutable**, nunca ambos a la vez. El borrow checker de Rust comprueba que los
préstamos no se solapen; los préstamos terminan en su último uso (NLL), no
necesariamente al final del scope.

### 17.1 Préstamos compartidos

```pengu
grimoire
    bind text = String.from("pengu")
    bind a = &text
    bind b = &text
    print(a.len() + b.len())
```

Rust generado:

```rust
fn main() {
    let text = String::from("pengu");
    let a = &text;
    let b = &text;
    println!("{}", a.len() + b.len());
}
```

Reglas:

1. `&value` presta `value` por lectura.
2. Se pueden crear tantos `&T` como se quiera mientras no haya un `&mut T`
   activo.
3. El dueño no se puede mover mientras exista un préstamo activo.
4. Un `&T` permite leer y copiar el valor si `T: Copy`, pero no mutarlo.
5. Un `&T` se puede volver a prestar como `&T` sin límite.

### 17.2 Préstamos mutables

```pengu
grimoire
    morph text = String.from("pengu")
    bind r = &mut text
    r.push_str("!")
    print(text)
```

Rust generado:

```rust
fn main() {
    let mut text = String::from("pengu");
    let r = &mut text;
    r.push_str("!");
    println!("{}", text);
}
```

Reglas:

1. `&mut value` requiere que `value` sea un binding `morph` o un campo mutable.
2. Mientras un `&mut T` esté activo, no puede haber ningún otro `&T` ni `&mut T`
   sobre el mismo valor (`PGS-E1701`).
3. A través de `&mut T` se puede leer y escribir.
4. El préstamo mutable termina en su último uso; después el dueño vuelve a ser
   usable.
5. No se puede mover el dueño mientras el préstamo mutable esté activo
   (`PGS-E1702`).

### 17.3 NLL: el préstamo termina en el último uso

```pengu
grimoire
    morph text = String.from("pengu")
    bind r = &text
    print(r.len())
    text.push_str("!")        -- permitido: r ya no se usa
    print(text)
```

Rust generado:

```rust
fn main() {
    let mut text = String::from("pengu");
    let r = &text;
    println!("{}", r.len());
    text.push_str("!");
    println!("{}", text);
}
```

El compilador no usa el scope léxico para decidir el fin del préstamo: usa el
último punto donde la referencia puede usarse. Esto se llama **non-lexical
lifetimes** (NLL). Un préstamo sigue activo mientras pueda usarse, aunque no se
use en una línea concreta.

### 17.4 Conflictos y errores

```text
error[E0502]: cannot borrow `text` as mutable because it is also borrowed as immutable
  --> src/main.rs:5:5
   |
 4 |     let r = &text;
   |             ----- immutable borrow occurs here
 5 |     text.push_str("!");
   |     ^^^^^^^^^^^^^^^^^ mutable borrow occurs here
 6 |     println!("{}", r.len());
   |                      - immutable borrow later used here
```

Correcciones, en orden:

1. Terminar el préstamo compartido antes de mutar (reordenar).
2. Usar un scope explícito para limitar el préstamo.
3. Pasar `&mut` a una función en lugar de mezclar préstamos.
4. Usar `RefCell`/`Cell` si la mutabilidad interior es realmente necesaria
   (§20.4).

### 17.5 Reborrow

Prestar una referencia crea un **reborrow**:

```pengu
grow = (text: &mut String) -> Unit
    text.push_str("!")

grimoire
    morph text = String.from("pengu")
    grow(&mut text)
    grow(&mut text)
    print(text)
```

Rust generado:

```rust
fn grow(text: &mut String) {
    text.push_str("!");
}

fn main() {
    let mut text = String::from("pengu");
    grow(&mut text);
    grow(&mut text);
    println!("{}", text);
}
```

Reglas:

1. `&mut *r` y `&*r` re-prestan el valor apuntado por `r`.
2. El reborrow puede acortar el préstamo; es la base de pasar `&mut` a funciones
   sin perder el dueño.
3. Un reborrow mutable no puede coexistir con otro préstamo activo.
4. El compilador inserta reborrows implícitos al llamar funciones que esperan
   `&mut T`; no hace falta escribirlos siempre.

### 17.6 Préstamos en funciones

```pengu
length = (text: &Str) -> Usize
    text.len()

append = (text: &mut String, suffix: &Str) -> Unit
    text.push_str(suffix)

grimoire
    morph text = String.from("pengu")
    append(&mut text, "!")
    print(length(&text))
```

Rust generado:

```rust
fn length(text: &str) -> usize {
    text.len()
}

fn append(text: &mut String, suffix: &str) {
    text.push_str(suffix);
}

fn main() {
    let mut text = String::from("pengu");
    append(&mut text, "!");
    println!("{}", length(&text));
}
```

Reglas:

1. Un parámetro `&T` no consume el argumento.
2. Un parámetro `&mut T` requiere un binding `morph` y presta mutabilidad.
3. La función no puede guardar la referencia más allá de su lifetime; §18
   explica cómo se declara.
4. Devolver una referencia requiere que el lifetime de salida esté ligado a una
   entrada (§18.2).

### 17.7 Structs con referencias

Un `rune` puede contener referencias, pero necesita un lifetime:

```pengu
rune Excerpt['a]
    text: &'a Str

ritual Excerpt['a]
    len = (@) -> Usize
        @.text.len()

grimoire
    bind text = "pengu"
    bind excerpt = Excerpt(text: text)
    print(excerpt.len())
```

Rust generado:

```rust
struct Excerpt<'a> {
    text: &'a str,
}

impl<'a> Excerpt<'a> {
    fn len(&self) -> usize {
        self.text.len()
    }
}

fn main() {
    let text = "pengu";
    let excerpt = Excerpt { text };
    println!("{}", excerpt.len());
}
```

Reglas:

1. El `rune` declara sus parámetros de lifetime entre `[...]`.
2. El lifetime del campo debe ser un parámetro del `rune`, no un `'static`
   implícito.
3. El `ritual` repite `['a]` para implementar sobre `Excerpt['a]`.
4. El valor prestado debe vivir al menos tanto como el `rune` (§18.5).

### 17.8 Conflictos con colecciones: `split_at_mut`

Dos préstamos mutables a mitades distintas son seguros si el compilador puede
demostrar que no se solapan:

```pengu
grimoire
    morph values = Vec.from([1, 2, 3, 4])
    bind (left, right) = values.split_at_mut(2)
    left[0] = 9
    right[0] = 8
    print(left[0] + right[0])
```

Rust generado:

```rust
fn main() {
    let mut values = Vec::from([1, 2, 3, 4]);
    let (left, right) = values.split_at_mut(2);
    left[0] = 9;
    right[0] = 8;
    println!("{}", left[0] + right[0]);
}
```

`split_at_mut` es la solución estándar para mutar dos mitades a la vez. Otras
soluciones: `chunks_mut`, `iter_mut`, `split_first_mut`, o separar los datos en
campos distintos.

### 17.9 Mutabilidad interior

Cuando un valor compartido necesita mutar por dentro, se usa mutabilidad
interior (§20.4):

```pengu
bind cell = RefCell.new(0)
*cell.borrow_mut() += 1
print(*cell.borrow())
```

Rust generado:

```rust
use std::cell::RefCell;

fn main() {
    let cell = RefCell::new(0);
    *cell.borrow_mut() += 1;
    println!("{}", *cell.borrow());
}
```

`RefCell` comprueba los préstamos en runtime; un conflicto produce panic, no un
error de compilación. `Cell` copia valores y no permite referencias; `Mutex` y
`RwLock` son las versiones thread-safe (§20.5).

### 17.10 Préstamos y `@`

Dentro de un método:

| Receptor | Equivale a | Permite |
|---|---|---|
| `@` | `&self` | leer campos, llamar métodos `&self` |
| `@mut` | `&mut self` | mutar campos, llamar métodos `&mut self` |
| `@own` | `self` | consumir el valor |

Un método `@` no puede mutar el receptor; uno `@mut` no puede coexistir con un
préstamo compartido activo. El compilador aplica las mismas reglas que a
cualquier `&`/`&mut`.

### 17.11 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E1701` | préstamo mutable y compartido solapados | terminar uno antes del otro |
| `PGS-E1702` | move mientras hay un préstamo activo | esperar a que termine el préstamo |
| `PGS-E1703` | dos préstamos mutables solapados | usar `split_at_mut` o separar campos |
| `PGS-E1704` | préstamo de un temporal que no vive suficiente | guardar el temporal en un `bind` |
| `PGS-E1705` | retorno de referencia sin lifetime | añadir `'a` o devolver el valor |
| `PGS-E1706` | `&mut` sobre binding inmutable | usar `morph` |
| `PGS-W1701` | préstamo compartido innecesariamente largo | acortar el scope |

### 17.12 Criterios de aceptación

- [x] `&`/`&mut` y la regla XOR están definidos.
- [x] NLL y reborrow están explicados.
- [x] Los préstamos en funciones y retornos están cubiertos.
- [x] Los structs con referencias introducen lifetimes.
- [x] Los conflictos y sus soluciones incluyen `split_at_mut` e interior
      mutability.
- [x] El ejemplo de error muestra el mensaje de Rust y la corrección.
- [x] El ejemplo tiene Rust compilable.

[↑ Volver al índice](#indice)

