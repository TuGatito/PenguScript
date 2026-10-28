# Third-party components

PenguScript is MIT-licensed (see [LICENSE](LICENSE)). The following third-party
components are vendored in this repository and keep their original licenses.

## SDS — Simple Dynamic Strings

- **Location:** [`std_c/sds/`](std_c/sds/)
- **Version:** SDS 2.x (the stand-alone Redis SDS distribution)
- **License:** BSD-2-Clause. Full text in
  [`std_c/sds/LICENSE`](std_c/sds/LICENSE); release packages also ship it as
  `share/doc/pengu/SDS_LICENSE`.
- **Authors / credits:** Salvatore Sanfilippo (`antirez`), Oran Agra and the
  Redis Labs / Redis community.
- **Usage:** the C runtime (`pengu_runtime.h`) uses SDS as the allocation
  backend of every owned `PenguString`. `std_c/sds/sds.c` is compiled into
  `libpengu_runtime.a`; `std_c/sds/sds.h` is installed next to
  `pengu_runtime.h`.

Thank you to the SDS authors and the Redis community for building a small,
battle-tested, permissively licensed string library and for making it available
to the rest of the C ecosystem.

## CC — Convenient Containers

- **Location:** [`std_c/CC-main/`](std_c/CC-main/)
- **Version:** CC v1.4.3 (single header)
- **License:** MIT. Full text in [`std_c/CC-main/LICENSE`](std_c/CC-main/LICENSE);
  release packages also ship it as `share/doc/pengu/CC_LICENSE`.
- **Author / credits:** Jackson L. Allan and the CC contributors.
- **Usage:** `runtime/pengu_containers.c` and `runtime/pengu_cc_extra.c` include
  `cc.h` with `CC_NO_SHORT_NAMES`. CC `vec` backs `list`, CC `map` backs
  `map`, and CC `list`/`set`/`oset`/`omap` back the new `std.ordinal` types.

Thank you to Jackson L. Allan for building CC and releasing it under the MIT
license; its type-erased internals let PenguScript keep its stable runtime
container ABI while replacing the hand-written storage.
