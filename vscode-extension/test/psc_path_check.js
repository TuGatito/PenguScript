/**
 * Deterministic checks for vscode-extension/src/pscPath.ts.
 *
 * Run as: node psc_path_check.js <compiled-dir>
 * Exits non-zero and prints "FAIL ..." lines when an expectation does not hold.
 */
'use strict';

const path = require('path');
const mod = require(path.join(process.argv[2], 'pscPath.js'));

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
// session, whose PATH (systemd's) has no `psc`, while the release sits in
// ~/psc/.
const SYSTEMD_PATH = '/usr/local/sbin:/usr/local/bin:/usr/bin:/usr/lib/emscripten';
const HOME = '/home/u';

check(
    'user case: ~/psc/psc is found when PATH has none',
    mod.resolvePscCommand({
        homeDir: HOME,
        platform: 'linux',
        pathValue: SYSTEMD_PATH,
        workspaceFolders: [],
        isFile: fsOf([`${HOME}/psc/psc`])
    }),
    { command: `${HOME}/psc/psc`, source: 'well-known location' }
);

check(
    'workspace bin/psc is preferred over ~/psc/psc',
    mod.resolvePscCommand({
        homeDir: HOME,
        platform: 'linux',
        pathValue: SYSTEMD_PATH,
        workspaceFolders: ['/work/proj'],
        isFile: fsOf([`${HOME}/psc/psc`, '/work/proj/bin/psc'])
    }),
    { command: '/work/proj/bin/psc', source: 'well-known location' }
);

check(
    'PATH wins over the well-known locations',
    mod.resolvePscCommand({
        homeDir: HOME,
        platform: 'linux',
        pathValue: `/opt/bin:${SYSTEMD_PATH}`,
        workspaceFolders: [],
        isFile: fsOf([`${HOME}/psc/psc`, '/opt/bin/psc'])
    }),
    { command: '/opt/bin/psc', source: 'PATH' }
);

check(
    'the setting wins and expands ~',
    mod.resolvePscCommand({
        configuredPath: '~/psc/psc',
        homeDir: HOME,
        platform: 'linux',
        pathValue: '/opt/bin',
        isFile: fsOf(['/opt/bin/psc'])
    }),
    { command: `${HOME}/psc/psc`, source: 'pengus.executablePath' }
);

check(
    '$PSC_BIN_PATH wins over PATH',
    mod.resolvePscCommand({
        envPath: '/custom/psc',
        homeDir: HOME,
        platform: 'linux',
        pathValue: '/opt/bin',
        isFile: fsOf(['/opt/bin/psc'])
    }),
    { command: '/custom/psc', source: 'PSC_BIN_PATH' }
);

check(
    'a blank setting is ignored',
    mod.resolvePscCommand({
        configuredPath: '   ',
        homeDir: HOME,
        platform: 'linux',
        pathValue: SYSTEMD_PATH,
        isFile: fsOf([`${HOME}/.local/bin/psc`])
    }),
    { command: `${HOME}/.local/bin/psc`, source: 'well-known location' }
);

check(
    'Windows: PATHEXT is honoured',
    mod.resolvePscCommand({
        homeDir: 'C:\\Users\\u',
        platform: 'win32',
        pathValue: 'C:\\tools',
        pathExt: '.EXE;.CMD',
        isFile: fsOf(['C:\\tools\\psc.EXE'])
    }),
    { command: 'C:\\tools\\psc.EXE', source: 'PATH' }
);

check(
    'nothing anywhere yields undefined (the caller then explains why)',
    mod.resolvePscCommand({
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
