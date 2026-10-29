/* Optional libffi/dlfcn bridge for std.ffi_call and std.dynlib. */
#include "pengu_runtime.h"

#if defined(__has_include)
#  if __has_include(<ffi.h>)
#    include <ffi.h>
#    define PENGU_HAVE_FFI 1
#  endif
#endif

#if PENGU_WINDOWS
#  include <windows.h>
#else
#  include <dlfcn.h>
#endif

#ifdef PENGU_HAVE_FFI

typedef struct
{
  ffi_cif cif;
  ffi_type *rtype;
  ffi_type **atypes;
  int nargs;
} PenguFfiSig;

static ffi_type *pengu_ffi_type(int code)
{
  switch (code)
  {
    case 0: return &ffi_type_void;
    case 1: return &ffi_type_sint8;
    case 2: return &ffi_type_uint8;
    case 3: return &ffi_type_sint16;
    case 4: return &ffi_type_uint16;
    case 5: return &ffi_type_sint32;
    case 6: return &ffi_type_uint32;
    case 7: return &ffi_type_sint64;
    case 8: return &ffi_type_uint64;
    case 9: return &ffi_type_float;
    case 10: return &ffi_type_double;
    case 11: return &ffi_type_pointer;
    case 12: return &ffi_type_pointer;
    case 13: return &ffi_type_uint8;
    default: return &ffi_type_pointer;
  }
}

void *ccx_ffi_sig_new(int ret, PenguList args)
{
  int n = args.len;
  if (n < 0 || n > 64 || !args.data)
    n = 0;
  PenguFfiSig *sig = (PenguFfiSig *)calloc(1, sizeof(*sig));
  if (!sig)
    return NULL;
  sig->nargs = n;
  sig->rtype = pengu_ffi_type(ret);
  sig->atypes = (ffi_type **)calloc((size_t)(n > 0 ? n : 1), sizeof(ffi_type *));
  if (!sig->atypes)
  {
    free(sig);
    return NULL;
  }
  for (int i = 0; i < n; i++)
  {
    int code = *(int *)((char *)args.data + (size_t)i * args.elem_size);
    sig->atypes[i] = pengu_ffi_type(code);
  }
  if (ffi_prep_cif(&sig->cif, FFI_DEFAULT_ABI, (unsigned)n, sig->rtype, sig->atypes) != FFI_OK)
  {
    free(sig->atypes);
    free(sig);
    return NULL;
  }
  return sig;
}

void ccx_ffi_sig_free(void *handle)
{
  PenguFfiSig *sig = (PenguFfiSig *)handle;
  if (!sig)
    return;
  free(sig->atypes);
  free(sig);
}

bool ccx_ffi_call(void *handle, void *fn, PenguList args, void *out)
{
  PenguFfiSig *sig = (PenguFfiSig *)handle;
  if (!sig || !fn || !out || args.len < sig->nargs)
    return false;
  void **argv = (void **)calloc((size_t)(sig->nargs > 0 ? sig->nargs : 1), sizeof(void *));
  if (!argv)
    return false;
  for (int i = 0; i < sig->nargs; i++)
    argv[i] = *(void **)((char *)args.data + (size_t)i * args.elem_size);
  ffi_call(&sig->cif, FFI_FN(fn), out, argv);
  free(argv);
  return true;
}

int ccx_ffi_ret_size(void *handle)
{
  PenguFfiSig *sig = (PenguFfiSig *)handle;
  return (sig && sig->rtype) ? (int)sig->rtype->size : 0;
}

#endif /* PENGU_HAVE_FFI */

void *ccx_dyn_open(const char *path)
{
  if (!path)
    return NULL;
#if PENGU_WINDOWS
  return (void *)LoadLibraryA(path);
#else
  return dlopen(path, RTLD_NOW | RTLD_LOCAL);
#endif
}

void *ccx_dyn_symbol(void *handle, const char *name)
{
  if (!handle || !name)
    return NULL;
#if PENGU_WINDOWS
  return (void *)GetProcAddress((HMODULE)handle, name);
#else
  return dlsym(handle, name);
#endif
}

void ccx_dyn_close(void *handle)
{
  if (!handle)
    return;
#if PENGU_WINDOWS
  FreeLibrary((HMODULE)handle);
#else
  dlclose(handle);
#endif
}
