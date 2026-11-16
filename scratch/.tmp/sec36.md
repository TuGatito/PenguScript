<a id="sec-36-associated-items"></a>
## 36. Associated items (types, consts, GATs)

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 5 |
| Rust | `type`, `const`, GATs, RPITIT, `async fn` |
| Palabras mágicas | `pact`, `essence`, `sigil`, `Self` |
| Depende de | §31, §35 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec36_associated.pengu` |

Los **items asociados** pertenecen a un `pact` o a un `ritual`, no al módulo.
Pueden ser tipos (`essence`), constantes (`sigil`) o funciones. Permiten que un
contrato diga “tengo un tipo de elemento” sin fijarlo en la declaración.

### 36.1 Tipos asociados

```pengu
pact Container
    essence Item

    first = (@) -> ?&Item

rune Numbers
    values: Vec[Int]

ritual Container for Numbers
    essence Item = Int

    first = (@) -> ?&Int
        @.values.first()

bind n = Numbers(values: Vec[1, 2, 3])
print(n.first())
```

Rust generado:

```rust
trait Container {
    type Item;

    fn first(&self) -> Option<&Self::Item>;
}

struct Numbers {
    values: Vec<i32>,
}

impl Container for Numbers {
    type Item = i32;

    fn first(&self) -> Option<&i32> {
        self.values.first()
    }
}

fn main() {
    let n = Numbers { values: vec![1, 2, 3] };
    println!("{:?}", n.first());
}
```

Reglas:

1. `essence Nombre` sin `=` declara un tipo asociado en un `pact`.
2. `essence Nombre = Tipo` lo fija en un `ritual`.
3. Dentro del `pact`, `Item` se refiere a `Self::Item`; fuera se proyecta con
   `Self::Item` o `Pact::Item` según el contexto.
4. Un tipo asociado debe fijarse exactamente una vez por implementación
   (`PGS-E3601`).
5. El tipo puede depender de los parámetros del `pact`.
6. No hay defaults de tipo asociado en el subconjunto estable; se fija en cada
   `ritual`.

### 36.2 Proyecciones y bounds

```pengu
pact Container
    essence Item
    first = (@) -> ?&Item

sum_first = [C](container: &C) -> ?Int where C: Container[Item = Int]
    container.first().copied()

rune Numbers
    values: Vec[Int]

ritual Container for Numbers
    essence Item = Int
    first = (@) -> ?&Int
        @.values.first()

bind n = Numbers(values: Vec[1, 2, 3])
print(sum_first(&n))
```

Rust generado:

```rust
trait Container {
    type Item;
    fn first(&self) -> Option<&Self::Item>;
}

fn sum_first<C>(container: &C) -> Option<i32>
where
    C: Container<Item = i32>,
{
    container.first().copied()
}

struct Numbers {
    values: Vec<i32>,
}

impl Container for Numbers {
    type Item = i32;
    fn first(&self) -> Option<&i32> {
        self.values.first()
    }
}

fn main() {
    let n = Numbers { values: vec![1, 2, 3] };
    println!("{:?}", sum_first(&n));
}
```

1. `Pact[Item = Tipo]` fija el asociado en un bound.
2. `Self::Item` es la proyección dentro del `pact`; `C::Item` es la proyección
   sobre un parámetro.
3. No se puede asumir un asociado no fijado; el compilador lo trata como opaco.
4. Un bound de asociado no crea una implementación; solo restringe.

### 36.3 Constantes asociadas

```pengu
pact Limits
    sigil MAX: Int
    sigil NAME: Str

rune Small
    value: Int

ritual Limits for Small
    sigil MAX: Int = 100
    sigil NAME: Str = "small"

print(Small.MAX)
print(Small.NAME)
```

Rust generado:

```rust
trait Limits {
    const MAX: i32;
    const NAME: &'static str;
}

struct Small {
    value: i32,
}

impl Limits for Small {
    const MAX: i32 = 100;
    const NAME: &'static str = "small";
}

fn main() {
    println!("{}", Small::MAX);
    println!("{}", Small::NAME);
}
```

1. Una constante asociada se declara con `sigil` dentro de un `pact`.
2. Debe ser evaluable en `const`; no puede llamar a métodos no `const`.
3. Se accede como `Tipo.CONSTANTE`, no como `Tipo.CONSTANTE()`.
4. Un `pact` con constantes asociadas no es object safe (§35.5).
5. El tipo debe ser `Sized` para una constante asociada de tipo `Self`; se
   prefiere un tipo concreto.

### 36.4 GATs (generic associated types)

Un **GAT** es un tipo asociado con parámetros propios, normalmente un lifetime:

```pengu
pact Lending
    essence View['a] where Self: 'a
    view = ['a](@) -> Self::View['a]

rune Buffer
    data: Vec[Int]

ritual Lending for Buffer
    essence View['a] = &'a [Int]

    view = ['a](@) -> &'a [Int]
        &@.data[..]

bind b = Buffer(data: Vec[1, 2, 3])
print(b.view().len())
```

Rust generado:

```rust
trait Lending {
    type View<'a>
    where
        Self: 'a;

    fn view<'a>(&'a self) -> Self::View<'a>;
}

struct Buffer {
    data: Vec<i32>,
}

impl Lending for Buffer {
    type View<'a> = &'a [i32];

    fn view<'a>(&'a self) -> &'a [i32] {
        &self.data[..]
    }
}

