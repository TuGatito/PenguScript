/* std_c/wrappers_tomlc17.c
 * PenguScript-friendly shim over the tomlc17 TOML parser (libtomlc17.a).
 *
 * tomlc17's core API returns the toml_result_t struct BY VALUE and exposes
 * the parsed document as a toml_datum_t tree (also by value/pointers into
 * the result) - none of which pure PenguScript can express today (no by-value
 * opaque structs, no out-buffers). These helpers give PenguScript the small,
 * real, verifiable surface of the parser: "is this text / this file a valid
 * TOML document?". Anything deeper (querying keys/values) stays C-level.
 *
 * Compiled into build/lib/libtomlc17.a by build_runtime.build_tomlc17()
 * (alongside the upstream tomlc17.o); prototypes live in pengu_tomlc17.h,
 * which is staged to build/include/ so `include "pengu_tomlc17.h"` resolves
 * in project builds.
 */
#include <stddef.h>
#include <string.h>
#include "tomlc17.h"

/* Returns 1 when `text` parses as a valid TOML document, 0 otherwise
 * (including a NULL pointer). The parsed result is freed before returning. */
int pengu_toml_valid(const char *text)
{
  if (!text)
    return 0;
  toml_result_t r = toml_parse(text, (int)strlen(text));
  int ok = r.ok ? 1 : 0;
  toml_free(r);
  return ok;
}

/* Returns 1 when the file at `fname` parses as a valid TOML document,
 * 0 otherwise (unreadable file or parse error). */
int pengu_toml_valid_file(const char *fname)
{
  if (!fname)
    return 0;
  toml_result_t r = toml_parse_file_ex(fname);
  int ok = r.ok ? 1 : 0;
  toml_free(r);
  return ok;
}
