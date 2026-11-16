# B3d: estado y estrategia restante

## Hecho

- Closures con captura y sin captura (`Box<dyn Fn>` + `ClosureCall`).
- `for` sobre `Vec`, array, slice, `Set` y `Map` (Set/Map se materializan a `Vec`
  con `collect`; Map produce tuplas `(K, V)`).
- Tests reales de ejecución en `crates/pengu-codegen/tests/codegen.rs`.

## Pendiente

1. **Iteradores/adaptadores**: `Vec.iter()`/`Vec.into_iter()` producen
   `Ty::Iterator`, y `map`/`filter` son perezosos; `fold`/`collect` son
   terminales. La LIR usa `LTerm::Next` con bloques `some`/`none`. `Map.iter()`
   y `Set.iter()` también producen `Ty::Iterator`; ya no se materializan a `Vec`.
2. **Impls genéricos**: `emit_impl` usa la primera `LFunction` del método. Hay
   que especializar por `(DefId, Vec<Ty>)` y emitir `impl<T>` o `impl` concreto
   según el uso; los cuerpos deben bajar con el mismo `type_env` de B2.
3. **Runtime/`Drop`**: B4. `Show`/`print` ya se emiten; falta `Drop` explícito
   y el runtime de errores/panic.

- `for (clave, valor) in mapa` desestructura la tupla con `LStmt::Destructure`; también se soportan tuplas anidadas (`(a, (b, c))`).

- `Map.iter()`/`Set.iter()` se bajan como `IntoIter` consumidor para mantener el tipo `Iterator[(K,V)]`/`Iterator[T]` sin referencias.

- `Map.iter()`/`Set.iter()` bajan a `IntoIter` consumidor para mantener el tipo de item por valor; documentado.
- Closures con parámetros tipados ya enlazan sus locales en el checker; `len` existe para `Vec`/`Map`/`Set`/`String`/`Str`.

- `impl[T] Tipo[T]` inherente se emite como `impl<T> Tipo<T>` usando la firma HIR y un cuerpo LIR representativo; los métodos con operaciones dependientes de `T` siguen limitados por el lowering.

- `MonoPlan` ahora instancia métodos de impls genéricos desde los tipos ADT concretos del checker y `lower_crate` los baja con el entorno del impl. `emit_impl` emite `impl Wrap<i32>` por instancia.
- Caso resuelto: `ritual[T] Wrap[T] { get = (@) -> T { @.value } }` con `Wrap[Int]`. Para `T` no-`Copy` sigue haciendo falta `@own`/clone; no se inserta un `clone` implícito.
