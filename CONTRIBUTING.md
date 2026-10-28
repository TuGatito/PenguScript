# Contributing to PenguScript

PenguScript is built with its own compiler (`psc`). Python is not required to
build, test, or run the project.

## Build

```bash
# Download a PSC bootstrap release for your platform and export PENGU_HOME/PATH.
./tools/build_runtime.sh
psc build .
./build/psc version
```

## Tests

```bash
./tests/run.sh          # Linux/macOS
./tests/run.ps1         # Windows
```

## Code style

```bash
psc fmt --check src std
```

## Pull requests

- Keep changes focused.
- Add or update tests under `tests/`.
- Run the compiler and test suite before opening the PR.
- Do not add Python to the compiler or its runtime.

## License

By contributing you agree that your changes are licensed under the MIT License.
