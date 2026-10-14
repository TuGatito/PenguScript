/**
 * Deterministic checks for vscode-extension/src/penguPath.ts.
 *
 * Run as: node pengu_path_check.js <compiled-dir>
 * Exits non-zero and prints "FAIL ..." lines when an expectation does not hold.
 */
'use strict';

const path = require('path');
const mod = require(path.join(process.argv[2], 'penguPath.js'));

let failures = 0;
function check(name, actual, expected) {
    const a = JSON.stringify(actual);
    const e = JSON.stringify(expected);
    if (a !== e) {
        failures += 1;
        console.log(`FAIL ${name}\n  expected ${e}\n  actual   ${a}`);
    } else {
        console.log(`ok   ${name} -> ${a}`);
    }
}

/** Builds an isFile predicate over a synthetic filesystem. */
function fsOf(files) {
    const set = new Set(files);
    return (candidate) => set.has(candidate);
}

// The environment the bug was reported in: a VS Code launched from the desktop
// session, whose PATH (systemd's) has no `pengu`, while the release sits in
// ~/pengu/.
const SYSTEMD_PATH = '/usr/local/sbin:/usr/local/bin:/usr/bin:/usr/lib/emscripten';
const HOME = '/home/u';

check(
    'user case: ~/pengu/pengu is found when PATH has none',
    mod.resolvePenguCommand({
        homeDir: HOME,
        platform: 'linux',
        pathValue: SYSTEMD_PATH,
        workspaceFolders: [],
        isFile: fsOf([`${HOME}/pengu/pengu`])
    }),
    { command: `${HOME}/pengu/pengu`, source: 'well-known location' }
);

check(
    'workspace .venv/bin/pengu is preferred over ~/pengu/pengu',
    mod.resolvePenguCommand({
        homeDir: HOME,
        platform: 'linux',
        pathValue: SYSTEMD_PATH,
        workspaceFolders: ['/work/proj'],
        isFile: fsOf([`${HOME}/pengu/pengu`, '/work/proj/.venv/bin/pengu'])
    }),
    { command: '/work/proj/.venv/bin/pengu', source: 'well-known location' }
);

check(
    'PATH wins over the well-known locations',
    mod.resolvePenguCommand({
        homeDir: HOME,
        platform: 'linux',
        pathValue: `/opt/bin:${SYSTEMD_PATH}`,
        workspaceFolders: [],
        isFile: fsOf([`${HOME}/pengu/pengu`, '/opt/bin/pengu'])
    }),
    { command: '/opt/bin/pengu', source: 'PATH' }
);

check(
    'the setting wins and expands ~',
    mod.resolvePenguCommand({
        configuredPath: '~/pengu/pengu',
        homeDir: HOME,
        platform: 'linux',
        pathValue: '/opt/bin',
        isFile: fsOf(['/opt/bin/pengu'])
    }),
    { command: `${HOME}/pengu/pengu`, source: 'pengus.executablePath' }
);

check(
    '$PENGU_BIN_PATH wins over PATH',
    mod.resolvePenguCommand({
        envPath: '/custom/pengu',
        homeDir: HOME,
        platform: 'linux',
        pathValue: '/opt/bin',
        isFile: fsOf(['/opt/bin/pengu'])
    }),
    { command: '/custom/pengu', source: 'PENGU_BIN_PATH' }
);

check(
    'a blank setting is ignored',
    mod.resolvePenguCommand({
        configuredPath: '   ',
        homeDir: HOME,
        platform: 'linux',
        pathValue: SYSTEMD_PATH,
        isFile: fsOf([`${HOME}/.local/bin/pengu`])
    }),
    { command: `${HOME}/.local/bin/pengu`, source: 'well-known location' }
);

check(
    'Windows: PATHEXT is honoured',
    mod.resolvePenguCommand({
        homeDir: 'C:\\Users\\u',
        platform: 'win32',
        pathValue: 'C:\\tools',
        pathExt: '.EXE;.CMD',
        isFile: fsOf(['C:\\tools\\pengu.EXE'])
    }),
    { command: 'C:\\tools\\pengu.EXE', source: 'PATH' }
);

check(
    'nothing anywhere yields undefined (the caller then explains why)',
    mod.resolvePenguCommand({
        homeDir: HOME,
        platform: 'linux',
        pathValue: SYSTEMD_PATH,
        workspaceFolders: ['/work/proj'],
        isFile: fsOf([])
    }),
    undefined
);

console.log(failures === 0 ? 'ALL OK' : `${failures} FAILURE(S)`);
process.exit(failures === 0 ? 0 : 1);
