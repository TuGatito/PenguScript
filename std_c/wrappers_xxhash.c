/* std_c/wrappers_xxhash.c
 * Compiles the xxHash implementation unit (xxhash.h) into its own object
 * file inside libpengu_stb.a, so PenguScript programs that import
 * std.xxhash resolve the real C symbols (XXH32/XXH64/XXH3_*...) automatically.
 *
 * NOTE: this vendored xxhash.h keeps its internal static declarations
 * (struct XXH32_state_s / XXH64_state_s / XXH3_state_s, XXH_ALIGN,
 * XXH3_kSecret, ...) guarded by XXH_STATIC_LINKING_ONLY, and the out-of-line
 * implementation bodies reference those declarations, so BOTH macros must be
 * defined in this translation unit.
 */
#define XXH_STATIC_LINKING_ONLY
#define XXH_IMPLEMENTATION
#include "xxhash.h"
