#!/usr/bin/env python3
"""The fake `pengu` binary used by tests/tooling/test_release_verify.py.

It emulates exactly the four commands `scripts/verify_release_artifact.py`
executes, including the *layout discovery* the FHS gate depends on: `build`
fails unless `libpengu_runtime.a` is reachable from the executable's own
location, which is what makes the negative control meaningful.

Written by the test into a temporary release archive; never shipped.
"""

import sys
from pathlib import Path

VERSION = "1.2.3"


def main(argv):
    exe_dir = Path(__file__).resolve().parent
    args = argv[1:]
    if not args:
        return 2
    command = args[0]

    if command == "-V":
        print(f"pengu {VERSION}")
        return 0

    if command == "new":
        # `pengu new exe <name>`
        name = args[-1]
        project = Path.cwd() / name
        (project / "src").mkdir(parents=True, exist_ok=True)
        (project / "src" / "main.pengu").write_text("", encoding="utf-8")
        print(f"Created exe project '{name}'")
        return 0

    if command == "build":
        # The two layouts the release actually produces:
        #   portable: <dir>/runtime/libpengu_runtime.a
        #   fhs:      <prefix>/bin/pengu + <prefix>/lib/pengu/libpengu_runtime.a
        candidates = [
            exe_dir / "runtime" / "libpengu_runtime.a",
            exe_dir.parent / "lib" / "pengu" / "libpengu_runtime.a",
        ]
        if not any(c.is_file() for c in candidates):
            print(
                "Error:\nlibpengu_runtime.a not found.\n  Searched:\n"
                + "\n".join(f"    {c}" for c in candidates),
                file=sys.stderr,
            )
            return 1
        print("Finished [debug] target(s)")
        return 0

    if command == "run":
        print("Hello, world!")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
