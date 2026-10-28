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
