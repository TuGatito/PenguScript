# Stage0 bootstrap

`psc_stage0.c` is generated C11 emitted by a working native `psc` from the
current compiler sources. Do not edit it by hand.

- Regenerate after compiler/std changes: `./tools/gen_stage0.sh`
- Verify the committed bundle is current: `./tools/gen_stage0.sh --check`
- Build it with only a C compiler: `./tools/build_bootstrap.sh`
  (produces `build/psc-stage0`)

CI uses this bundle because the latest published release still ships the
legacy `pengu` compiler, which is too slow to compile this tree.
