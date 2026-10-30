/**
 * Locating the `psc` executable for the VS Code extension.
 *
 * Deliberately free of the `vscode` module: `extension.ts` passes the workspace
 * folders in, so this search can be exercised with plain Node (see
 * `test/psc_path_check.js`).
 *
 * It exists because a VS Code started from the desktop does not inherit the
 * `PATH` a login shell builds — on Linux the session's own `PATH` comes from
 * systemd (`systemctl --user show-environment`), so a `psc` exported from
 * `~/.bashrc` is invisible to the editor and the language client used to die
 * with a bare `spawn psc ENOENT`.
 */
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';

/** A located `psc` executable plus the rule that found it. */
export interface PscCommand {
    command: string;
    /** Where the path came from; logged so a wrong pick is diagnosable. */
    source: string;
}

/** Every input the search reads, so a test can pin all of them. */
export interface ResolvePscOptions {
    /** `pengus.executablePath`, when the user set one. */
    configuredPath?: string;
    /** `$PSC_BIN_PATH` (or legacy `$PENGU_BIN_PATH`), when set. */
    envPath?: string;
    /** `$PENGU_PSC`, written by `tools/build.sh` / `tools/build.ps1`. */
    penguPsc?: string;
    /** `$PENGU_HOME`, the compiler checkout or install prefix. */
    penguHome?: string;
    /** Explicit `pengu.env.json`; defaults to the per-user config file. */
    envFile?: string;
    /** File-system paths of the workspace folders, in order. */
    workspaceFolders?: string[];
    /** Directory treated as `~`; defaults to `os.homedir()`. */
    homeDir?: string;
    /** `process.platform`; defaults to the running platform. */
    platform?: NodeJS.Platform;
    /** `$PATH`; defaults to `process.env.PATH`. */
    pathValue?: string;
    /** `$PATHEXT` (Windows); defaults to `process.env.PATHEXT`. */
    pathExt?: string;
    /** File predicate, injectable for tests; defaults to `fs.statSync`. */
    isFile?: (candidate: string) => boolean;
}

export function isFile(candidate: string): boolean {
    try {
        return fs.statSync(candidate).isFile();
    } catch {
        return false;
    }
}

/** True for a regular file that can be executed on this platform. */
export function isExecutable(candidate: string): boolean {
    if (!isFile(candidate)) {
        return false;
    }
    if (process.platform === 'win32') {
        return true;
    }
    try {
        fs.accessSync(candidate, fs.constants.X_OK);
        return true;
    } catch {
        return false;
    }
}

/** True when `value` is a name, not a path. */
function isBareName(value: string): boolean {
    return !value.includes('/') && !value.includes('\\');
}

/** Expands a leading `~`: the shell does it for a terminal, VS Code does not. */
export function expandHome(target: string, homeDir: string): string {
    if (target === '~') {
        return homeDir;
    }
    if (target.startsWith('~/') || target.startsWith('~\\')) {
        return path.join(homeDir, target.slice(2));
    }
    return target;
}

/** Searches `PATH` for `name`, honouring `PATHEXT` on Windows. */
export function findOnPath(
    name: string,
    pathValue: string,
    platform: NodeJS.Platform,
    pathExt: string,
    isFile: (candidate: string) => boolean
): string | undefined {
    // The flavour follows the *target* platform, not the host: that is what
    // makes the Windows branch exercisable from a Linux test run.
    const flavour = platform === 'win32' ? path.win32 : path.posix;
    const dirs = pathValue.split(flavour.delimiter).filter(Boolean);
    const extensions = platform === 'win32'
        ? pathExt.split(';').filter(Boolean)
        : [''];
    for (const dir of dirs) {
        for (const extension of extensions) {
            const candidate = flavour.join(dir, name + extension);
            if (isFile(candidate)) {
                return candidate;
            }
        }
    }
    return undefined;
}

/** The persistent, shell-independent toolchain description written by the build. */
export interface PenguEnv {
    schema?: number;
    version?: string;
    home?: string;
    psc?: string;
    std?: string;
    include?: string;
    lib?: string;
    wasm?: string;
    bind?: string;
    path?: string[];
}

/** Default per-user env file, matching tools/build.{sh,ps1}. */
export function defaultEnvFile(
    homeDir: string,
    platform: NodeJS.Platform = process.platform,
    env: NodeJS.ProcessEnv = process.env
): string {
    if (platform === 'win32') {
        const base = env.LOCALAPPDATA || path.win32.join(homeDir, '.config');
        return path.win32.join(base, 'pengu', 'env.json');
    }
    const base = env.XDG_CONFIG_HOME || path.posix.join(homeDir, '.config');
    return path.posix.join(base, 'pengu', 'env.json');
}

