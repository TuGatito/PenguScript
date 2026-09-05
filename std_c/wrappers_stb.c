/* std_c/wrappers_stb.c
 * Compiles the implementation units of every single-header library shipped in
 * std_c/ into the static library libpengu_stb.a. PenguScript programs that
 * import std.imago / std.scriptor / std.typis / std.pactum / std.datastructura /
 * std.perlinum / std.nanosvg / std.nanosvgrast therefore resolve the real C
 * symbols automatically.
 *
 * NOTE: each header below uses its original implementation macro even though
 * the files were renamed to Latin names (STB_IMAGE_IMPLEMENTATION, etc.).
 */

#define STB_IMAGE_IMPLEMENTATION
#include "imago.h"

#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "scriptor.h"

/* stb_truetype (typis.h) only uses its built-in rectangle-packing fallback
 * when stb_rect_pack.h was NOT included first (guarded by
 * STB_RECT_PACK_VERSION), so pactum.h must precede typis.h. */
#define STB_RECT_PACK_IMPLEMENTATION
#include "pactum.h"

#define STB_TRUETYPE_IMPLEMENTATION
#include "typis.h"

#define STB_DS_IMPLEMENTATION
#include "datastructura.h"

#define STB_PERLIN_IMPLEMENTATION
#include "perlinum.h"

#define NANOSVG_IMPLEMENTATION
#include "nanosvg.h"

#define NANOSVGRAST_IMPLEMENTATION
#include "nanosvgrast.h"
