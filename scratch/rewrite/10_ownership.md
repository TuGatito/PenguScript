---

<a id="sec-11"></a>
## 11. Ownership y referencias

### 11.1 Move

Asignar o pasar un valor owned lo **mueve**. Después del movimiento, el binding
original no se puede usar.

```pengu
bind a = String.from("pengu")
bind b = a
-- ERROR PGS-E1103: `a` fue movido
print(a)
```

Para conservar el original se presta (`&a`) o se clona explícitamente
(`a.clone()`).

### 11.2 `Copy`

Los tipos simples se copian en lugar de moverse:

`Bool`, `Int`, `I8`–`I64`, `U8`–`U64`, `Isize`, `Usize`, `Float`, `F32`,
`F64`, `Char`, `Unit`, tuplas de `Copy` y arrays de `Copy`.

```pengu
bind x = 1
bind y = x
print(x) -- válido: Int es Copy
```

Un record puede ser `Copy` solo si todos sus campos lo son y si se deriva con
`@@derive(Copy, Clone)`. `String`, `Vec`, `Map` y `Set` nunca son `Copy`.

### 11.3 `Clone`

`clone()` crea una copia profunda explícita:

```pengu
bind a = Vec[1, 2, 3]
bind b = a.clone()
```

No hay clonado implícito. Pasar un `Vec` a una función que no lo necesita
consume el original; si la función solo lee, recibe `&[T]`.

### 11.4 Referencias

```pengu
length = (s: &Str) -> Usize
    s.len()

append = (values: &mut Vec[Int], value: Int) -> Unit
    values.push(value)
```

Reglas:

- `&T` presta de forma inmutable; `&mut T` presta de forma mutable.
- No puede haber a la vez un `&T` y un `&mut T` al mismo valor.
- Una referencia no puede escapar de la función que la crea.
- No se guardan referencias en campos, variantes, retornos, alias ni
  colecciones.
- No se escribe ninguna anotación de vida. El compilador la infiere.

### 11.5 Referencias en locales

```pengu
bind text = String.from("pengu")
bind view: &Str = &text
print(view)
```

La referencia vive mientras `text` viva y no se mueva. El compilador rechaza
usar `view` después de mover `text`.

### 11.6 Retornos

Una función no puede devolver `&T` ni `&mut T`:

```pengu
-- ERROR PGS-E1801
first_word = (text: &Str) -> &Str
    text
```

Para devolver una vista se devuelve el valor owned (`String`), un `Box[String]`
o un `Rc[String]`/`Arc[String]`.

### 11.7 `Box`, `Rc`, `Arc`

- `Box[T]` es propiedad única en el heap.
- `Rc[T]` comparte dentro de un hilo.
- `Arc[T]` comparte entre hilos.

`Box` está en la prelude. `Rc` y `Arc` se importan:

```pengu
summon std::rc::Rc

bind shared = Rc.new(String.from("pengu"))
bind copy = shared.clone()
print(shared.len())
```

`Rc` y `Arc` no son `Copy`; clonarlos incrementa el contador. No hay
mutabilidad interior en el núcleo: si se necesita, se importa de
`std.cell`/`std.concurrent` y se hace explícita.

### 11.8 Destrucción

El valor se destruye automáticamente al final de su scope. No hay `Drop`
visible ni `defer` en el núcleo. El orden es el inverso al de declaración.

### 11.9 Préstamos y métodos

Un método `@` toma `&self`; `@mut` toma `&mut self`; `@own` toma `self`.

```pengu
rune Counter
    value: Int

ritual Counter
    get = (@) -> Int
        @.value

    bump = (@mut) -> Unit
        @.value = @.value + 1

    into_value = (@own) -> Int
        @.value
```

### 11.10 Diagnósticos de ownership

| Código | Situación |
|---|---|
| `PGS-E4101` | Uso de un valor movido. |
| `PGS-E4102` | Préstamo inmutable y mutable simultáneos. |
| `PGS-E4103` | Asignación a un binding inmutable. |
| `PGS-E4104` | Referencia que escapa del scope. |
| `PGS-E4105` | Referencia en campo, variante o retorno. |
| `PGS-E4106` | Movimiento de un valor prestado. |
| `PGS-E4107` | `Rc`/`Arc` usado sin importar. |
| `PGS-E4108` | Destrucción de un valor todavía prestado. |
| `PGS-E1801` | No se puede inferir la vida de una referencia. |

[↑ Volver al índice](#indice)