/** Reads and minimally validates a `pengu.env.json`; never throws. */
export function readPenguEnv(file: string): PenguEnv | undefined {
    try {
        const text = fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, '');
        const raw = JSON.parse(text) as unknown;
        if (!raw || typeof raw !== 'object') {
            return undefined;
        }
        const obj = raw as Record<string, unknown>;
        const out: PenguEnv = { schema: typeof obj.schema === 'number' ? obj.schema : undefined };
        const strings: (keyof PenguEnv)[] = ['version', 'home', 'psc', 'std', 'include', 'lib', 'wasm', 'bind'];
        for (const key of strings) {
            const value = obj[key];
            if (typeof value === 'string' && value.length > 0) {
                (out as Record<string, unknown>)[key] = value;
            }
        }
        if (Array.isArray(obj.path) && obj.path.every((item) => typeof item === 'string')) {
            out.path = obj.path as string[];
        }
        return out.psc || out.home ? out : undefined;
    } catch {
        return undefined;
    }
}

/**
 * Well-known places a release is unpacked into.
 *
 * `docs/README_RELEASE.md` documents extracting the archive into a directory
 * and running `./bin/psc` (or `./install.sh`, which defaults to `~/.local`), so
 * the workspace and the home directory are searched before giving up.
 */
export function candidateExecutables(options: ResolvePscOptions): string[] {
    const platform = options.platform ?? process.platform;
    const exists = options.isFile ?? isFile;
    const home = options.homeDir ?? os.homedir();
    const exe = platform === 'win32' ? 'psc.exe' : 'psc';
    const join = (platform === 'win32' ? path.win32 : path.posix).join;
    const candidates: string[] = [];

    for (const root of options.workspaceFolders ?? []) {
        candidates.push(
            join(root, exe),
            join(root, 'bin', exe),
            join(root, 'dist', exe),
            join(root, 'build', exe)
        );
    }

    candidates.push(
        join(home, 'psc', exe),
        join(home, 'pengu', exe),
        join(home, '.local', 'bin', exe),
        join(home, 'bin', exe)
    );
    if (platform === 'win32') {
        candidates.push(join(home, 'AppData', 'Local', 'Programs', 'PenguScript', exe));
    } else {
        candidates.push('/usr/local/bin/psc', '/usr/bin/psc', '/opt/psc/psc', '/opt/pengu/psc');
    }

    return candidates.filter(exists);
}

/**
 * Locates the `psc` executable.
 *
 * Order: the `pengus.executablePath` setting, then `$PSC_BIN_PATH` (legacy
 * `$PENGU_BIN_PATH`), then `PATH`, then the well-known locations. Returns
 * `undefined` when nothing is found, which the caller turns into an actionable
 * message instead of a bare `spawn ENOENT`.
 */
export function resolvePscCommand(options: ResolvePscOptions = {}): PscCommand | undefined {
    const platform = options.platform ?? process.platform;
    const home = options.homeDir ?? os.homedir();
    const exists = options.isFile ?? isFile;
    const pathValue = options.pathValue ?? process.env.PATH ?? '';
    const pathExt = options.pathExt ?? process.env.PATHEXT ?? '.EXE;.CMD;.BAT';

    const seek = (value: string, source: string): PscCommand => {
        if (isBareName(value)) {
            const hit = findOnPath(value, pathValue, platform, pathExt, exists);
            if (hit) {
                return { command: hit, source: `${source} (PATH)` };
            }
        }
        return { command: expandHome(value, home), source };
    };

    // A stale setting (for example a removed `~/pengu/bin/psc`) must not
    // disable the extension: try the remaining sources and let the caller log
    // that the explicit path was skipped.
    const configured = options.configuredPath?.trim();
    if (configured) {
        const hit = seek(configured, 'pengus.executablePath');
        if (exists(hit.command)) {
            return hit;
        }
    }

    const penguPsc = options.penguPsc?.trim();
    if (penguPsc) {
        const hit = seek(penguPsc, 'PENGU_PSC');
        if (exists(hit.command)) {
            return hit;
        }
    }

    const fromEnv = options.envPath?.trim();
    if (fromEnv) {
        const hit = seek(fromEnv, 'PSC_BIN_PATH');
        if (exists(hit.command)) {
            return hit;
        }
    }

    const envFile = options.envFile ?? defaultEnvFile(home, platform);
    const env = readPenguEnv(envFile);
    if (env?.psc) {
        const command = expandHome(env.psc, home);
        if (exists(command)) {
            return { command, source: `env.json (${envFile})` };
        }
    }

    const homeRoot = env?.home ?? options.penguHome;
    if (homeRoot) {
        const join = platform === 'win32' ? path.win32.join : path.posix.join;
        const exe = platform === 'win32' ? 'psc.exe' : 'psc';
        const candidate = join(homeRoot, 'build', exe);
        if (exists(candidate)) {
            return { command: candidate, source: 'PENGU_HOME/build' };
        }
    }

    const bare = 'psc';
    const onPath = findOnPath(
        bare,
        pathValue,
        platform,
        pathExt,
        exists
    );
    if (onPath) {
        return { command: onPath, source: 'PATH' };
    }

    const [candidate] = candidateExecutables({ ...options, platform, homeDir: home, isFile: exists });
    if (candidate) {
        return { command: candidate, source: 'well-known location' };
    }

    return undefined;
}
