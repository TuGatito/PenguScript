# Stage0 bootstrap

`psc_stage0_<os>_<arch>.c` are C11 bundles emitted by a working native `psc`
from the current compiler sources, one per CI platform. Do not edit them by
hand.

- Regenerate after compiler/std changes: `./tools/gen_stage0.sh`
- Verify the committed bundles are current: `./tools/gen_stage0.sh --check`
- Build the host bundle with only a C compiler: `./tools/build_bootstrap.sh`
  (produces `build/psc-stage0`)

CI uses these bundles because the latest published release still ships the
legacy `pengu` compiler, which is too slow to compile this tree.
