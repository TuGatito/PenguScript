/* Optional libsodium bridge for std.secrets. */
#include "pengu_runtime.h"

#if defined(__has_include)
#  if __has_include(<sodium.h>)
#    include <sodium.h>
#    define PENGU_HAVE_SODIUM 1
#  endif
#endif

#ifdef PENGU_HAVE_SODIUM

bool ccx_sodium_init(void)
{
  return sodium_init() >= 0;
}

bool ccx_sodium_random(PenguList bytes, int n)
{
  if (!bytes.data || n <= 0 || n > bytes.cap)
    return false;
  randombytes_buf(bytes.data, (size_t)n);
  return true;
}

PenguString ccx_sodium_list_string(PenguList bytes, int n)
{
  if (!bytes.data || n <= 0)
    return pengu_string_from_cstr("");
  return pengu_string_owned(bytes.data, n);
}

PenguString ccx_sodium_sha256(PenguString data)
{
  unsigned char out[crypto_hash_sha256_BYTES];
  crypto_hash_sha256(out, (const unsigned char *)(data.data ? data.data : ""), (unsigned long long)data.len);
  return pengu_string_owned(out, (int)sizeof out);
}

void ccx_sodium_wipe(void *p, int n)
{
  if (p && n > 0)
    sodium_memzero(p, (size_t)n);
}

int ccx_sodium_compare(const void *a, const void *b, int n)
{
  if (!a || !b || n <= 0)
    return 0;
  return sodium_compare((const unsigned char *)a, (const unsigned char *)b, (unsigned long long)n);
}

#endif
