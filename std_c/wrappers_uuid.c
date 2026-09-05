/* std_c/wrappers_uuid.c
 * Compiles the UUID implementation unit (uuid.h) into its own object file
 * inside libpengu_stb.a, so PenguScript programs that import std.uuid
 * resolve the real C symbols (uuid0_generate/uuid4_generate/uuid_type/
 * uuid_to_string/uuid_from_string/uuid_copy) automatically.
 *
 * std_c/uuid.h was patched to add a MinGW/_WIN32 branch for
 * uuid4_generate() that uses the BCrypt RNG (link with -lbcrypt); the
 * original upstream header only handled MSVC on Windows and would hit
 * `#error "unhandled platform"` under MinGW.
 */
#define UUID_IMPLEMENTATION
#include "uuid.h"
