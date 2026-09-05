/* std_c/pengu_tomlc17.h
 * Companion header for std_c/wrappers_tomlc17.c: prototypes of the
 * PenguScript-friendly tomlc17 shim functions. Staged to build/include/ by
 * build_runtime.build_tomlc17() so `include "pengu_tomlc17.h"` resolves in
 * project builds (std/tomlum.d.pengu includes it).
 */
#ifndef PENGU_TOMLC17_H
#define PENGU_TOMLC17_H

#ifdef __cplusplus
extern "C" {
#endif

/* Returns 1 when `text` parses as a valid TOML document, 0 otherwise. */
int pengu_toml_valid(const char *text);

/* Returns 1 when the file at `fname` parses as a valid TOML document,
 * 0 otherwise (unreadable file or parse error). */
int pengu_toml_valid_file(const char *fname);

#ifdef __cplusplus
}
#endif

#endif /* PENGU_TOMLC17_H */
