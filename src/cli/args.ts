export interface ParsedArgs {
  readonly command: string;
  readonly positionals: readonly string[];
  readonly flags: Readonly<Record<string, string | true>>;
  readonly passthrough: readonly string[];
  /** Directorios de `-I` (bindgen los pasa a clang). */
  readonly include_dirs: readonly string[];
}

// Flags que esperan un valor en el argumento siguiente (`--out ruta`).
const VALUE_FLAGS = new Set(["out", "realm", "link", "clang", "lib", "entry", "target", "type", "compiler", "base", "base-realm", "base-module"]);

// Estos flags aceptan valores que empiezan por `-` (`--link -lraylib`).
const DASHED_VALUE_FLAGS = new Set(["link", "lib"]);

export function parse_args(argv: readonly string[]): ParsedArgs {
  const positionals: string[] = [];
  const flags: Record<string, string | true> = {};
  const passthrough: string[] = [];
  const include_dirs: string[] = [];
  let command = "";

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === undefined) break;
    if (arg === "--") {
      passthrough.push(...argv.slice(index + 1));
      break;
    }
    if (arg.startsWith("--")) {
      const body = arg.slice(2);
      const equals = body.indexOf("=");
      if (equals >= 0) {
        flags[body.slice(0, equals)] = body.slice(equals + 1);
      } else if (VALUE_FLAGS.has(body)) {
        const next = argv[index + 1];
        const dashed = DASHED_VALUE_FLAGS.has(body);
        if (next !== undefined && (dashed ? !next.startsWith("--") : !next.startsWith("-"))) {
          flags[body] = next;
          index += 1;
        } else {
          flags[body] = true;
        }
      } else {
        flags[body] = true;
      }
      continue;
    }
    if (arg === "-I" || arg.startsWith("-I")) {
      const attached = arg.slice(2);
      if (attached.length > 0) {
        include_dirs.push(attached);
      } else {
        const next = argv[index + 1];
        if (next !== undefined) {
          include_dirs.push(next);
          index += 1;
        }
      }
      continue;
    }
    if (arg.startsWith("-") && arg.length > 1) {
      flags[arg.slice(1)] = true;
      continue;
    }
    if (command === "") {
      command = arg;
      continue;
    }
    positionals.push(arg);
  }

  return { command, positionals, flags, passthrough, include_dirs };
}

export function flag_string(args: ParsedArgs, name: string): string | undefined {
  const value = args.flags[name];
  return typeof value === "string" ? value : undefined;
}

export function flag_bool(args: ParsedArgs, name: string): boolean {
  return args.flags[name] === true || args.flags[name] === "true";
}
