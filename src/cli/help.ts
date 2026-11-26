import { TOOL_NAME, VERSION } from "../version.ts";

export const COMMANDS = [
  "build",
  "run",
  "check",
  "fmt",
  "lsp",
  "bindgen",
  "ts-bindgen",
  "size",
  "init",
  "doctor",
  "clean",
] as const;

export type CommandName = (typeof COMMANDS)[number];

export function is_command(name: string): name is CommandName {
  return (COMMANDS as readonly string[]).includes(name);
}

export function main_help(): string {
  return [
    `${TOOL_NAME} ${VERSION} — compilador de PenguScript`,
    "",
    "Uso:",
    `  ${TOOL_NAME} <comando> [opciones] [archivo|directorio]`,
    "",
    "Comandos:",
    "  build     Compila a un binario nativo (cpp) o a módulos JS (js).",
    "  run       Compila (con caché) y ejecuta un programa.",
    "  check     Analiza sin generar código; reporta diagnósticos.",
    "  fmt       Formatea archivos .pengu.",
    "  lsp       Inicia el servidor de lenguaje (JSON-RPC por stdio).",
    "  bindgen   Genera declaraciones .d.pengu desde cabeceras C/C++.",
    "  size      Mide tamaños y alineación reales de los tipos del proyecto.",
    "  init      Crea un proyecto nuevo con pengu.toml y src/main.pengu.",
    "  doctor    Muestra el toolchain y la stdlib que usa el compilador.",
    "  clean     Borra la caché de compilación.",
    "",
    "Opciones globales:",
    "  --version  Muestra la versión.",
    "  --help     Muestra esta ayuda.",
    "",
    "Ejemplos:",
    `  ${TOOL_NAME} run examples/01_hello/hello.pengu`,
    `  ${TOOL_NAME} check examples/03_runes`,
    `  ${TOOL_NAME} fmt --check src/`,
  ].join("\n");
}

const COMMAND_HELP: Readonly<Record<CommandName, string>> = {
  build: [
    `Uso: ${TOOL_NAME} build [archivo|dir] [opciones]`,
    "",
    "  --target <cpp|js>  Backend de salida (por defecto cpp).",
    "  --out, -o <ruta>   Binario de salida (cpp) o directorio de módulos (js).",
    "  --release          Optimiza (-O2) y oculta símbolos.",
    "  --emit-cpp         Conserva los .hpp/.cpp generados junto al fuente.",
    "  --cxx <compilador> g++ (por defecto) o clang++.",
    "  --link <lib|obj>   Enlaza con una biblioteca (`raylib` → `-lraylib`) u objeto.",
    "  --int64 <bigint|number>  Enteros de 64 bits en JS (por defecto bigint).",
    "  --jsdoc            Añade comentarios JSDoc al código JS generado.",
  ].join("\n"),
  run: [
    `Uso: ${TOOL_NAME} run <archivo.pengu> [-- args...]`,
    "",
    "  Compila con caché y ejecuta el programa.",
    "  --target <cpp|js>  Backend de ejecución (por defecto cpp).",
    "  --release          Optimiza antes de ejecutar.",
    "  --link <lib|obj>   Enlaza con una biblioteca o un objeto.",
    "  --int64 <bigint|number>  Enteros de 64 bits en JS (por defecto bigint).",
  ].join("\n"),
  check: [
    `Uso: ${TOOL_NAME} check [archivo|dir] [opciones]`,
    "",
    "  --target <cpp|js>  Valida el programa para ese backend.",
    "  --json             Emite diagnósticos en JSON.",
    "  --strict           Trata warnings como errores.",
  ].join("\n"),
  fmt: [
    `Uso: ${TOOL_NAME} fmt [archivo|dir] [opciones]`,
    "",
    "  --check            No escribe; falla si hay diferencias.",
    "  --stdout           Imprime el resultado en vez de escribir.",
  ].join("\n"),
  lsp: [
    `Uso: ${TOOL_NAME} lsp [--stdio]`,
    "",
    "  Servidor de lenguaje. Habla JSON-RPC 2.0 por stdin/stdout.",
  ].join("\n"),
  size: [
    `Uso: ${TOOL_NAME} size [archivo.pengu] [opciones]`,
    "",
    "  --json             Emite la tabla en JSON.",
    "  --compiler <cxx>   Compilador con el que medir (g++ por defecto).",
    "  Solo mide el backend C++: en JS no hay tamaños ni alineación.",
  ].join("\n"),
  bindgen: [
    `Uso: ${TOOL_NAME} bindgen <cabecera.h> [opciones]`,
    "",
    "  -o, --out <ruta>   Archivo .d.pengu de salida.",
    "  --clang <ruta>     Ejecutable clang++ a usar.",
    "  --realm <nombre>   Realm de las declaraciones generadas.",
    "  -I <dir>           Directorio de includes (repetible).",
    "  --link <lib>       Solo informa de la orden de enlace (`-llib`).",
  ].join("\n"),
  "ts-bindgen": [
    `Uso: ${TOOL_NAME} ts-bindgen <archivo.d.ts> [opciones]`,
    "",
    "  --realm <nombre>   Realm de las declaraciones generadas.",
    "  -o, --out <ruta>   Archivo .d.pengu o directorio de salida.",
    "  --only <dominio>   Dominio del archivo (por defecto, el del nombre).",
    "  --check            Falla si el archivo generado no está al día.",
    "  --report           Informe de tipos, miembros y omisiones.",
    "  --json             Informe en JSON (implica --report).",
  ].join("\n"),
  init: [
    `Uso: ${TOOL_NAME} init [directorio]`,
    "",
    "  Crea pengu.toml, src/main.pengu y .gitignore.",
  ].join("\n"),
  doctor: [
    `Uso: ${TOOL_NAME} doctor [--json]`,
    "",
    "  Muestra bun, los compiladores de C++20 y la huella de la stdlib que",
    "  lleva el binario. Si el proyecto tiene su propio std/, avisa cuando no",
    "  coincide: reinstala el compilador para que CLI y LSP usen la misma.",
  ].join("\n"),
  clean: [
    `Uso: ${TOOL_NAME} clean`,
    "",
    "  Elimina .pengu-cache en el directorio actual.",
  ].join("\n"),
};

export function command_help(command: CommandName): string {
  return COMMAND_HELP[command];
}
