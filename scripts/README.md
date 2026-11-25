# scripts/

Utilidades para compilar e instalar PenguScript sin depender del shell que uses.

| Script | Para qué |
|--------|----------|
| `install.sh` / `install.ps1` | Compilan `pengu` con Bun y dejan el ejecutable en un directorio del PATH. |
| `vsix.sh` / `vsix.ps1` | Empaquetan la extensión de VS Code como `.vsix` y la instalan con el CLI `code`. |
| `bench_backends.sh` | Compara el mismo bucle aritmético compilado a C++20 y a JavaScript (`--target js`). |
| `embed_std.ts` | Regenera `std_bundle.ts` con las fuentes de `std/` (lo exige un test). |

## Instalar el ejecutable

```sh
./scripts/install.sh                  # Linux / macOS: compila e instala en un directorio del PATH
./scripts/install.sh --prefix ~/bin   # directorio propio
./scripts/install.sh --skip-build     # reutiliza dist/pengu
```

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install.ps1
```

En Linux/macOS el script solo escribe el binario: nunca edita `.bashrc`, `.zshrc`,
`config.fish` ni perfiles de PowerShell. Si `~/.local/bin` ya está en PATH lo usa;
si no, elige el primer directorio escribible del PATH y, como último recurso, deja
el binario en `~/.local/bin` e indica cómo añadirlo. En Windows modifica la
variable `Path` de usuario (la heredan todos los shells).

## Medir los dos backends

```sh
./scripts/bench_backends.sh          # 10⁶ iteraciones
./scripts/bench_backends.sh 100000   # menos vueltas, para una comprobación rápida
```

Compila el mismo programa con los dos backends, mide el mínimo de cinco
ejecuciones e imprime el factor entre JavaScript y C++. Los números de
referencia están en [`docs/javascript.md`](../docs/javascript.md).

## Empaquetar e instalar la extensión

```sh
./scripts/vsix.sh                 # empaqueta e instala con el CLI `code`
./scripts/vsix.sh --package-only  # solo genera dist/penguscript-0.1.0.vsix
```

```powershell
powershell -ExecutionPolicy Bypass -File scripts\vsix.ps1 -PackageOnly
```

La extensión necesita `pengu` en el PATH (o configurar `pengu.executable` en los
ajustes de VS Code). El script no instala VS Code: si no encuentra `code`,
`code-insiders` ni `codium`, deja el `.vsix` listo y explica cómo instalarlo a mano.
