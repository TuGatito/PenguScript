/* std_c/wrappers_minicoro.c
 * Compiles the minicoro implementation unit (minicoro.h) into its own
 * object file inside libpengu_stb.a, so PenguScript programs that import
 * std.minicoro resolve the real C symbols (mco_create/mco_resume/mco_yield/
 * mco_status/mco_destroy/mco_running/...) automatically.
 *
 * The implementation macro is MINICORO_IMPL (not MINICORO_IMPLEMENTATION).
 * On Win64 + GCC, minicoro picks its assembly context-switch backend
 * (MCO_USE_ASM); no extra platform libraries are needed.
 */
#define MINICORO_IMPL
#include "minicoro.h"

/* ---- PenguScript-friendly shim -----------------------------------------
 * minicoro's mco_create needs a fully-populated mco_desc (function pointer,
 * user data, stack size). These helpers let a PenguScript weave act as the
 * coroutine body: C invokes the weave (mco calls it), and the weave can call
 * pengu_mco_yield to suspend. 'co' is exposed as ref to void on the Pengu side.
 */
typedef void (*pengu_coro_body)(void *co);

void *pengu_mco_start(pengu_coro_body body, void *user_data, size_t stack_size)
{
  if (!body)
    return NULL;
  mco_desc desc = mco_desc_init((void (*)(mco_coro *))body, stack_size);
  desc.user_data = user_data;
  mco_coro *co = NULL;
  if (mco_create(&co, &desc) != MCO_SUCCESS)
    return NULL;
  return (void *)co;
}

void pengu_mco_resume(void *co)
{
  if (co)
    mco_resume((mco_coro *)co);
}

void pengu_mco_yield(void *co)
{
  if (co)
    mco_yield((mco_coro *)co);
}

int pengu_mco_status(void *co)
{
  if (!co)
    return -1;
  return (int)mco_status((mco_coro *)co);
}

void pengu_mco_destroy(void *co)
{
  if (co)
  {
    mco_destroy((mco_coro *)co);
    co = NULL;
  }
}

