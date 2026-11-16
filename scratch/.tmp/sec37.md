<a id="sec-37-hrtb"></a>
## 37. Higher-Ranked Items (HRTB)

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 5 |
| Rust | `for<'a>`, HRTB, function pointers |
| Palabras mágicas | `for<'a>`, `Fn`, `dyn` |
| Depende de | §18, §34, §38, §39 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec37_hrtb.pengu` |

Un **Higher-Ranked Trait Bound** (HRTB) expresa que una función o un tipo debe
funcionar para **todos** los lifetimes, no para uno concreto. Se escribe
`for<'a>` y se lee “para todo `'a`”. No es un tipo de item nuevo: es una forma de
cuantificar lifetimes en un bound o en un tipo de función.

### 37.1 `for<'a>` en tipos de función

```pengu
first = (s: &Str) -> &Str
    &s[..1]

apply_fn = (f: for<'a> (&'a Str) -> &'a Str, s: &Str) -> &Str
    f(s)

print(apply_fn(first, "pengu"))
```

Rust generado:

```rust
fn first(s: &str) -> &str {
    &s[..1]
}

fn apply_fn(f: for<'a> fn(&'a str) -> &'a str, s: &str) -> &str {
    f(s)
}

fn main() {
    println!("{}", apply_fn(first, "pengu"));
}
```

Reglas:

1. `for<'a> (A) -> B` es un tipo de función que funciona para cualquier
   lifetime `'a`.
2. `for<'a>` solo cuantifica lifetimes; no existen `for<T>` ni `for<const N>`.
3. Un `fn` item como `first` cumple automáticamente el HRTB si su firma es
   compatible.
4. Un function pointer (`fn`) es `Copy`; un closure que captura no lo es
   necesariamente (§38).
5. La forma sin `for<'a>` puede ser early-bound o elidida; si el préstamo debe
   vivir lo que el llamador decida, se escribe `for<'a>`.

### 37.2 HRTB en bounds

```pengu
apply = [F](f: F, s: &Str) -> &Str where F: for<'a> Fn(&'a Str) -> &'a Str
    f(s)

print(apply(first, "pengu"))
```

Rust generado:

```rust
fn first(s: &str) -> &str {
    &s[..1]
}

fn apply<F>(f: F, s: &str) -> &str
where
    F: for<'a> Fn(&'a str) -> &'a str,
{
    f(s)
}

fn main() {
    println!("{}", apply(first, "pengu"));
}
```

1. `F: for<'a> Fn(&'a T) -> &'a U` exige que `F` acepte cualquier lifetime.
2. Se puede combinar con otros bounds: `F: for<'a> Fn(&'a T) + Clone`.
3. El HRTB se comprueba en el punto de llamada; un closure que solo acepta un
   lifetime concreto no cumple.
4. La sintaxis `for<'a>` también aparece en `dyn` y en tipos de función.

### 37.3 `dyn for<'a>`

```pengu
first = (s: &Str) -> &Str
    &s[..1]

bind f: Box[dyn for<'a> Fn(&'a Str) -> &'a Str] = Box.new(first)
print(f("pengu"))
```

Rust generado:

```rust
fn first(s: &str) -> &str {
    &s[..1]
}

fn main() {
    let f: Box<dyn for<'a> Fn(&'a str) -> &'a str> = Box::new(first);
    println!("{}", f("pengu"));
}
```

1. `dyn for<'a> Fn(...)` es un trait object que acepta cualquier lifetime.
2. Necesita un puntero (`Box`, `&`, `Rc`, `Arc`).
3. El trait object no puede tener métodos genéricos; `for<'a>` en la firma no
   viola object safety porque el lifetime es parte del contrato.
4. `Fn`, `FnMut` y `FnOnce` aceptan `for<'a>`; `FnOnce` se consume al llamar.

### 37.4 Late-bound y early-bound

- Un lifetime **late-bound** se introduce en la llamada; `for<'a>` lo hace
  explícito. Es el caso de `fn(&str) -> &str` cuando la elisión lo permite.
- Un lifetime **early-bound** se fija al construir el item o el trait object;
  aparece en la firma del `fn` o en los parámetros del tipo.
- `for<'a>` fuerza late-bound: el llamador elige `'a` en cada llamada.
- Si un lifetime aparece solo en el retorno, debe estar conectado a un
  parámetro; si no, el compilador lo rechaza (`PGS-E3702`).

### 37.5 HRTB y closures

```pengu
apply = [F](f: F, s: &Str) -> &Str where F: for<'a> Fn(&'a Str) -> &'a Str
    f(s)

bind first = (s: &Str) => &s[..1]
print(apply(first, "pengu"))
```

1. Un closure puede cumplir un HRTB si no captura de forma que fije el lifetime.
2. Si el closure captura una referencia con un lifetime concreto, el HRTB puede
   fallar; usa `move` o un `fn` item.
3. `dyn for<'a> Fn` acepta closures y fn pointers.
4. Un closure que muta el entorno es `FnMut`; el HRTB se escribe
   `for<'a> FnMut(&'a T)`.

### 37.6 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E3701` | `for` sin lifetime | usar `for<'a>` |
| `PGS-E3702` | lifetime de retorno no conectado a un parámetro | añadir el préstamo o `'static` |
| `PGS-E3703` | HRTB no satisfecho por el closure | usar `move` o un `fn` item |
| `PGS-E3704` | `dyn` sin puntero | envolver en `Box[dyn ...]` o `&dyn ...` |
| `PGS-E3705` | `for<T>` o `for<const N>` | solo se cuantifican lifetimes |
| `PGS-W3701` | `for<'a>` redundante con la elisión | simplificar si no cambia la semántica |

### 37.7 Criterios de aceptación

- [x] `for<'a>` en tipos de función y bounds tiene ejemplo.
- [x] `dyn for<'a>` y su necesidad de puntero están definidos.
- [x] Late-bound/early-bound están explicados.
- [x] HRTB con closures está cubierto.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)
