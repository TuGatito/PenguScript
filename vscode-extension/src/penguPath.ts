/**
 * Locating the `pengu` executable for the VS Code extension.
 *
 * Deliberately free of the `vscode` module: `extension.ts` passes the workspace
 * folders in, so this search can be exercised with plain Node (see
 * `tests/lsp/test_vscode_pengu_path.py`).
 *
 * It exists because a VS Code started from the desktop does not inherit the
 * `PATH` a login shell builds — on Linux the session's own `PATH` comes from
 * systemd (`systemctl --user show-environment`), so a `pengu` exported from
 * `~/.bashrc` is invisible to the editor and the language client used to die
 * with a bare `spawn pengu ENOENT`.
 */
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';

/** A located `pengu` executable plus the rule that found it. */
export interface PenguCommand {
    command: string;
    /** Where the path came from; logged so a wrong pick is diagnosable. */
    source: string;
}

/** Every input the search reads, so a test can pin all of them. */
export interface ResolvePenguOptions {
    /** `pengus.executablePath`, when the user set one. */
    configuredPath?: string;
    /** `$PENGU_BIN_PATH`, when set. */
    envPath?: string;
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

/**
 * Well-known places a release is unpacked into.
 *
 * `docs/README_RELEASE.md` documents extracting the archive into a directory
 * and running `./pengu` (or `./install.sh`, which defaults to `~/.local`), so
 * the workspace and the home directory are searched before giving up.
 */
export function candidateExecutables(options: ResolvePenguOptions): string[] {
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
            join(root, 'dist2', exe),
            join(root, 'build', exe)
        );
    }

    candidates.push(
        join(home, 'pengu', exe),
        join(home, '.local', 'bin', exe),
        join(home, 'bin', exe)
    );
    if (platform === 'win32') {
        candidates.push(join(home, 'AppData', 'Local', 'Programs', 'pengu', exe));
    } else {
        candidates.push('/usr/local/bin/psc', '/usr/bin/psc', '/opt/pengu/psc');
    }

    return candidates.filter(exists);
}

/**
 * Locates the `pengu` executable.
 *
 * Order: the `pengus.executablePath` setting, then `$PENGU_BIN_PATH`, then
 * `PATH`, then the well-known locations. Returns `undefined` when nothing is
 * found, which the caller turns into an actionable message instead of a bare
 * `spawn ENOENT`.
 */
export function resolvePenguCommand(options: ResolvePenguOptions = {}): PenguCommand | undefined {
    const platform = options.platform ?? process.platform;
    const home = options.homeDir ?? os.homedir();
    const exists = options.isFile ?? isFile;

    const configured = options.configuredPath?.trim();
    if (configured) {
        return { command: expandHome(configured, home), source: 'pengus.executablePath' };
    }

    const fromEnv = options.envPath?.trim();
    if (fromEnv) {
        return { command: expandHome(fromEnv, home), source: 'PENGU_BIN_PATH' };
    }

    const bare = 'psc';
    const onPath = findOnPath(
        bare,
        options.pathValue ?? process.env.PATH ?? '',
        platform,
        options.pathExt ?? process.env.PATHEXT ?? '.EXE;.CMD;.BAT',
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
