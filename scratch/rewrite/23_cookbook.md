---

<a id="sec-24"></a>
## 24. Cookbook

### 24.1 Hola

```pengu
grimoire
    print("hola, pengu")
```

### 24.2 Argumentos

```pengu
summon std::env

grimoire
    bind args = env.args()
    if args.len() > 1 then
        print(args[1])
    else
        print("sin argumentos")
```

### 24.3 Leer un archivo

```pengu
summon std::fs

enchanting ReadError
    Missing(path: String)
    Invalid

read_config = (path: &Str) -> Result[String, ReadError]
    bind text = fs.read_to_string(path) else
        return err(Missing(String.from(path)))
    ok(text)
```

### 24.4 Propagar errores

```pengu
enchanting AppError
    Read(ReadError)
    Parse

load = (path: &Str) -> Result[String, AppError]
    bind text = read_config(path).map_err((e: ReadError) => Read(e))?
    ok(text)
```

### 24.5 CLI con código de salida

```pengu
summon std::process

grimoire: Result[Unit, AppError]
    bind text = load("app.toml")?
    print(text)
    ok(())
```

Si el `Result` es `err`, el backend imprime el error y sale con código 1.

### 24.6 Records y sums

```pengu
rune User
    name: String
    age: Int

enchanting Role
    Admin
    Member
    Guest

describe = (user: User, role: Role) -> String
    match role
        when Admin then "#{user.name} (admin)"
        when Member then "#{user.name} (member)"
        when Guest then "#{user.name} (invitado)"
```

### 24.7 Colecciones

```pengu
morph counts = { "a": 1, "b": 2 }
counts.insert("c", 3)

morph names = Vec["ana", "pengu"]
names.push("lua")

morph tags = Set["magic", "static"]
tags.insert("sharp")

for (key, value) in counts do
    print("#{key} = #{value}")
```

### 24.8 Patrones

```pengu
bind (x, y) = (1, 2)
bind Point(px, py) = Point(x: 3.0, y: 4.0)

bind status = match result
    when ok(value) then "ok: #{value}"
    when err(reason) then "error: #{reason}"
```

### 24.9 Un método

```pengu
rune Counter
    value: Int

ritual Counter
    bump = (@mut) -> Unit
        @.value = @.value + 1

    get = (@) -> Int
        @.value

morph counter = Counter(value: 0)
counter.bump()
print(counter.get())
```

### 24.10 FFI

```pengu
summon std::ffi::CString

foreign "C"
    puts = (text: &CStr) -> Int

grimoire
    bind message = CString.new("hola") else
        panic("NUL")
    curse
        -- SAFETY: el CString vive hasta después de puts y puts no retiene el puntero.
        _ = puts(&message)
```

### 24.11 Test

```pengu
add = (a: Int, b: Int) -> Int
    a + b

@@test
adds = () -> Unit
    assert_eq(add(1, 2), 3)
```

### 24.12 Librería

```pengu
-- lib.pengu
unveil rune Greeting
    unveil text: String

unveil greet = (name: &Str) -> Greeting
    Greeting(text: "hola, #{name}")
```

[↑ Volver al índice](#indice)
