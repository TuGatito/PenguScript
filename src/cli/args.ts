export interface ParsedArgs {
  readonly command: string;
  readonly positionals: readonly string[];
  readonly flags: Readonly<Record<string, string | true>>;
  readonly passthrough: readonly string[];
}

// Flags que esperan un valor en el argumento siguiente (`--out ruta`).
const VALUE_FLAGS = new Set(["out", "realm", "link", "clang", "lib", "entry", "target", "type", "compiler"]);

export function parse_args(argv: readonly string[]): ParsedArgs {
  const positionals: string[] = [];
  const flags: Record<string, string | true> = {};
  const passthrough: string[] = [];
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
        if (next !== undefined && !next.startsWith("-")) {
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

  return { command, positionals, flags, passthrough };
}

export function flag_string(args: ParsedArgs, name: string): string | undefined {
  const value = args.flags[name];
  return typeof value === "string" ? value : undefined;
}

export function flag_bool(args: ParsedArgs, name: string): boolean {
  return args.flags[name] === true || args.flags[name] === "true";
}