fn main() {
    let b = Buffer { data: vec![1, 2, 3] };
    println!("{}", b.view().len());
}
```

Reglas:

1. `essence View['a]` declara un GAT con un parámetro de lifetime; el
   `where Self: 'a` es obligatorio en el subconjunto estable de Rust.
2. Los parámetros del GAT se declaran en el corchete, como los de un `rune`.
3. En el `ritual`, `essence View['a] = &'a [Int]` fija la familia de tipos.
4. El método que devuelve `Self::View['a]` declara `['a]` y usa `@` con ese
   lifetime. El GAT exige `where Self: 'a` para que la implementación pueda
   prestar datos del receptor.
5. Los GATs permiten préstamos sin boxeo; son la base de iteradores que
   devuelven referencias.
6. No se permiten GATs con parámetros de tipo que no aparezcan en la firma;
   el compilador los rechaza.

### 36.5 RPITIT y `async fn` en `pact`

Un método de `pact` puede devolver `impl Iterator` (RPITIT) o ser `dream`:

```pengu
pact Evens
    evens = (@) -> impl Iterator[Item = Int]

rune Numbers
    values: Vec[Int]

ritual Evens for Numbers
    evens = (@) -> impl Iterator[Item = Int]
        @.values.iter().copied().filter((x: Int) => x % 2 == 0)

bind n = Numbers(values: Vec[1, 2, 3, 4])
print(n.evens().count())
```

Rust generado:

```rust
trait Evens {
    fn evens(&self) -> impl Iterator<Item = i32>;
}

struct Numbers {
    values: Vec<i32>,
}

impl Evens for Numbers {
    fn evens(&self) -> impl Iterator<Item = i32> {
        self.values.iter().copied().filter(|x| x % 2 == 0)
    }
}

fn main() {
    let n = Numbers { values: vec![1, 2, 3, 4] };
    println!("{}", n.evens().count());
}
```

`async fn` en un `pact` se declara con `dream`:

```pengu
pact Fetch
    dream fetch = (@) -> String

rune Client
    name: String

ritual Fetch for Client
    dream fetch = (@) -> String
        "data from #{@.name}"
```

Rust generado:

```rust
trait Fetch {
    async fn fetch(&self) -> String;
}

struct Client {
    name: String,
}

impl Fetch for Client {
    async fn fetch(&self) -> String {
        format!("data from {}", self.name)
    }
}
```

1. RPITIT devuelve un tipo opaco por método; no se puede nombrar fuera del
   `pact`.
2. `impl Iterator[Item = Int]` es la forma de return-position `impl Trait`.
3. `dream` en un `pact` es `async fn`; el llamador necesita un runtime (§50).
4. Un `pact` con `async fn` no es object safe en el sentido clásico; para
   despacho dinámico se usa `dyn` con cuidado o se evita.
5. `impl Trait` en retorno de un `pact` captura los lifetimes del receptor; si
   el préstamo no vive, el compilador lo rechaza.

### 36.6 `Self` y proyecciones

1. `Self` es el tipo que implementa; en un `pact` es el tipo del receptor.
2. `Self::Item` proyecta un tipo asociado; `Self` solo es válido en
   `pact`/`ritual`.
3. En un `ritual`, `Self` se puede usar en firmas y cuerpos.
4. `Self` no se puede usar como valor de retorno por valor en un `pact` object
   safe; usa `&Self` o un tipo concreto.
5. Las proyecciones no se evalúan en runtime; son tipos.

### 36.7 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E3601` | tipo asociado no fijado | añadir `essence Item = Tipo` |
| `PGS-E3602` | tipo asociado fijado dos veces | eliminar duplicado |
| `PGS-E3603` | GAT con parámetro no usado | usar el parámetro o eliminarlo |
| `PGS-E3604` | bound de asociado incompatible | alinear `Pact[Item = Tipo]` |
| `PGS-E3605` | `impl Trait` en posición inválida | moverlo a retorno/parámetro |
| `PGS-E3606` | `async fn` en `pact` object-safe | usar `dyn` compatible o evitar |
| `PGS-E3607` | constante asociada no const | simplificar la expresión |
| `PGS-W3601` | GAT que solo se usa con un lifetime | simplificar a tipo asociado |

### 36.8 Criterios de aceptación

- [x] Tipos asociados, proyecciones y bounds tienen ejemplo.
- [x] Constantes asociadas están definidas.
- [x] GATs tienen ejemplo compilable.
- [x] RPITIT y `async fn` en `pact` están cubiertos.
- [x] `Self` y los diagnósticos están explicados.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)
