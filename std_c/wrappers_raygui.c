/* std_c/wrappers_raygui.c
 * Compiles the raygui implementation unit (raygui.h) into its own object
 * file inside libpengu_stb.a. raygui is header-only behind
 * RAYGUI_IMPLEMENTATION and is implemented in terms of the raylib API, so
 * this TU includes <raylib.h> first (raylib.h is staged in build/include by
 * build_runtime.build_raylib). The object only references raylib symbols, so
 * it is pulled from the archive only when a program actually calls a raygui
 * function, and such a program must also link -lraylib (and the platform GL
 * libraries) - the same requirement as using raylib itself.
 */
#define RAYGUI_STATIC
#define RAYGUI_IMPLEMENTATION
#include "raylib.h"
#include "raygui.h"
