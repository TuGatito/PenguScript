/*
 * ABI v2 layout check for the PenguScript C runtime.
 *
 * Compile and run standalone:
 *     gcc -I<repo> tests/abi/test_abi_layout.c -o abi_check && ./abi_check
 *
 * The sizes/offsets below are for 64-bit targets (LP64 and LLP64); on a 32-bit
 * target the program reports SKIP instead of asserting, because ABI v2 only
 * covers 64-bit platforms.  `tests/test_abi_layout.py` runs this for the gc
 * toolchain available in CI.
 */
#include "pengu_runtime.h"

#include <stddef.h>
#include <stdio.h>

static int failures = 0;

#define CHECK_SIZE(T, EXPECTED)                                               \
    do {                                                                      \
        size_t sz = sizeof(T);                                                \
        if (sz != (size_t)(EXPECTED)) {                                       \
            fprintf(stderr, "FAIL: sizeof(%s) = %zu, expected %zu\n",         \
                    #T, sz, (size_t)(EXPECTED));                              \
            failures++;                                                       \
        }                                                                     \
    } while (0)

#define CHECK_OFFSET(T, FIELD, EXPECTED)                                      \
    do {                                                                      \
        size_t off = offsetof(T, FIELD);                                      \
        if (off != (size_t)(EXPECTED)) {                                      \
            fprintf(stderr, "FAIL: offsetof(%s, %s) = %zu, expected %zu\n",   \
                    #T, #FIELD, off, (size_t)(EXPECTED));                     \
            failures++;                                                       \
        }                                                                     \
    } while (0)

int main(void)
{
#if !defined(__LP64__) && !defined(_WIN64) && !defined(__x86_64__) && !defined(__aarch64__)
    printf("ABI v2 SKIP (non-64-bit target): sizeof(PenguString)=%zu\n", sizeof(PenguString));
    return 0;
#else
    /* PenguString: char* + int + int32_t */
    CHECK_SIZE(PenguString, 16);
    CHECK_OFFSET(PenguString, data, 0);
    CHECK_OFFSET(PenguString, len, 8);
    CHECK_OFFSET(PenguString, is_owned, 12);

    /* PenguSlice: void* + int (+pad) + size_t */
    CHECK_SIZE(PenguSlice, 24);
    CHECK_OFFSET(PenguSlice, data, 0);
    CHECK_OFFSET(PenguSlice, len, 8);
    CHECK_OFFSET(PenguSlice, elem_size, 16);

    /* PenguList: void* + int + int + size_t (no element callbacks since v2) */
    CHECK_SIZE(PenguList, 24);
    CHECK_OFFSET(PenguList, data, 0);
    CHECK_OFFSET(PenguList, len, 8);
    CHECK_OFFSET(PenguList, cap, 12);
    CHECK_OFFSET(PenguList, elem_size, 16);

    /* PenguMap: entries + int + int + 2 size_t (no entry callbacks since v2) */
    CHECK_SIZE(PenguMap, 32);
    CHECK_OFFSET(PenguMap, entries, 0);
    CHECK_OFFSET(PenguMap, len, 8);
    CHECK_OFFSET(PenguMap, cap, 12);
    CHECK_OFFSET(PenguMap, key_size, 16);
    CHECK_OFFSET(PenguMap, val_size, 24);

    /* PenguMaybe: bool (+pad) + void* */
    CHECK_SIZE(PenguMaybe, 16);
    CHECK_OFFSET(PenguMaybe, is_present, 0);
    CHECK_OFFSET(PenguMaybe, value, 8);

    /* PenguResult: bool (+pad) + void* + void* */
    CHECK_SIZE(PenguResult, 24);
    CHECK_OFFSET(PenguResult, is_ok, 0);
    CHECK_OFFSET(PenguResult, ok_val, 8);
    CHECK_OFFSET(PenguResult, err_val, 16);

    /* PenguRange: int64_t + int64_t */
    CHECK_SIZE(PenguRange, 16);
    CHECK_OFFSET(PenguRange, start, 0);
    CHECK_OFFSET(PenguRange, end, 8);

    if (PENGU_ABI_VERSION != 2) {
        fprintf(stderr, "FAIL: PENGU_ABI_VERSION = %d, expected 2\n", PENGU_ABI_VERSION);
        failures++;
    }

    if (failures) {
        fprintf(stderr, "ABI v2 FAILED (%d check(s))\n", failures);
        return 1;
    }
    printf("ABI v2 OK\n");
    return 0;
#endif
}
