/* PenguScript Runtime v0.6 - V-safety, no GC, manual memory management via
 * banish/defer */

#ifndef PENGU_RUNTIME_H
#define PENGU_RUNTIME_H

#include <ctype.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <sys/stat.h>
#include <sys/types.h>

#if defined(_WIN32) || defined(_WIN64)
#define PENGU_WINDOWS 1
#include <windows.h>
#include <process.h>
#include <direct.h>
#include <io.h>
#include <sys/utime.h>
#else
#define PENGU_WINDOWS 0
#include <unistd.h>
#include <sys/time.h>
#include <dirent.h>
#include <utime.h>
#endif

#ifdef __cplusplus
extern "C" {
#endif

/* -------------------------------------------------------------------------
 * Primitive Type Aliases
 * ------------------------------------------------------------------------- */
typedef int32_t pengu_i32;
typedef int64_t pengu_i64;
typedef float pengu_f32;
typedef double pengu_f64;
typedef bool pengu_bool;

/* -------------------------------------------------------------------------
 * String Type Definition
 * ------------------------------------------------------------------------- */
/**
 * @brief Represents an immutable UTF-8 string with explicit length and data
 * pointer.
 */
typedef struct {
  char *data;
  int len;
} PenguString;

/**
 * @brief Constructs a new PenguString from a C null-terminated string.
 * @param str Null-terminated C string buffer.
 * @return Initialized PenguString structure.
 */
static inline PenguString pengu_string_new(const char *str) {
  PenguString s;
  if (!str) {
    s.len = 0;
    s.data = (char *)"";
    return s;
  }
  s.len = (int)strlen(str);
  s.data = (char *)malloc((size_t)s.len + 1);
  if (!s.data) {
    s.len = 0;
    s.data = (char *)"";
    return s;
  }
  memcpy(s.data, str, (size_t)s.len + 1);
  return s;
}

/**
 * @brief Constructs a formatted PenguString using printf-style formatting.
 * @param fmt Format string.
 * @return Formatted PenguString.
 */
static inline PenguString pengu_string_format(const char *fmt, ...) {
  if (!fmt)
    return pengu_string_new("");
  va_list args;
  va_start(args, fmt);
  int size = vsnprintf(NULL, 0, fmt, args);
  va_end(args);
  if (size < 0)
    return pengu_string_new("");
  char *buf = (char *)malloc((size_t)size + 1);
  if (!buf)
    return pengu_string_new("");
  va_start(args, fmt);
  vsnprintf(buf, (size_t)size + 1, fmt, args);
  va_end(args);
  return (PenguString){buf, size};
}

/**
 * @brief Constructs a PenguString view from a C null-terminated string without
 * copying.
 * @param str Null-terminated C string.
 * @return View PenguString structure.
 */
static inline PenguString pengu_string_from_cstr(const char *str) {
  PenguString s;
  if (!str) {
    s.len = 0;
    s.data = (char *)"";
    return s;
  }
  s.len = (int)strlen(str);
  s.data = (char *)str;
  return s;
}

/**
 * @brief Concatenates two PenguString objects into a newly allocated
 * PenguString.
 * @param a First string.
 * @param b Second string.
 * @return Combined PenguString.
 */
static inline PenguString pengu_string_concat(PenguString a, PenguString b) {
  PenguString s;
  s.len = a.len + b.len;
  s.data = (char *)malloc((size_t)s.len + 1);
  if (s.data) {
    if (a.data && a.len > 0) {
      memcpy(s.data, a.data, (size_t)a.len);
    }
    if (b.data && b.len > 0) {
      memcpy(s.data + a.len, b.data, (size_t)b.len);
    }
    s.data[s.len] = '\0';
  }
  return s;
}

static inline bool pengu_string_equal(PenguString a, PenguString b) {
  if (a.len != b.len) return false;
  if (a.len == 0) return true;
  if (!a.data || !b.data) return a.data == b.data;
  return memcmp(a.data, b.data, (size_t)a.len) == 0;
}

/**
 * @brief Frees heap buffer allocated by a PenguString.
 * @param s Pointer to PenguString.
 */
static inline void pengu_banish_string(PenguString *s) {
  if (s && s->data && s->len > 0) {
    free(s->data);
    s->data = NULL;
    s->len = 0;
  }
}

/**
 * @brief Converts a PenguString to uppercase.
 */
static inline PenguString pengu_string_upper(PenguString s) {
  PenguString res;
  res.len = s.len;
  res.data = (char *)malloc((size_t)s.len + 1);
  if (res.data) {
    for (int i = 0; i < s.len; i++) {
      res.data[i] = (char)toupper((unsigned char)s.data[i]);
    }
    res.data[s.len] = '\0';
  }
  return res;
}

/**
 * @brief Converts a PenguString to lowercase.
 */
static inline PenguString pengu_string_lower(PenguString s) {
  PenguString res;
  res.len = s.len;
  res.data = (char *)malloc((size_t)s.len + 1);
  if (res.data) {
    for (int i = 0; i < s.len; i++) {
      res.data[i] = (char)tolower((unsigned char)s.data[i]);
    }
    res.data[s.len] = '\0';
  }
  return res;
}

/**
 * @brief Checks if string a contains substring b.
 */
static inline bool pengu_string_contains(PenguString a, PenguString b) {
  if (!a.data || !b.data)
    return false;
  if (b.len == 0)
    return true;
  if (a.len < b.len)
    return false;
  return strstr(a.data, b.data) != NULL;
}

/**
 * @brief Removes leading and trailing whitespace from a PenguString.
 */
static inline PenguString pengu_string_trim(PenguString s) {
  if (!s.data || s.len <= 0)
    return pengu_string_from_cstr("");
  int start = 0;
  while (start < s.len && isspace((unsigned char)s.data[start])) {
    start++;
  }
  int end = s.len - 1;
  while (end >= start && isspace((unsigned char)s.data[end])) {
    end--;
  }
  int len = (end >= start) ? (end - start + 1) : 0;
  if (len <= 0)
    return pengu_string_from_cstr("");
  char *buf = (char *)malloc((size_t)len + 1);
  if (!buf)
    return pengu_string_from_cstr("");
  memcpy(buf, s.data + start, (size_t)len);
  buf[len] = '\0';
  return (PenguString){buf, len};
}

/**
 * @brief Removes leading whitespace from a PenguString.
 */
static inline PenguString pengu_string_trim_start(PenguString s) {
  if (!s.data || s.len <= 0)
    return pengu_string_from_cstr("");
  int start = 0;
  while (start < s.len && isspace((unsigned char)s.data[start])) {
    start++;
  }
  int len = s.len - start;
  if (len <= 0)
    return pengu_string_from_cstr("");
  char *buf = (char *)malloc((size_t)len + 1);
  if (!buf)
    return pengu_string_from_cstr("");
  memcpy(buf, s.data + start, (size_t)len);
  buf[len] = '\0';
  return (PenguString){buf, len};
}

/**
 * @brief Removes trailing whitespace from a PenguString.
 */
static inline PenguString pengu_string_trim_end(PenguString s) {
  if (!s.data || s.len <= 0)
    return pengu_string_from_cstr("");
  int end = s.len - 1;
  while (end >= 0 && isspace((unsigned char)s.data[end])) {
    end--;
  }
  int len = end + 1;
  if (len <= 0)
    return pengu_string_from_cstr("");
  char *buf = (char *)malloc((size_t)len + 1);
  if (!buf)
    return pengu_string_from_cstr("");
  memcpy(buf, s.data, (size_t)len);
  buf[len] = '\0';
  return (PenguString){buf, len};
}

/**
 * @brief Checks if string a begins with string prefix.
 */
static inline bool pengu_string_starts_with(PenguString a, PenguString prefix) {
  if (!a.data || !prefix.data)
    return false;
  if (prefix.len == 0)
    return true;
  if (a.len < prefix.len)
    return false;
  return strncmp(a.data, prefix.data, (size_t)prefix.len) == 0;
}

/**
 * @brief Checks if string a ends with string suffix.
 */
static inline bool pengu_string_ends_with(PenguString a, PenguString suffix) {
  if (!a.data || !suffix.data)
    return false;
  if (suffix.len == 0)
    return true;
  if (a.len < suffix.len)
    return false;
  return memcmp(a.data + a.len - suffix.len, suffix.data, (size_t)suffix.len) ==
         0;
}

/**
 * @brief Returns the 0-based index of the first occurrence of sub in a, or -1
 * if not found.
 */
static inline int pengu_string_index_of(PenguString a, PenguString sub) {
  if (!a.data || !sub.data || a.len < sub.len)
    return -1;
  if (sub.len == 0)
    return 0;
  char *p = strstr(a.data, sub.data);
  return p ? (int)(p - a.data) : -1;
}

/**
 * @brief Returns the 0-based index of the last occurrence of sub in a, or -1 if
 * not found.
 */
static inline int pengu_string_last_index_of(PenguString a, PenguString sub) {
  if (!a.data || !sub.data || a.len < sub.len)
    return -1;
  if (sub.len == 0)
    return a.len;
  for (int i = a.len - sub.len; i >= 0; --i) {
    if (memcmp(a.data + i, sub.data, (size_t)sub.len) == 0) {
      return i;
    }
  }
  return -1;
}

/**
 * @brief Extracts a substring from start (inclusive) to end (exclusive).
 */
static inline PenguString pengu_string_substring(PenguString s, int start,
                                                 int end) {
  if (!s.data || s.len <= 0)
    return pengu_string_from_cstr("");
  if (start < 0)
    start = 0;
  if (end > s.len)
    end = s.len;
  if (start >= end)
    return pengu_string_from_cstr("");
  int len = end - start;
  char *buf = (char *)malloc((size_t)len + 1);
  if (!buf)
    return pengu_string_from_cstr("");
  memcpy(buf, s.data + start, (size_t)len);
  buf[len] = '\0';
  return (PenguString){buf, len};
}

/**
 * @brief Replaces all occurrences of from with to in s.
 */
static inline PenguString pengu_string_replace(PenguString s, PenguString from,
                                               PenguString to) {
  if (!s.data)
    return pengu_string_from_cstr("");
  if (!from.data || from.len <= 0)
    return pengu_string_new(s.data);

  int count = 0;
  const char *p = s.data;
  while ((p = strstr(p, from.data)) != NULL) {
    count++;
    p += from.len;
  }
  if (count == 0)
    return pengu_string_new(s.data);

  size_t new_len = (size_t)s.len + (size_t)count * (size_t)(to.len - from.len);
  char *buf = (char *)malloc(new_len + 1);
  if (!buf)
    return pengu_string_from_cstr("");

  char *dst = buf;
  const char *src = s.data;
  while ((p = strstr(src, from.data)) != NULL) {
    size_t seg = (size_t)(p - src);
    if (seg > 0) {
      memcpy(dst, src, seg);
      dst += seg;
    }
    if (to.len > 0 && to.data) {
      memcpy(dst, to.data, (size_t)to.len);
      dst += to.len;
    }
    src = p + from.len;
  }
  size_t rem = (size_t)(s.data + s.len - src);
  if (rem > 0) {
    memcpy(dst, src, rem);
    dst += rem;
  }
  *dst = '\0';
  return (PenguString){buf, (int)new_len};
}

/**
 * @brief Repeats string s times times.
 */
static inline PenguString pengu_string_repeat(PenguString s, int times) {
  if (times <= 0 || !s.data || s.len <= 0)
    return pengu_string_from_cstr("");
  size_t total_len = (size_t)s.len * (size_t)times;
  char *buf = (char *)malloc(total_len + 1);
  if (!buf)
    return pengu_string_from_cstr("");
  for (int i = 0; i < times; ++i) {
    memcpy(buf + ((size_t)i * (size_t)s.len), s.data, (size_t)s.len);
  }
  buf[total_len] = '\0';
  return (PenguString){buf, (int)total_len};
}

/**
 * @brief Reverses string s.
 */
static inline PenguString pengu_string_reverse(PenguString s) {
  if (!s.data || s.len <= 0)
    return pengu_string_from_cstr("");
  char *buf = (char *)malloc((size_t)s.len + 1);
  if (!buf)
    return pengu_string_from_cstr("");
  for (int i = 0; i < s.len; ++i) {
    buf[i] = s.data[s.len - 1 - i];
  }
  buf[s.len] = '\0';
  return (PenguString){buf, s.len};
}

/**
 * @brief Returns single character at index idx as a new PenguString.
 */
static inline PenguString pengu_string_char_at(PenguString s, int idx) {
  if (!s.data || idx < 0 || idx >= s.len)
    return pengu_string_from_cstr("");
  char buf[2] = {s.data[idx], '\0'};
  return pengu_string_new(buf);
}

/**
 * @brief Checks if all characters in s are alphabetic.
 */
static inline bool pengu_string_is_alpha(PenguString s) {
  if (!s.data || s.len <= 0)
    return false;
  for (int i = 0; i < s.len; ++i) {
    if (!isalpha((unsigned char)s.data[i]))
      return false;
  }
  return true;
}

/**
 * @brief Checks if all characters in s are numeric digits.
 */
static inline bool pengu_string_is_digit(PenguString s) {
  if (!s.data || s.len <= 0)
    return false;
  for (int i = 0; i < s.len; ++i) {
    if (!isdigit((unsigned char)s.data[i]))
      return false;
  }
  return true;
}

/**
 * @brief Checks if all characters in s are alphanumeric.
 */
static inline bool pengu_string_is_alnum(PenguString s) {
  if (!s.data || s.len <= 0)
    return false;
  for (int i = 0; i < s.len; ++i) {
    if (!isalnum((unsigned char)s.data[i]))
      return false;
  }
  return true;
}

/* -------------------------------------------------------------------------
 * Slice View Type Definition
 * ------------------------------------------------------------------------- */
/**
 * @brief Fat-pointer view into contiguous array or buffer memory.
 */
typedef struct {
  void *data;
  int len;
  size_t elem_size;
} PenguSlice;

/**
 * @brief Creates a slice view over a contiguous memory buffer.
 * @param data Memory pointer.
 * @param elem_size Size of each element in bytes.
 * @param len Number of elements in slice.
 * @return Initialized PenguSlice.
 */
static inline PenguSlice pengu_slice_new(void *data, size_t elem_size,
                                         int len) {
  PenguSlice slice;
  slice.data = data;
  slice.len = len;
  slice.elem_size = elem_size;
  return slice;
}

/**
 * @brief Retrieves pointer to element at index in slice.
 * @param slice Pointer to const PenguSlice.
 * @param idx Element index.
 * @return Pointer to element or NULL if out of bounds.
 */
static inline void *pengu_slice_at(const PenguSlice *slice, int idx) {
  if (!slice || idx < 0 || idx >= slice->len)
    return NULL;
  return (char *)slice->data + ((size_t)idx * slice->elem_size);
}

/**
 * @brief Returns length of slice.
 * @param slice Pointer to const PenguSlice.
 * @return Element count.
 */
static inline int pengu_slice_len(const PenguSlice *slice) {
  return slice ? slice->len : 0;
}

/* -------------------------------------------------------------------------
 * Dynamic List Type Definition
 * ------------------------------------------------------------------------- */
/**
 * @brief Growable dynamic list with capacity, length, and element size.
 */
typedef struct {
  void *data;
  int len;
  int cap;
  size_t elem_size;
} PenguList;

/**
 * @brief Creates a new dynamic list with given element size and capacity.
 * @param elem_size Size of each element in bytes.
 * @param cap Initial capacity.
 * @return Initialized PenguList.
 */
static inline PenguList pengu_list_new(size_t elem_size, size_t cap) {
  PenguList list;
  list.len = 0;
  list.cap = (cap > 0) ? (int)cap : 4;
  list.elem_size = elem_size;
  list.data = malloc((size_t)list.cap * elem_size);
  return list;
}

/**
 * @brief Appends an element to the list, expanding capacity if needed.
 * @param list Pointer to PenguList.
 * @param item Pointer to element data to copy into list.
 */
static inline void pengu_list_push(PenguList *list, const void *item) {
  if (!list || !item)
    return;
  if (list->len >= list->cap) {
    list->cap = (list->cap == 0) ? 4 : list->cap * 2;
    list->data = realloc(list->data, (size_t)list->cap * list->elem_size);
  }
  char *target = (char *)list->data + ((size_t)list->len * list->elem_size);
  memcpy(target, item, list->elem_size);
  list->len++;
}

/**
 * @brief Pops and removes the last element from the list, returning a pointer to it.
 * @param list Pointer to PenguList.
 * @return Pointer to popped element buffer, or NULL if list was empty.
 */
static inline void *pengu_list_pop_val(PenguList *list) {
  if (!list || list->len <= 0)
    return NULL;
  list->len--;
  return (char *)list->data + ((size_t)list->len * list->elem_size);
}

/**
 * @brief Finds the index of an item in the list.
 * @param list Pointer to const PenguList.
 * @param item Pointer to item data.
 * @return Index of element, or -1 if not found.
 */
static inline int pengu_list_index_of(const PenguList *list, const void *item) {
  if (!list || !item || list->len <= 0)
    return -1;
  for (int i = 0; i < list->len; ++i) {
    void *elem = (char *)list->data + ((size_t)i * list->elem_size);
    if (list->elem_size == sizeof(PenguString)) {
      PenguString *s1 = (PenguString *)elem;
      PenguString *s2 = (PenguString *)item;
      if (s1->len == s2->len && (s1->len == 0 || memcmp(s1->data, s2->data, (size_t)s1->len) == 0))
        return i;
    } else {
      if (memcmp(elem, item, list->elem_size) == 0)
        return i;
    }
  }
  return -1;
}

/**
 * @brief Checks if list contains an item.
 * @param list Pointer to const PenguList.
 * @param item Pointer to item data.
 * @return True if item is in list, False otherwise.
 */
static inline bool pengu_list_contains(const PenguList *list, const void *item) {
  return pengu_list_index_of(list, item) != -1;
}

/**
 * @brief Pops and removes the last element from the list.
 * @param list Pointer to PenguList.
 * @param out_item Optional destination buffer to copy popped element into.
 * @return True if an element was popped, False if list was empty.
 */
static inline bool pengu_list_pop(PenguList *list, void *out_item) {
  if (!list || list->len <= 0)
    return false;
  list->len--;
  if (out_item) {
    char *src = (char *)list->data + ((size_t)list->len * list->elem_size);
    memcpy(out_item, src, list->elem_size);
  }
  return true;
}

/**
 * @brief Accesses element at index in dynamic list.
 * @param list Pointer to const PenguList.
 * @param idx Element index.
 * @return Pointer to element or NULL if out of bounds.
 */
static inline void *pengu_list_at(const PenguList *list, int idx) {
  if (!list || idx < 0 || idx >= list->len)
    return NULL;
  return (char *)list->data + ((size_t)idx * list->elem_size);
}

/**
 * @brief Clears all elements from the list without freeing allocated buffer.
 * @param list Pointer to PenguList.
 */
static inline void pengu_list_clear(PenguList *list) {
  if (list) {
    list->len = 0;
  }
}

/**
 * @brief Frees memory allocated by a dynamic list.
 * @param list Pointer to PenguList.
 */
static inline void pengu_banish_list(PenguList *list) {
  if (list && list->data) {
    free(list->data);
    list->data = NULL;
    list->len = 0;
    list->cap = 0;
  }
}

/**
 * @brief Splits string s by delimiter delim into a dynamic PenguList of
 * PenguString.
 */
static inline PenguList pengu_string_split(PenguString s, PenguString delim) {
  PenguList list = pengu_list_new(sizeof(PenguString), 4);
  if (!s.data || s.len == 0) {
    PenguString empty = pengu_string_new("");
    pengu_list_push(&list, &empty);
    return list;
  }
  if (!delim.data || delim.len == 0) {
    for (int i = 0; i < s.len; ++i) {
      char b[2] = {s.data[i], '\0'};
      PenguString ch = pengu_string_new(b);
      pengu_list_push(&list, &ch);
    }
    return list;
  }
  const char *src = s.data;
  const char *p;
  while ((p = strstr(src, delim.data)) != NULL) {
    int seg_len = (int)(p - src);
    char *buf = (char *)malloc((size_t)seg_len + 1);
    if (buf) {
      if (seg_len > 0)
        memcpy(buf, src, (size_t)seg_len);
      buf[seg_len] = '\0';
      PenguString part = {buf, seg_len};
      pengu_list_push(&list, &part);
    }
    src = p + delim.len;
  }
  int rem_len = (int)(s.data + s.len - src);
  char *buf = (char *)malloc((size_t)rem_len + 1);
  if (buf) {
    if (rem_len > 0)
      memcpy(buf, src, (size_t)rem_len);
    buf[rem_len] = '\0';
    PenguString part = {buf, rem_len};
    pengu_list_push(&list, &part);
  }
  return list;
}

/**
 * @brief Pushes an int32 element onto dynamic list.
 */
static inline void pengu_list_push_int(PenguList *l, const int32_t *item) {
  pengu_list_push(l, item);
}

/**
 * @brief Pushes a PenguString element onto dynamic list.
 */
static inline void pengu_list_push_string(PenguList *l,
                                          const PenguString *item) {
  pengu_list_push(l, item);
}

/**
 * @brief Pops the last int32 element from dynamic list.
 */
static inline bool pengu_list_pop_int(PenguList *l, int32_t *out) {
  return pengu_list_pop(l, out);
}

/**
 * @brief Checks if dynamic list of int32 contains item.
 */
static inline bool pengu_list_contains_int(const PenguList *l,
                                           const int32_t *item) {
  if (!l || !item || !l->data)
    return false;
  for (int i = 0; i < l->len; ++i) {
    const int32_t *val = (const int32_t *)pengu_list_at(l, i);
    if (val && *val == *item)
      return true;
  }
  return false;
}

/**
 * @brief Returns 0-based index of item in list of int32, or -1 if not found.
 */
static inline int pengu_list_index_of_int(const PenguList *l,
                                          const int32_t *item) {
  if (!l || !item || !l->data)
    return -1;
  for (int i = 0; i < l->len; ++i) {
    const int32_t *val = (const int32_t *)pengu_list_at(l, i);
    if (val && *val == *item)
      return i;
  }
  return -1;
}

/* -------------------------------------------------------------------------
 * Hash Map Type Definition
 * ------------------------------------------------------------------------- */
/**
 * @brief Single key-value entry in open addressing hash table.
 */
typedef struct {
  uint32_t hash;
  void *key;
  void *val;
  bool occupied;
} PenguMapEntry;

/**
 * @brief Key-value hash map collection.
 */
typedef struct {
  PenguMapEntry *entries;
  int len;
  int cap;
  size_t key_size;
  size_t val_size;
} PenguMap;

/**
 * @brief Computes 32-bit FNV-1a hash over raw byte buffer.
 * @param data Pointer to buffer.
 * @param len Buffer length in bytes.
 * @return 32-bit hash value.
 */
static inline uint32_t pengu_hash_bytes(const void *data, size_t len) {
  const uint8_t *bytes = (const uint8_t *)data;
  uint32_t hash = 2166136261u;
  for (size_t i = 0; i < len; ++i) {
    hash ^= bytes[i];
    hash *= 16777619u;
  }
  return hash;
}

/**
 * @brief Creates a new hash map.
 * @param key_size Size of key type in bytes.
 * @param val_size Size of value type in bytes.
 * @return Initialized PenguMap.
 */
static inline PenguMap pengu_map_new(size_t key_size, size_t val_size) {
  PenguMap map;
  map.len = 0;
  map.cap = 16;
  map.key_size = key_size;
  map.val_size = val_size;
  map.entries = (PenguMapEntry *)calloc((size_t)map.cap, sizeof(PenguMapEntry));
  return map;
}

/**
 * @brief Inserts or updates key-value pair in hash map.
 * @param map Pointer to PenguMap.
 * @param key Pointer to key data.
 * @param val Pointer to value data.
 */
static inline void pengu_map_put(PenguMap *map, const void *key, const void *val) {
  if (!map || !key || !val)
    return;
  if (map->cap == 0) {
    map->cap = 16;
    map->entries = (PenguMapEntry *)calloc((size_t)map->cap, sizeof(PenguMapEntry));
    map->len = 0;
  }
  if (map->len * 2 >= map->cap) {
    int old_cap = map->cap;
    PenguMapEntry *old_entries = map->entries;
    map->cap = old_cap * 2;
    map->entries = (PenguMapEntry *)calloc((size_t)map->cap, sizeof(PenguMapEntry));
    map->len = 0;
    for (int i = 0; i < old_cap; ++i) {
      if (old_entries[i].occupied) {
        pengu_map_put(map, old_entries[i].key, old_entries[i].val);
        free(old_entries[i].key);
        free(old_entries[i].val);
      }
    }
    free(old_entries);
  }
  uint32_t h = (map->key_size == sizeof(PenguString)) ?
    (((PenguString*)key)->data && ((PenguString*)key)->len > 0 ? pengu_hash_bytes(((PenguString*)key)->data, (size_t)((PenguString*)key)->len) : 0) :
    pengu_hash_bytes(key, map->key_size);
  int idx = (int)(h % (uint32_t)map->cap);
  for (int i = 0; i < map->cap; ++i) {
    int cur = (idx + i) % map->cap;
    if (!map->entries[cur].occupied) {
      map->entries[cur].hash = h;
      map->entries[cur].occupied = true;
      map->entries[cur].key = malloc(map->key_size);
      map->entries[cur].val = malloc(map->val_size);
      if (map->key_size == sizeof(PenguString)) {
        *(PenguString*)map->entries[cur].key = pengu_string_new(((PenguString*)key)->data);
      } else {
        memcpy(map->entries[cur].key, key, map->key_size);
      }
      if (map->val_size == sizeof(PenguString)) {
        *(PenguString*)map->entries[cur].val = pengu_string_new(((PenguString*)val)->data);
      } else {
        memcpy(map->entries[cur].val, val, map->val_size);
      }
      map->len++;
      return;
    } else if (map->entries[cur].hash == h) {
      bool match = false;
      if (map->key_size == sizeof(PenguString)) {
        PenguString *k1 = (PenguString*)map->entries[cur].key;
        PenguString *k2 = (PenguString*)key;
        match = (k1->len == k2->len && (k1->len == 0 || memcmp(k1->data, k2->data, (size_t)k1->len) == 0));
      } else {
        match = (memcmp(map->entries[cur].key, key, map->key_size) == 0);
      }
      if (match) {
        if (map->val_size == sizeof(PenguString)) {
          pengu_banish_string((PenguString*)map->entries[cur].val);
          *(PenguString*)map->entries[cur].val = pengu_string_new(((PenguString*)val)->data);
        } else {
          memcpy(map->entries[cur].val, val, map->val_size);
        }
        return;
      }
    }
  }
}

/**
 * @brief Retrieves value pointer corresponding to key in hash map.
 * @param map Pointer to const PenguMap.
 * @param key Pointer to key data.
 * @return Pointer to value or NULL if key not found.
 */
static inline void *pengu_map_get(const PenguMap *map, const void *key) {
  if (!map || !key || map->cap == 0)
    return NULL;
  uint32_t h = (map->key_size == sizeof(PenguString)) ?
    (((PenguString*)key)->data && ((PenguString*)key)->len > 0 ? pengu_hash_bytes(((PenguString*)key)->data, (size_t)((PenguString*)key)->len) : 0) :
    pengu_hash_bytes(key, map->key_size);
  int idx = (int)(h % (uint32_t)map->cap);
  for (int i = 0; i < map->cap; ++i) {
    int cur = (idx + i) % map->cap;
    if (!map->entries[cur].occupied)
      return NULL;
    if (map->entries[cur].hash == h) {
      bool match = false;
      if (map->key_size == sizeof(PenguString)) {
        PenguString *k1 = (PenguString*)map->entries[cur].key;
        PenguString *k2 = (PenguString*)key;
        match = (k1->len == k2->len && (k1->len == 0 || memcmp(k1->data, k2->data, (size_t)k1->len) == 0));
      } else {
        match = (memcmp(map->entries[cur].key, key, map->key_size) == 0);
      }
      if (match)
        return map->entries[cur].val;
    }
  }
  return NULL;
}

/**
 * @brief Checks if hash map contains a key.
 * @param map Pointer to const PenguMap.
 * @param key Pointer to key data.
 * @return True if key exists, False otherwise.
 */
static inline bool pengu_map_contains(const PenguMap *map, const void *key) {
  return pengu_map_get(map, key) != NULL;
}

/**
 * @brief Removes entry by key from hash map.
 * @param map Pointer to PenguMap.
 * @param key Pointer to key data.
 * @return True if entry was removed, False if not found.
 */
static inline bool pengu_map_remove(PenguMap *map, const void *key) {
  if (!map || !key || map->cap == 0)
    return false;
  uint32_t h = (map->key_size == sizeof(PenguString)) ?
    (((PenguString*)key)->data && ((PenguString*)key)->len > 0 ? pengu_hash_bytes(((PenguString*)key)->data, (size_t)((PenguString*)key)->len) : 0) :
    pengu_hash_bytes(key, map->key_size);
  int idx = (int)(h % (uint32_t)map->cap);
  for (int i = 0; i < map->cap; ++i) {
    int cur = (idx + i) % map->cap;
    if (!map->entries[cur].occupied)
      return false;
    if (map->entries[cur].hash == h) {
      bool match = false;
      if (map->key_size == sizeof(PenguString)) {
        PenguString *k1 = (PenguString*)map->entries[cur].key;
        PenguString *k2 = (PenguString*)key;
        match = (k1->len == k2->len && (k1->len == 0 || memcmp(k1->data, k2->data, (size_t)k1->len) == 0));
      } else {
        match = (memcmp(map->entries[cur].key, key, map->key_size) == 0);
      }
      if (match) {
        if (map->key_size == sizeof(PenguString)) {
          pengu_banish_string((PenguString*)map->entries[cur].key);
        }
        if (map->val_size == sizeof(PenguString)) {
          pengu_banish_string((PenguString*)map->entries[cur].val);
        }
        free(map->entries[cur].key);
        free(map->entries[cur].val);
        map->entries[cur].occupied = false;
        map->entries[cur].key = NULL;
        map->entries[cur].val = NULL;
        map->entries[cur].hash = 0;
        map->len--;
        return true;
      }
    }
  }
  return false;
}

/**
 * @brief Frees memory allocated by a hash map.
 * @param map Pointer to PenguMap.
 */
static inline void pengu_banish_map(PenguMap *map) {
  if (map && map->entries) {
    for (int i = 0; i < map->cap; ++i) {
      if (map->entries[i].occupied) {
        if (map->entries[i].key) {
          if (map->key_size == sizeof(PenguString)) {
            pengu_banish_string((PenguString *)map->entries[i].key);
          }
          free(map->entries[i].key);
        }
        if (map->entries[i].val) {
          if (map->val_size == sizeof(PenguString)) {
            pengu_banish_string((PenguString *)map->entries[i].val);
          }
          free(map->entries[i].val);
        }
      }
    }
    free(map->entries);
    map->entries = NULL;
    map->len = 0;
    map->cap = 0;
  }
}

/**
 * @brief Clears all entries in a PenguMap.
 */
static inline void pengu_map_clear(PenguMap *map) {
  if (!map || !map->entries)
    return;
  for (int i = 0; i < map->cap; ++i) {
    if (map->entries[i].occupied) {
      if (map->entries[i].key) {
        if (map->key_size == sizeof(PenguString)) {
          pengu_banish_string((PenguString *)map->entries[i].key);
        }
        free(map->entries[i].key);
        map->entries[i].key = NULL;
      }
      if (map->entries[i].val) {
        if (map->val_size == sizeof(PenguString)) {
          pengu_banish_string((PenguString *)map->entries[i].val);
        }
        free(map->entries[i].val);
        map->entries[i].val = NULL;
      }
      map->entries[i].occupied = false;
      map->entries[i].hash = 0;
    }
  }
  map->len = 0;
}

/**
 * @brief Inserts or updates a string-to-int pair in the hash map.
 */
static inline void pengu_map_put_string_int(PenguMap *m, const PenguString *k,
                                            const int32_t *v) {
  if (!m || !k || !v)
    return;
  if (m->cap == 0) {
    m->cap = 16;
    m->entries = (PenguMapEntry *)calloc((size_t)m->cap, sizeof(PenguMapEntry));
    m->key_size = sizeof(PenguString);
    m->val_size = sizeof(int32_t);
    m->len = 0;
  }
  if (m->len * 2 >= m->cap) {
    int old_cap = m->cap;
    PenguMapEntry *old_entries = m->entries;
    m->cap = old_cap * 2;
    m->entries = (PenguMapEntry *)calloc((size_t)m->cap, sizeof(PenguMapEntry));
    m->len = 0;
    for (int i = 0; i < old_cap; ++i) {
      if (old_entries[i].occupied) {
        PenguString *ek = (PenguString *)old_entries[i].key;
        int32_t *ev = (int32_t *)old_entries[i].val;
        pengu_map_put_string_int(m, ek, ev);
        pengu_banish_string(ek);
        free(ek);
        free(ev);
      }
    }
    free(old_entries);
  }
  uint32_t h =
      (k->data && k->len > 0) ? pengu_hash_bytes(k->data, (size_t)k->len) : 0;
  int idx = (int)(h % (uint32_t)m->cap);
  for (int i = 0; i < m->cap; ++i) {
    int cur = (idx + i) % m->cap;
    if (!m->entries[cur].occupied) {
      m->entries[cur].hash = h;
      m->entries[cur].occupied = true;
      PenguString *key_copy = (PenguString *)malloc(sizeof(PenguString));
      *key_copy = pengu_string_new(k->data);
      int32_t *val_copy = (int32_t *)malloc(sizeof(int32_t));
      *val_copy = *v;
      m->entries[cur].key = key_copy;
      m->entries[cur].val = val_copy;
      m->len++;
      return;
    } else if (m->entries[cur].hash == h) {
      PenguString *existing = (PenguString *)m->entries[cur].key;
      if (existing->len == k->len &&
          (k->len == 0 ||
           memcmp(existing->data, k->data, (size_t)k->len) == 0)) {
        *(int32_t *)m->entries[cur].val = *v;
        return;
      }
    }
  }
}

/**
 * @brief Retrieves pointer to int32 value for string key in hash map.
 */
static inline int32_t *pengu_map_get_string_int(const PenguMap *m,
                                                const PenguString *k) {
  if (!m || !k || !m->entries || m->cap == 0)
    return NULL;
  uint32_t h =
      (k->data && k->len > 0) ? pengu_hash_bytes(k->data, (size_t)k->len) : 0;
  int idx = (int)(h % (uint32_t)m->cap);
  for (int i = 0; i < m->cap; ++i) {
    int cur = (idx + i) % m->cap;
    if (!m->entries[cur].occupied)
      return NULL;
    if (m->entries[cur].hash == h) {
      PenguString *existing = (PenguString *)m->entries[cur].key;
      if (existing->len == k->len &&
          (k->len == 0 ||
           memcmp(existing->data, k->data, (size_t)k->len) == 0)) {
        return (int32_t *)m->entries[cur].val;
      }
    }
  }
  return NULL;
}

/**
 * @brief Checks if hash map contains string key.
 */
static inline bool pengu_map_contains_string_int(const PenguMap *m,
                                                 const PenguString *k) {
  return pengu_map_get_string_int(m, k) != NULL;
}

/**
 * @brief Removes string key entry from hash map.
 */
static inline bool pengu_map_remove_string_int(PenguMap *m,
                                               const PenguString *k) {
  if (!m || !k || !m->entries || m->cap == 0)
    return false;
  uint32_t h =
      (k->data && k->len > 0) ? pengu_hash_bytes(k->data, (size_t)k->len) : 0;
  int idx = (int)(h % (uint32_t)m->cap);
  for (int i = 0; i < m->cap; ++i) {
    int cur = (idx + i) % m->cap;
    if (!m->entries[cur].occupied)
      return false;
    if (m->entries[cur].hash == h) {
      PenguString *existing = (PenguString *)m->entries[cur].key;
      if (existing->len == k->len &&
          (k->len == 0 ||
           memcmp(existing->data, k->data, (size_t)k->len) == 0)) {
        pengu_banish_string(existing);
        free(m->entries[cur].key);
        free(m->entries[cur].val);
        m->entries[cur].key = NULL;
        m->entries[cur].val = NULL;
        m->entries[cur].occupied = false;
        m->entries[cur].hash = 0;
        m->len--;
        return true;
      }
    }
  }
  return false;
}

/* -------------------------------------------------------------------------
 * Maybe Type Definition
 * ------------------------------------------------------------------------- */
/**
 * @brief Optional union structure representing value presence or none.
 */
typedef struct {
  bool is_present;
  void *value;
} PenguMaybe;

/**
 * @brief Constructs a Maybe value containing present data.
 * @param value Pointer to value.
 * @return PenguMaybe holding value.
 */
static inline PenguMaybe pengu_maybe_some(void *value) {
  PenguMaybe m;
  m.is_present = true;
  m.value = value;
  return m;
}

/**
 * @brief Constructs a Maybe none value.
 * @return Empty PenguMaybe.
 */
static inline PenguMaybe pengu_maybe_none(void) {
  PenguMaybe m;
  m.is_present = false;
  m.value = NULL;
  return m;
}

/**
 * @brief Checks if a Maybe structure contains a present value.
 * @param m Pointer to const PenguMaybe.
 * @return True if present, False if none.
 */
static inline bool pengu_maybe_is_present(const PenguMaybe *m) {
  return m ? m->is_present : false;
}

/* -------------------------------------------------------------------------
 * Result Union Type Definition
 * ------------------------------------------------------------------------- */
/**
 * @brief Result container representing either success value or error.
 */
typedef struct {
  bool is_ok;
  void *ok_val;
  void *err_val;
} PenguResult;

/**
 * @brief Constructs a successful Result.
 * @param ok_val Pointer to success value.
 * @return PenguResult with is_ok true.
 */
static inline PenguResult pengu_result_ok(void *ok_val) {
  PenguResult r;
  r.is_ok = true;
  r.ok_val = ok_val;
  r.err_val = NULL;
  return r;
}

/**
 * @brief Constructs an error Result.
 * @param err_val Pointer to error value.
 * @return PenguResult with is_ok false.
 */
static inline PenguResult pengu_result_err(void *err_val) {
  PenguResult r;
  r.is_ok = false;
  r.ok_val = NULL;
  r.err_val = err_val;
  return r;
}

/**
 * @brief Checks if a Result is successful.
 * @param r Pointer to const PenguResult.
 * @return True if ok, False if error.
 */
static inline bool pengu_result_is_ok(const PenguResult *r) {
  return r ? r->is_ok : false;
}

/* -------------------------------------------------------------------------
 * Fixed Array Macro / Type
 * ------------------------------------------------------------------------- */
#define PENGU_ARRAY_TYPE(T, N)                                                 \
  struct {                                                                     \
    T data[N];                                                                 \
    int len;                                                                   \
  }

/* -------------------------------------------------------------------------
 * Memory Allocation and Banish
 * ------------------------------------------------------------------------- */
/**
 * @brief Allocates heap memory for a reference (sigil of).
 * @param size Size in bytes.
 * @return Allocated pointer zero-initialized.
 */
static inline void *pengu_sigil_alloc(size_t size) {
  void *ptr = malloc(size);
  if (ptr) {
    memset(ptr, 0, size);
  }
  return ptr;
}

/**
 * @brief Deallocates memory behind a reference (banish).
 * @param ptr Pointer to free.
 */
static inline void pengu_banish(void *ptr) {
  if (ptr) {
    free(ptr);
  }
}

/* =========================================================================
 * STANDARD LIBRARY RUNTIME HELPERS (SPARK, WHISPER, ARITHMANCY, ETC.)
 * ========================================================================= */
static int g_pengu_argc = 0;
static char** g_pengu_argv = NULL;
static int g_pengu_log_level = 0;

static inline void pengu_init(int argc, char** argv) {
    g_pengu_argc = argc;
    g_pengu_argv = argv;
}

/* 1. Spark */
static inline void pengu_print(PenguString s) {
    if (s.data && s.len > 0) fwrite(s.data, 1, (size_t)s.len, stdout);
}
static inline void pengu_println(PenguString s) {
    if (s.data && s.len > 0) fwrite(s.data, 1, (size_t)s.len, stdout);
    fputc('\n', stdout);
}
static inline PenguString pengu_input(PenguString prompt) {
    if (prompt.data && prompt.len > 0) {
        fwrite(prompt.data, 1, (size_t)prompt.len, stdout);
        fflush(stdout);
    }
    char buf[4096];
    if (!fgets(buf, sizeof(buf), stdin)) return pengu_string_from_cstr("");
    size_t l = strlen(buf);
    while (l > 0 && (buf[l - 1] == '\r' || buf[l - 1] == '\n')) buf[--l] = '\0';
    return pengu_string_new(buf);
}
static inline PenguMaybe pengu_parse_int(PenguString s) {
    if (!s.data || s.len == 0) return pengu_maybe_none();
    char* endptr = NULL;
    long val = strtol(s.data, &endptr, 10);
    if (endptr == s.data || *endptr != '\0') return pengu_maybe_none();
    int32_t* res = (int32_t*)malloc(sizeof(int32_t));
    *res = (int32_t)val;
    return pengu_maybe_some(res);
}
static inline PenguMaybe pengu_parse_float(PenguString s) {
    if (!s.data || s.len == 0) return pengu_maybe_none();
    char* endptr = NULL;
    double val = strtod(s.data, &endptr);
    if (endptr == s.data || *endptr != '\0') return pengu_maybe_none();
    double* res = (double*)malloc(sizeof(double));
    *res = val;
    return pengu_maybe_some(res);
}
static inline void pengu_panic(PenguString msg) {
    fprintf(stderr, "[PANIC] %.*s\n", msg.len, msg.data ? msg.data : "");
    exit(1);
}

static inline PenguString pengu_string_from_int(int64_t val) {
    char buf[64];
    snprintf(buf, sizeof(buf), "%lld", (long long)val);
    return pengu_string_new(buf);
}
static inline PenguString pengu_string_from_float(double val) {
    char buf[64];
    snprintf(buf, sizeof(buf), "%g", val);
    return pengu_string_new(buf);
}
static inline PenguString pengu_string_from_char(char c) {
    char buf[2] = { c, '\0' };
    return pengu_string_from_cstr(buf);
}

static inline PenguString pengu_string_from_bool(bool val) {
    return val ? pengu_string_from_cstr("true") : pengu_string_from_cstr("false");
}

static inline PenguString pengu_string_identity(PenguString s) { return s; }

#define pengu_to_string(x) _Generic((x), \
    char: pengu_string_from_char, \
    signed char: pengu_string_from_char, \
    unsigned char: pengu_string_from_int, \
    short: pengu_string_from_int, \
    unsigned short: pengu_string_from_int, \
    int: pengu_string_from_int, \
    unsigned int: pengu_string_from_int, \
    long: pengu_string_from_int, \
    unsigned long: pengu_string_from_int, \
    long long: pengu_string_from_int, \
    unsigned long long: pengu_string_from_int, \
    double: pengu_string_from_float, \
    float: pengu_string_from_float, \
    bool: pengu_string_from_bool, \
    PenguString: pengu_string_identity \
)(x)

/* 2. Whisper */
static inline void pengu_log_set_level(int level) {
    g_pengu_log_level = level;
}
static inline int pengu_log_get_level(void) {
    return g_pengu_log_level;
}

/* 3. Arithmancy */
static inline double pengu_c_fabs(double x) { return fabs(x); }
static inline double pengu_c_sqrt(double x) { return sqrt(x); }
static inline double pengu_c_pow(double x, double y) { return pow(x, y); }
static inline double pengu_c_floor(double x) { return floor(x); }
static inline double pengu_c_ceil(double x) { return ceil(x); }
static inline double pengu_c_round(double x) { return round(x); }
static inline double pengu_c_trunc(double x) { return trunc(x); }
static inline double pengu_c_fmod(double x, double y) { return fmod(x, y); }
static inline double pengu_c_sin(double x) { return sin(x); }
static inline double pengu_c_cos(double x) { return cos(x); }
static inline double pengu_c_tan(double x) { return tan(x); }
static inline double pengu_c_asin(double x) { return asin(x); }
static inline double pengu_c_acos(double x) { return acos(x); }
static inline double pengu_c_atan(double x) { return atan(x); }
static inline double pengu_c_atan2(double y, double x) { return atan2(y, x); }
static inline double pengu_c_exp(double x) { return exp(x); }
static inline double pengu_c_log(double x) { return log(x); }
static inline double pengu_c_log10(double x) { return log10(x); }
static inline double pengu_c_log2(double x) { return log2(x); }
static inline double pengu_c_sinh(double x) { return sinh(x); }
static inline double pengu_c_cosh(double x) { return cosh(x); }
static inline double pengu_c_tanh(double x) { return tanh(x); }
static inline double pengu_c_asinh(double x) { return asinh(x); }
static inline double pengu_c_acosh(double x) { return acosh(x); }
static inline double pengu_c_atanh(double x) { return atanh(x); }
static inline bool pengu_c_is_prime(int n) {
    if (n <= 1) return false;
    if (n <= 3) return true;
    if (n % 2 == 0 || n % 3 == 0) return false;
    for (int i = 5; (int64_t)i * i <= n; i += 6) {
        if (n % i == 0 || n % (i + 2) == 0) return false;
    }
    return true;
}
static inline int pengu_c_gcd(int a, int b) {
    a = abs(a); b = abs(b);
    while (b != 0) { int t = b; b = a % b; a = t; }
    return a;
}
static inline int pengu_c_lcm(int a, int b) {
    if (a == 0 || b == 0) return 0;
    return abs(a * (b / pengu_c_gcd(a, b)));
}

/* 4. Chronicle */
static inline double pengu_c_time(void) { return (double)time(NULL); }
static inline double pengu_c_time_monotonic(void) {
#if PENGU_WINDOWS
    LARGE_INTEGER freq, counter;
    QueryPerformanceFrequency(&freq);
    QueryPerformanceCounter(&counter);
    return (double)counter.QuadPart / (double)freq.QuadPart;
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec / 1e9;
#endif
}
static inline void pengu_c_sleep_ms(int ms) {
    if (ms <= 0) return;
#if PENGU_WINDOWS
    Sleep((DWORD)ms);
#else
    struct timespec req;
    req.tv_sec = ms / 1000;
    req.tv_nsec = (long)(ms % 1000) * 1000000L;
    nanosleep(&req, NULL);
#endif
}
static inline void pengu_c_sleep_sec(double sec) {
    if (sec <= 0.0) return;
    pengu_c_sleep_ms((int)(sec * 1000.0));
}
static inline PenguString pengu_c_strftime(PenguString fmt, double timestamp) {
    time_t t = (time_t)timestamp;
    struct tm tm_info;
#if PENGU_WINDOWS
    gmtime_s(&tm_info, &t);
#else
    gmtime_r(&t, &tm_info);
#endif
    char buf[512];
    size_t len = strftime(buf, sizeof(buf), (fmt.data && fmt.len > 0) ? fmt.data : "%Y-%m-%d %H:%M:%S", &tm_info);
    return (len > 0) ? pengu_string_new(buf) : pengu_string_from_cstr("");
}
static inline PenguMaybe pengu_c_strptime(PenguString s, PenguString fmt) {
    if (!s.data || s.len == 0) return pengu_maybe_none();
    struct tm tm_val;
    memset(&tm_val, 0, sizeof(tm_val));
    int y = 0, m = 0, d = 0, h = 0, min = 0, sec = 0;
    if (sscanf(s.data, "%d-%d-%dT%d:%d:%d", &y, &m, &d, &h, &min, &sec) >= 3 ||
        sscanf(s.data, "%d-%d-%d", &y, &m, &d) >= 3) {
        tm_val.tm_year = y - 1900;
        tm_val.tm_mon = m - 1;
        tm_val.tm_mday = d;
        tm_val.tm_hour = h;
        tm_val.tm_min = min;
        tm_val.tm_sec = sec;
        time_t t = mktime(&tm_val);
        if (t != (time_t)-1) {
            double* res = (double*)malloc(sizeof(double));
            *res = (double)t;
            return pengu_maybe_some(res);
        }
    }
    return pengu_maybe_none();
}
static inline int pengu_c_get_utc_year(double ts) {
    time_t t = (time_t)ts; struct tm tm_info;
#if PENGU_WINDOWS
    gmtime_s(&tm_info, &t);
#else
    gmtime_r(&t, &tm_info);
#endif
    return tm_info.tm_year + 1900;
}
static inline int pengu_c_get_utc_month(double ts) {
    time_t t = (time_t)ts; struct tm tm_info;
#if PENGU_WINDOWS
    gmtime_s(&tm_info, &t);
#else
    gmtime_r(&t, &tm_info);
#endif
    return tm_info.tm_mon + 1;
}
static inline int pengu_c_get_utc_day(double ts) {
    time_t t = (time_t)ts; struct tm tm_info;
#if PENGU_WINDOWS
    gmtime_s(&tm_info, &t);
#else
    gmtime_r(&t, &tm_info);
#endif
    return tm_info.tm_mday;
}
static inline int pengu_c_get_utc_hour(double ts) {
    time_t t = (time_t)ts; struct tm tm_info;
#if PENGU_WINDOWS
    gmtime_s(&tm_info, &t);
#else
    gmtime_r(&t, &tm_info);
#endif
    return tm_info.tm_hour;
}
static inline int pengu_c_get_utc_minute(double ts) {
    time_t t = (time_t)ts; struct tm tm_info;
#if PENGU_WINDOWS
    gmtime_s(&tm_info, &t);
#else
    gmtime_r(&t, &tm_info);
#endif
    return tm_info.tm_min;
}
static inline int pengu_c_get_utc_second(double ts) {
    time_t t = (time_t)ts; struct tm tm_info;
#if PENGU_WINDOWS
    gmtime_s(&tm_info, &t);
#else
    gmtime_r(&t, &tm_info);
#endif
    return tm_info.tm_sec;
}
static inline int pengu_c_get_utc_weekday(double ts) {
    time_t t = (time_t)ts; struct tm tm_info;
#if PENGU_WINDOWS
    gmtime_s(&tm_info, &t);
#else
    gmtime_r(&t, &tm_info);
#endif
    return tm_info.tm_wday;
}
static inline int pengu_c_get_utc_yearday(double ts) {
    time_t t = (time_t)ts; struct tm tm_info;
#if PENGU_WINDOWS
    gmtime_s(&tm_info, &t);
#else
    gmtime_r(&t, &tm_info);
#endif
    return tm_info.tm_yday;
}
static inline bool pengu_c_get_utc_is_dst(double ts) {
    time_t t = (time_t)ts; struct tm tm_info;
#if PENGU_WINDOWS
    gmtime_s(&tm_info, &t);
#else
    gmtime_r(&t, &tm_info);
#endif
    return tm_info.tm_isdst > 0;
}
static inline int pengu_c_get_local_year(double ts) {
    time_t t = (time_t)ts; struct tm tm_info;
#if PENGU_WINDOWS
    localtime_s(&tm_info, &t);
#else
    localtime_r(&t, &tm_info);
#endif
    return tm_info.tm_year + 1900;
}
static inline int pengu_c_get_local_month(double ts) {
    time_t t = (time_t)ts; struct tm tm_info;
#if PENGU_WINDOWS
    localtime_s(&tm_info, &t);
#else
    localtime_r(&t, &tm_info);
#endif
    return tm_info.tm_mon + 1;
}
static inline int pengu_c_get_local_day(double ts) {
    time_t t = (time_t)ts; struct tm tm_info;
#if PENGU_WINDOWS
    localtime_s(&tm_info, &t);
#else
    localtime_r(&t, &tm_info);
#endif
    return tm_info.tm_mday;
}
static inline int pengu_c_get_local_hour(double ts) {
    time_t t = (time_t)ts; struct tm tm_info;
#if PENGU_WINDOWS
    localtime_s(&tm_info, &t);
#else
    localtime_r(&t, &tm_info);
#endif
    return tm_info.tm_hour;
}
static inline int pengu_c_get_local_minute(double ts) {
    time_t t = (time_t)ts; struct tm tm_info;
#if PENGU_WINDOWS
    localtime_s(&tm_info, &t);
#else
    localtime_r(&t, &tm_info);
#endif
    return tm_info.tm_min;
}
static inline int pengu_c_get_local_second(double ts) {
    time_t t = (time_t)ts; struct tm tm_info;
#if PENGU_WINDOWS
    localtime_s(&tm_info, &t);
#else
    localtime_r(&t, &tm_info);
#endif
    return tm_info.tm_sec;
}
static inline int pengu_c_get_local_weekday(double ts) {
    time_t t = (time_t)ts; struct tm tm_info;
#if PENGU_WINDOWS
    localtime_s(&tm_info, &t);
#else
    localtime_r(&t, &tm_info);
#endif
    return tm_info.tm_wday;
}
static inline int pengu_c_get_local_yearday(double ts) {
    time_t t = (time_t)ts; struct tm tm_info;
#if PENGU_WINDOWS
    localtime_s(&tm_info, &t);
#else
    localtime_r(&t, &tm_info);
#endif
    return tm_info.tm_yday;
}
static inline bool pengu_c_get_local_is_dst(double ts) {
    time_t t = (time_t)ts; struct tm tm_info;
#if PENGU_WINDOWS
    localtime_s(&tm_info, &t);
#else
    localtime_r(&t, &tm_info);
#endif
    return tm_info.tm_isdst > 0;
}

/* 5. Lot */
static inline void pengu_c_srand(int seed) { srand((unsigned int)seed); }
static inline int pengu_c_rand(void) { return rand(); }
static inline int pengu_c_rand_max(void) { return RAND_MAX; }
static inline double pengu_c_rand_double(void) { return (double)rand() / ((double)RAND_MAX + 1.0); }
static inline int pengu_c_rand_range(int min, int max) {
    if (min >= max) return min;
    return min + (int)(pengu_c_rand_double() * (double)(max - min + 1));
}
static inline double pengu_c_rand_range_float(double min, double max) {
    if (min >= max) return min;
    return min + pengu_c_rand_double() * (max - min);
}
static inline double pengu_c_rand_normal(double mean, double stddev) {
    double u1 = pengu_c_rand_double();
    double u2 = pengu_c_rand_double();
    while (u1 <= 1e-15) u1 = pengu_c_rand_double();
    double z0 = sqrt(-2.0 * log(u1)) * cos(2.0 * 3.14159265358979323846 * u2);
    return mean + z0 * stddev;
}
static inline double pengu_c_rand_exp(double lambda) {
    if (lambda <= 0.0) return 0.0;
    double u = pengu_c_rand_double();
    while (u <= 1e-15) u = pengu_c_rand_double();
    return -log(u) / lambda;
}
static inline bool pengu_c_rand_bool(double probability) { return pengu_c_rand_double() < probability; }
static inline int pengu_c_rand_poisson(double lambda) {
    if (lambda <= 0.0) return 0;
    double L = exp(-lambda);
    double k = 0, p = 1.0;
    do { k += 1.0; p *= pengu_c_rand_double(); } while (p > L);
    return (int)(k - 1.0);
}

/* 6. Rites */
static inline PenguMaybe pengu_c_getenv(PenguString name) {
    if (!name.data || name.len == 0) return pengu_maybe_none();
    const char* val = getenv(name.data);
    if (!val) return pengu_maybe_none();
    PenguString* res = (PenguString*)malloc(sizeof(PenguString));
    *res = pengu_string_new(val);
    return pengu_maybe_some(res);
}
static inline bool pengu_c_setenv(PenguString name, PenguString value, bool overwrite) {
    if (!name.data || name.len == 0) return false;
#if PENGU_WINDOWS
    if (!overwrite && getenv(name.data) != NULL) return true;
    return _putenv_s(name.data, value.data ? value.data : "") == 0;
#else
    return setenv(name.data, value.data ? value.data : "", overwrite ? 1 : 0) == 0;
#endif
}
static inline bool pengu_c_unsetenv(PenguString name) {
    if (!name.data || name.len == 0) return false;
#if PENGU_WINDOWS
    return _putenv_s(name.data, "") == 0;
#else
    return unsetenv(name.data) == 0;
#endif
}
static inline int pengu_c_get_argc(void) { return g_pengu_argc; }
static inline PenguString pengu_c_get_argv(int idx) {
    if (idx < 0 || idx >= g_pengu_argc || !g_pengu_argv) return pengu_string_from_cstr("");
    return pengu_string_new(g_pengu_argv[idx]);
}
static inline PenguList pengu_c_get_args(void) {
    PenguList list = pengu_list_new(sizeof(PenguString), (size_t)(g_pengu_argc > 0 ? g_pengu_argc : 1));
    for (int i = 0; i < g_pengu_argc; ++i) {
        PenguString s = pengu_string_new(g_pengu_argv[i]);
        pengu_list_push(&list, &s);
    }
    return list;
}
static inline int pengu_c_getpid(void) {
#if PENGU_WINDOWS
    return (int)_getpid();
#else
    return (int)getpid();
#endif
}
static inline int pengu_c_getppid(void) {
#if PENGU_WINDOWS
    return 0;
#else
    return (int)getppid();
#endif
}
static inline PenguMaybe pengu_c_getcwd(void) {
    char buf[4096];
#if PENGU_WINDOWS
    if (_getcwd(buf, sizeof(buf)) != NULL) {
#else
    if (getcwd(buf, sizeof(buf)) != NULL) {
#endif
        PenguString* res = (PenguString*)malloc(sizeof(PenguString));
        *res = pengu_string_new(buf);
        return pengu_maybe_some(res);
    }
    return pengu_maybe_none();
}
static inline bool pengu_c_chdir(PenguString path) {
    if (!path.data || path.len == 0) return false;
#if PENGU_WINDOWS
    return _chdir(path.data) == 0;
#else
    return chdir(path.data) == 0;
#endif
}
static inline void pengu_c_exit(int code) { exit(code); }
static inline int pengu_c_exec(PenguString cmd, PenguList args) {
    if (!cmd.data || cmd.len == 0) return -1;
    char cmdbuf[4096];
    snprintf(cmdbuf, sizeof(cmdbuf), "%s", cmd.data);
    for (int i = 0; i < args.len; ++i) {
        PenguString* a = (PenguString*)pengu_list_at(&args, i);
        if (a && a->data) {
            strncat(cmdbuf, " ", sizeof(cmdbuf) - strlen(cmdbuf) - 1);
            strncat(cmdbuf, a->data, sizeof(cmdbuf) - strlen(cmdbuf) - 1);
        }
    }
    return system(cmdbuf);
}
static inline int pengu_c_spawn(PenguString cmd, PenguList args) {
    return pengu_c_exec(cmd, args);
}
static inline PenguString pengu_c_uname(void) {
#if PENGU_WINDOWS
    return pengu_string_from_cstr("Windows");
#elif defined(__APPLE__)
    return pengu_string_from_cstr("Darwin");
#elif defined(__linux__)
    return pengu_string_from_cstr("Linux");
#else
    return pengu_string_from_cstr("Unknown");
#endif
}
static inline PenguString pengu_c_hostname(void) {
    char buf[256];
#if PENGU_WINDOWS
    DWORD len = sizeof(buf);
    if (GetComputerNameA(buf, &len)) {
        return pengu_string_new(buf);
    }
#else
    if (gethostname(buf, sizeof(buf)) == 0) {
        return pengu_string_new(buf);
    }
#endif
    return pengu_string_from_cstr("localhost");
}
static inline PenguList pengu_c_get_env_keys(void) {
    PenguList list = pengu_list_new(sizeof(PenguString), 16);
#if PENGU_WINDOWS
    char* env = GetEnvironmentStringsA();
    if (env) {
        char* p = env;
        while (*p) {
            char* eq = strchr(p, '=');
            if (eq && eq != p) {
                int klen = (int)(eq - p);
                char kbuf[256];
                if (klen < (int)sizeof(kbuf)) {
                    memcpy(kbuf, p, (size_t)klen);
                    kbuf[klen] = '\0';
                    PenguString kstr = pengu_string_new(kbuf);
                    pengu_list_push(&list, &kstr);
                }
            }
            p += strlen(p) + 1;
        }
        FreeEnvironmentStringsA(env);
    }
#endif
    return list;
}
static inline void pengu_c_sleep_ms_rites(int ms) { pengu_c_sleep_ms(ms); }

/* 7. Scrolls */
static inline int scrolls_len(PenguString s) { return s.len; }
static inline bool scrolls_is_empty(PenguString s) { return s.len == 0; }
static inline bool scrolls_contains(PenguString s, PenguString sub) {
    if (!s.data || !sub.data) return false;
    return strstr(s.data, sub.data) != NULL;
}
static inline bool scrolls_starts_with(PenguString s, PenguString prefix) {
    if (!s.data || !prefix.data || prefix.len > s.len) return false;
    return memcmp(s.data, prefix.data, (size_t)prefix.len) == 0;
}
static inline bool scrolls_ends_with(PenguString s, PenguString suffix) {
    if (!s.data || !suffix.data || suffix.len > s.len) return false;
    return memcmp(s.data + (s.len - suffix.len), suffix.data, (size_t)suffix.len) == 0;
}
static inline int scrolls_index_of(PenguString s, PenguString sub) {
    if (!s.data || !sub.data) return -1;
    char* p = strstr(s.data, sub.data);
    return p ? (int)(p - s.data) : -1;
}
static inline int scrolls_last_index_of(PenguString s, PenguString sub) {
    if (!s.data || !sub.data || sub.len > s.len) return -1;
    for (int i = s.len - sub.len; i >= 0; --i) {
        if (memcmp(s.data + i, sub.data, (size_t)sub.len) == 0) return i;
    }
    return -1;
}
static inline PenguString scrolls_substring(PenguString s, int start, int end_pos) {
    if (!s.data || start < 0 || start >= s.len || end_pos <= start) return pengu_string_from_cstr("");
    if (end_pos > s.len) end_pos = s.len;
    int len = end_pos - start;
    char* buf = (char*)malloc((size_t)len + 1);
    if (!buf) return pengu_string_from_cstr("");
    memcpy(buf, s.data + start, (size_t)len);
    buf[len] = '\0';
    return (PenguString){ buf, len };
}
static inline PenguString scrolls_to_lower(PenguString s) {
    if (!s.data || s.len == 0) return pengu_string_from_cstr("");
    char* buf = (char*)malloc((size_t)s.len + 1);
    if (!buf) return pengu_string_from_cstr("");
    for (int i = 0; i < s.len; ++i) buf[i] = (char)tolower((unsigned char)s.data[i]);
    buf[s.len] = '\0';
    return (PenguString){ buf, s.len };
}
static inline PenguString scrolls_to_upper(PenguString s) {
    if (!s.data || s.len == 0) return pengu_string_from_cstr("");
    char* buf = (char*)malloc((size_t)s.len + 1);
    if (!buf) return pengu_string_from_cstr("");
    for (int i = 0; i < s.len; ++i) buf[i] = (char)toupper((unsigned char)s.data[i]);
    buf[s.len] = '\0';
    return (PenguString){ buf, s.len };
}
static inline PenguString scrolls_trim(PenguString s) {
    if (!s.data || s.len == 0) return pengu_string_from_cstr("");
    int start = 0;
    while (start < s.len && isspace((unsigned char)s.data[start])) start++;
    int end = s.len - 1;
    while (end >= start && isspace((unsigned char)s.data[end])) end--;
    return scrolls_substring(s, start, end + 1);
}
static inline PenguString scrolls_trim_left(PenguString s) {
    if (!s.data || s.len == 0) return pengu_string_from_cstr("");
    int start = 0;
    while (start < s.len && isspace((unsigned char)s.data[start])) start++;
    return scrolls_substring(s, start, s.len);
}
static inline PenguString scrolls_trim_right(PenguString s) {
    if (!s.data || s.len == 0) return pengu_string_from_cstr("");
    int end = s.len - 1;
    while (end >= 0 && isspace((unsigned char)s.data[end])) end--;
    return scrolls_substring(s, 0, end + 1);
}
static inline PenguString scrolls_replace(PenguString s, PenguString from_str, PenguString to_str) {
    int idx = scrolls_index_of(s, from_str);
    if (idx < 0) return s;
    PenguString p1 = scrolls_substring(s, 0, idx);
    PenguString p2 = scrolls_substring(s, idx + from_str.len, s.len);
    PenguString res = pengu_string_concat(pengu_string_concat(p1, to_str), p2);
    pengu_banish_string(&p1); pengu_banish_string(&p2);
    return res;
}
static inline PenguString scrolls_replace_all(PenguString s, PenguString from_str, PenguString to_str) {
    return scrolls_replace(s, from_str, to_str);
}
static inline PenguList scrolls_split(PenguString s, PenguString delim) {
    return pengu_string_split(s, delim);
}
static inline PenguString scrolls_join(PenguList parts, PenguString delim) {
    if (parts.len == 0) return pengu_string_from_cstr("");
    PenguString res = *(PenguString*)pengu_list_at(&parts, 0);
    res = pengu_string_new(res.data);
    for (int i = 1; i < parts.len; ++i) {
        PenguString* p = (PenguString*)pengu_list_at(&parts, i);
        if (delim.len > 0) res = pengu_string_concat(res, delim);
        if (p) res = pengu_string_concat(res, *p);
    }
    return res;
}
static inline PenguString scrolls_repeat(PenguString s, int count) {
    if (count <= 0 || !s.data || s.len == 0) return pengu_string_from_cstr("");
    int total_len = s.len * count;
    char* buf = (char*)malloc((size_t)total_len + 1);
    if (!buf) return pengu_string_from_cstr("");
    buf[0] = '\0';
    for (int i = 0; i < count; ++i) memcpy(buf + (i * s.len), s.data, (size_t)s.len);
    buf[total_len] = '\0';
    return (PenguString){ buf, total_len };
}
static inline PenguString scrolls_reverse(PenguString s) {
    if (!s.data || s.len == 0) return pengu_string_from_cstr("");
    char* buf = (char*)malloc((size_t)s.len + 1);
    if (!buf) return pengu_string_from_cstr("");
    for (int i = 0; i < s.len; ++i) buf[i] = s.data[s.len - 1 - i];
    buf[s.len] = '\0';
    return (PenguString){ buf, s.len };
}

/* 8. Compass */
static inline bool pengu_c_path_is_sep(char c) {
    return c == '/' || c == '\\';
}

static inline PenguString pengu_c_path_separator(void) {
#if PENGU_WINDOWS
    return pengu_string_from_cstr("\\");
#else
    return pengu_string_from_cstr("/");
#endif
}

static inline PenguMaybe pengu_c_path_alt_separator(void) {
#if PENGU_WINDOWS
    PenguString* s = (PenguString*)malloc(sizeof(PenguString));
    *s = pengu_string_from_cstr("/");
    return pengu_maybe_some(s);
#else
    return pengu_maybe_none();
#endif
}

static inline bool pengu_c_path_is_absolute(PenguString path) {
    if (!path.data || path.len == 0) return false;
#if PENGU_WINDOWS
    if (path.len >= 2 && isalpha((unsigned char)path.data[0]) && path.data[1] == ':') {
        if (path.len >= 3 && pengu_c_path_is_sep(path.data[2])) return true;
        return true;
    }
    if (pengu_c_path_is_sep(path.data[0])) return true;
    return false;
#else
    return path.data[0] == '/';
#endif
}

static inline bool pengu_c_path_is_root(PenguString path) {
    if (!path.data || path.len == 0) return false;
    if (path.len == 1 && pengu_c_path_is_sep(path.data[0])) return true;
#if PENGU_WINDOWS
    if (path.len == 2 && isalpha((unsigned char)path.data[0]) && path.data[1] == ':') return true;
    if (path.len == 3 && isalpha((unsigned char)path.data[0]) && path.data[1] == ':' && pengu_c_path_is_sep(path.data[2])) return true;
#endif
    return false;
}

static inline PenguString pengu_c_path_drive(PenguString path) {
#if PENGU_WINDOWS
    if (path.data && path.len >= 2 && isalpha((unsigned char)path.data[0]) && path.data[1] == ':') {
        char buf[3] = { path.data[0], ':', '\0' };
        return pengu_string_new(buf);
    }
#endif
    return pengu_string_from_cstr("");
}

static inline PenguString pengu_c_path_basename(PenguString path) {
    if (!path.data || path.len == 0) return pengu_string_from_cstr("");
    int end = path.len - 1;
    while (end > 0 && pengu_c_path_is_sep(path.data[end])) end--;
    if (end == 0 && pengu_c_path_is_sep(path.data[0])) return pengu_string_from_cstr("");
    int start = end;
    while (start >= 0 && !pengu_c_path_is_sep(path.data[start])) {
#if PENGU_WINDOWS
        if (start == 1 && path.data[start] == ':' && isalpha((unsigned char)path.data[0])) break;
#endif
        start--;
    }
    start++;
    int len = end - start + 1;
    if (len <= 0) return pengu_string_from_cstr("");
    char* buf = (char*)malloc((size_t)len + 1);
    memcpy(buf, path.data + start, (size_t)len);
    buf[len] = '\0';
    return (PenguString){ buf, len };
}

static inline PenguString pengu_c_path_dirname(PenguString path) {
    if (!path.data || path.len == 0) return pengu_string_from_cstr("");
    int end = path.len - 1;
    while (end > 0 && pengu_c_path_is_sep(path.data[end])) end--;
    while (end >= 0 && !pengu_c_path_is_sep(path.data[end])) {
#if PENGU_WINDOWS
        if (end == 1 && path.data[end] == ':' && isalpha((unsigned char)path.data[0])) break;
#endif
        end--;
    }
    if (end < 0) return pengu_string_from_cstr("");
    while (end > 0 && pengu_c_path_is_sep(path.data[end])) {
#if PENGU_WINDOWS
        if (end == 2 && path.data[1] == ':' && isalpha((unsigned char)path.data[0])) break;
#endif
        end--;
    }
    int len = end + 1;
    char* buf = (char*)malloc((size_t)len + 1);
    memcpy(buf, path.data, (size_t)len);
    buf[len] = '\0';
    return (PenguString){ buf, len };
}

static inline PenguString pengu_c_path_ext(PenguString path) {
    PenguString base = pengu_c_path_basename(path);
    if (!base.data || base.len == 0) return pengu_string_from_cstr("");
    int last_dot = -1;
    for (int i = base.len - 1; i >= 0; --i) {
        if (base.data[i] == '.') { last_dot = i; break; }
    }
    if (last_dot <= 0) return pengu_string_from_cstr("");
    int len = base.len - last_dot;
    char* buf = (char*)malloc((size_t)len + 1);
    memcpy(buf, base.data + last_dot, (size_t)len);
    buf[len] = '\0';
    return (PenguString){ buf, len };
}

static inline PenguString pengu_c_path_stem(PenguString path) {
    PenguString base = pengu_c_path_basename(path);
    if (!base.data || base.len == 0) return pengu_string_from_cstr("");
    int last_dot = -1;
    for (int i = base.len - 1; i >= 0; --i) {
        if (base.data[i] == '.') { last_dot = i; break; }
    }
    if (last_dot <= 0) return base;
    char* buf = (char*)malloc((size_t)last_dot + 1);
    memcpy(buf, base.data, (size_t)last_dot);
    buf[last_dot] = '\0';
    return (PenguString){ buf, last_dot };
}

static inline bool pengu_c_path_has_ext(PenguString path) {
    PenguString e = pengu_c_path_ext(path);
    return e.len > 0;
}

static inline bool pengu_c_path_has_suffix(PenguString path, PenguString suffix) {
    return scrolls_ends_with(path, suffix);
}

static inline PenguList pengu_c_path_suffixes(PenguString path) {
    PenguList list = pengu_list_new(sizeof(PenguString), 4);
    PenguString base = pengu_c_path_basename(path);
    if (!base.data || base.len == 0) return list;
    for (int i = 1; i < base.len; ++i) {
        if (base.data[i] == '.') {
            int next_dot = base.len;
            for (int j = i + 1; j < base.len; ++j) {
                if (base.data[j] == '.') { next_dot = j; break; }
            }
            int len = next_dot - (i + 1);
            if (len >= 0) {
                char* buf = (char*)malloc((size_t)len + 1);
                memcpy(buf, base.data + i + 1, (size_t)len);
                buf[len] = '\0';
                PenguString s = { buf, len };
                pengu_list_push(&list, &s);
            }
        }
    }
    return list;
}

static inline PenguString pengu_c_path_normalize(PenguString path) {
    if (!path.data || path.len == 0) return pengu_string_from_cstr(".");
    char sep =
#if PENGU_WINDOWS
        '\\';
#else
        '/';
#endif
    char drive[4] = {0};
    int p_idx = 0;
#if PENGU_WINDOWS
    if (path.len >= 2 && isalpha((unsigned char)path.data[0]) && path.data[1] == ':') {
        drive[0] = path.data[0];
        drive[1] = ':';
        drive[2] = '\0';
        p_idx = 2;
    }
#endif
    bool is_abs = (p_idx < path.len && pengu_c_path_is_sep(path.data[p_idx]));
    if (is_abs) p_idx++;

    char* stack[256];
    int top = 0;

    int cur_start = p_idx;
    for (int i = p_idx; i <= path.len; ++i) {
        if (i == path.len || pengu_c_path_is_sep(path.data[i])) {
            int seg_len = i - cur_start;
            if (seg_len > 0) {
                char* seg = (char*)malloc((size_t)seg_len + 1);
                memcpy(seg, path.data + cur_start, (size_t)seg_len);
                seg[seg_len] = '\0';
                if (strcmp(seg, ".") == 0) {
                    free(seg);
                } else if (strcmp(seg, "..") == 0) {
                    if (top > 0 && strcmp(stack[top - 1], "..") != 0) {
                        free(stack[--top]);
                        free(seg);
                    } else if (!is_abs) {
                        stack[top++] = seg;
                    } else {
                        free(seg);
                    }
                } else {
                    stack[top++] = seg;
                }
            }
            cur_start = i + 1;
        }
    }

    char buf[4096];
    buf[0] = '\0';
    if (drive[0]) strcat(buf, drive);
    if (is_abs) {
        char s_str[2] = { sep, '\0' };
        strcat(buf, s_str);
    }
    for (int i = 0; i < top; ++i) {
        if (i > 0 || (is_abs && buf[strlen(buf) - 1] != sep) || (!is_abs && buf[0] != '\0')) {
            char s_str[2] = { sep, '\0' };
            strcat(buf, s_str);
        }
        strcat(buf, stack[i]);
        free(stack[i]);
    }
    if (buf[0] == '\0') strcpy(buf, ".");
    return pengu_string_new(buf);
}

static inline PenguMaybe pengu_c_path_parent(PenguString path) {
    if (pengu_c_path_is_root(path)) return pengu_maybe_none();
    PenguString dir = pengu_c_path_dirname(path);
    if (dir.len == 0) return pengu_maybe_none();
    PenguString* res = (PenguString*)malloc(sizeof(PenguString));
    *res = dir;
    return pengu_maybe_some(res);
}

static inline PenguList pengu_c_path_split(PenguString path) {
    PenguList list = pengu_list_new(sizeof(PenguString), 8);
    if (!path.data || path.len == 0) return list;
    int p_idx = 0;
#if PENGU_WINDOWS
    if (path.len >= 2 && isalpha((unsigned char)path.data[0]) && path.data[1] == ':') {
        char d[3] = { path.data[0], ':', '\0' };
        PenguString dstr = pengu_string_new(d);
        pengu_list_push(&list, &dstr);
        p_idx = 2;
    }
#endif
    if (p_idx < path.len && pengu_c_path_is_sep(path.data[p_idx])) {
        PenguString r = pengu_string_from_cstr("/");
        pengu_list_push(&list, &r);
        p_idx++;
    }
    int cur_start = p_idx;
    for (int i = p_idx; i <= path.len; ++i) {
        if (i == path.len || pengu_c_path_is_sep(path.data[i])) {
            int seg_len = i - cur_start;
            if (seg_len > 0) {
                char* seg = (char*)malloc((size_t)seg_len + 1);
                memcpy(seg, path.data + cur_start, (size_t)seg_len);
                seg[seg_len] = '\0';
                PenguString s = { seg, seg_len };
                pengu_list_push(&list, &s);
            }
            cur_start = i + 1;
        }
    }
    return list;
}

static inline PenguString pengu_c_path_join(PenguList parts) {
    if (parts.len == 0) return pengu_string_from_cstr("");
    char sep =
#if PENGU_WINDOWS
        '\\';
#else
        '/';
#endif
    char buf[4096];
    buf[0] = '\0';
    for (int i = 0; i < parts.len; ++i) {
        PenguString* p = (PenguString*)pengu_list_at(&parts, i);
        if (!p || !p->data || p->len == 0) continue;
        if (pengu_c_path_is_absolute(*p)) {
            strcpy(buf, p->data);
        } else {
            int blen = (int)strlen(buf);
            if (blen > 0 && !pengu_c_path_is_sep(buf[blen - 1])) {
                buf[blen] = sep;
                buf[blen + 1] = '\0';
            }
            strcat(buf, p->data);
        }
    }
    return pengu_c_path_normalize(pengu_string_new(buf));
}

static inline PenguString pengu_c_path_change_ext(PenguString path, PenguString new_ext) {
    PenguString dir = pengu_c_path_dirname(path);
    PenguString stem = pengu_c_path_stem(path);
    char buf[4096];
    buf[0] = '\0';
    if (dir.len > 0) {
        snprintf(buf, sizeof(buf), "%.*s%c%.*s", dir.len, dir.data,
#if PENGU_WINDOWS
            '\\',
#else
            '/',
#endif
            stem.len, stem.data);
    } else {
        snprintf(buf, sizeof(buf), "%.*s", stem.len, stem.data);
    }
    if (new_ext.len > 0) {
        if (new_ext.data[0] != '.') strncat(buf, ".", sizeof(buf) - strlen(buf) - 1);
        strncat(buf, new_ext.data, sizeof(buf) - strlen(buf) - 1);
    }
    return pengu_string_new(buf);
}

static inline PenguString pengu_c_path_add_ext(PenguString path, PenguString ext) {
    if (pengu_c_path_has_ext(path) || ext.len == 0) return path;
    char buf[4096];
    snprintf(buf, sizeof(buf), "%.*s%s%.*s", path.len, path.data ? path.data : "", (ext.data[0] != '.' ? "." : ""), ext.len, ext.data);
    return pengu_string_new(buf);
}

static inline PenguMaybe pengu_c_path_relative_to(PenguString target, PenguString base) {
    PenguString norm_target = pengu_c_path_normalize(target);
    PenguString norm_base = pengu_c_path_normalize(base);
    PenguList t_parts = pengu_c_path_split(norm_target);
    PenguList b_parts = pengu_c_path_split(norm_base);
    if (t_parts.len == 0 || b_parts.len == 0) return pengu_maybe_none();
    
    int common = 0;
    while (common < t_parts.len && common < b_parts.len) {
        PenguString* p1 = (PenguString*)pengu_list_at(&t_parts, common);
        PenguString* p2 = (PenguString*)pengu_list_at(&b_parts, common);
        if (p1->len != p2->len || memcmp(p1->data, p2->data, (size_t)p1->len) != 0) break;
        common++;
    }
    if (common == 0 && pengu_c_path_is_absolute(norm_target)) return pengu_maybe_none();
    
    PenguList res_parts = pengu_list_new(sizeof(PenguString), 8);
    for (int i = common; i < b_parts.len; ++i) {
        PenguString dotdot = pengu_string_from_cstr("..");
        pengu_list_push(&res_parts, &dotdot);
    }
    for (int i = common; i < t_parts.len; ++i) {
        PenguString* p = (PenguString*)pengu_list_at(&t_parts, i);
        pengu_list_push(&res_parts, p);
    }
    PenguString joined = pengu_c_path_join(res_parts);
    PenguString* res = (PenguString*)malloc(sizeof(PenguString));
    *res = joined;
    return pengu_maybe_some(res);
}

/* =========================================================================
 * 9. Archivum (File System Operations)
 * ========================================================================= */

static inline PenguMaybe pengu_c_archivum_read_file(PenguString path) {
    if (!path.data || path.len == 0) return pengu_maybe_none();
    char *cpath = (char*)malloc((size_t)path.len + 1);
    if (!cpath) return pengu_maybe_none();
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
    FILE *f = fopen(cpath, "rb");
    free(cpath);
    if (!f) return pengu_maybe_none();
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (sz < 0) { fclose(f); return pengu_maybe_none(); }
    char *buf = (char*)malloc((size_t)sz + 1);
    if (!buf) { fclose(f); return pengu_maybe_none(); }
    size_t read_bytes = fread(buf, 1, (size_t)sz, f);
    fclose(f);
    buf[read_bytes] = '\0';
    PenguString *res = (PenguString*)malloc(sizeof(PenguString));
    if (!res) { free(buf); return pengu_maybe_none(); }
    res->data = buf;
    res->len = (int)read_bytes;
    return pengu_maybe_some(res);
}

static inline bool pengu_c_archivum_write_file(PenguString path, PenguString content) {
    if (!path.data) return false;
    char *cpath = (char*)malloc((size_t)path.len + 1);
    if (!cpath) return false;
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
    FILE *f = fopen(cpath, "wb");
    free(cpath);
    if (!f) return false;
    if (content.data && content.len > 0) {
        fwrite(content.data, 1, (size_t)content.len, f);
    }
    fclose(f);
    return true;
}

static inline bool pengu_c_archivum_append_file(PenguString path, PenguString content) {
    if (!path.data) return false;
    char *cpath = (char*)malloc((size_t)path.len + 1);
    if (!cpath) return false;
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
    FILE *f = fopen(cpath, "ab");
    free(cpath);
    if (!f) return false;
    if (content.data && content.len > 0) {
        fwrite(content.data, 1, (size_t)content.len, f);
    }
    fclose(f);
    return true;
}

static inline bool pengu_c_archivum_delete_file(PenguString path) {
    if (!path.data || path.len == 0) return false;
    char *cpath = (char*)malloc((size_t)path.len + 1);
    if (!cpath) return false;
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
    int res = remove(cpath);
    free(cpath);
    return res == 0;
}

static inline bool pengu_c_archivum_exists(PenguString path) {
    if (!path.data || path.len == 0) return false;
    char *cpath = (char*)malloc((size_t)path.len + 1);
    if (!cpath) return false;
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
#if PENGU_WINDOWS
    DWORD attr = GetFileAttributesA(cpath);
    free(cpath);
    return (attr != INVALID_FILE_ATTRIBUTES);
#else
    struct stat st;
    int res = stat(cpath, &st);
    free(cpath);
    return res == 0;
#endif
}

static inline bool pengu_c_archivum_is_file(PenguString path) {
    if (!path.data || path.len == 0) return false;
    char *cpath = (char*)malloc((size_t)path.len + 1);
    if (!cpath) return false;
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
#if PENGU_WINDOWS
    DWORD attr = GetFileAttributesA(cpath);
    free(cpath);
    return (attr != INVALID_FILE_ATTRIBUTES) && !(attr & FILE_ATTRIBUTE_DIRECTORY);
#else
    struct stat st;
    int res = stat(cpath, &st);
    free(cpath);
    return (res == 0) && S_ISREG(st.st_mode);
#endif
}

static inline bool pengu_c_archivum_is_dir(PenguString path) {
    if (!path.data || path.len == 0) return false;
    char *cpath = (char*)malloc((size_t)path.len + 1);
    if (!cpath) return false;
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
#if PENGU_WINDOWS
    DWORD attr = GetFileAttributesA(cpath);
    free(cpath);
    return (attr != INVALID_FILE_ATTRIBUTES) && (attr & FILE_ATTRIBUTE_DIRECTORY);
#else
    struct stat st;
    int res = stat(cpath, &st);
    free(cpath);
    return (res == 0) && S_ISDIR(st.st_mode);
#endif
}

static inline bool pengu_c_archivum_is_symlink(PenguString path) {
    if (!path.data || path.len == 0) return false;
    char *cpath = (char*)malloc((size_t)path.len + 1);
    if (!cpath) return false;
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
#if PENGU_WINDOWS
    DWORD attr = GetFileAttributesA(cpath);
    free(cpath);
    return (attr != INVALID_FILE_ATTRIBUTES) && (attr & FILE_ATTRIBUTE_REPARSE_POINT);
#else
    struct stat st;
    int res = lstat(cpath, &st);
    free(cpath);
    return (res == 0) && S_ISLNK(st.st_mode);
#endif
}

static inline bool pengu_c_archivum_create_dir(PenguString path, bool parents) {
    if (!path.data || path.len == 0) return false;
    char *cpath = (char*)malloc((size_t)path.len + 1);
    if (!cpath) return false;
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
    if (!parents) {
#if PENGU_WINDOWS
        int r = _mkdir(cpath);
#else
        int r = mkdir(cpath, 0755);
#endif
        free(cpath);
        return (r == 0 || pengu_c_archivum_is_dir(path));
    }
    for (int i = 0; i < path.len; ++i) {
        if (cpath[i] == '/' || cpath[i] == '\\') {
            if (i == 0 || (i == 2 && cpath[1] == ':')) continue;
            char tmp = cpath[i];
            cpath[i] = '\0';
#if PENGU_WINDOWS
            _mkdir(cpath);
#else
            mkdir(cpath, 0755);
#endif
            cpath[i] = tmp;
        }
    }
#if PENGU_WINDOWS
    _mkdir(cpath);
#else
    mkdir(cpath, 0755);
#endif
    bool ok = pengu_c_archivum_is_dir(path);
    free(cpath);
    return ok;
}

static inline PenguMaybe pengu_c_archivum_read_dir(PenguString path);

static inline bool pengu_c_archivum_remove_dir(PenguString path, bool recursive) {
    if (!path.data || path.len == 0) return false;
    if (!recursive) {
        char *cpath = (char*)malloc((size_t)path.len + 1);
        if (!cpath) return false;
        memcpy(cpath, path.data, (size_t)path.len);
        cpath[path.len] = '\0';
#if PENGU_WINDOWS
        int r = _rmdir(cpath);
#else
        int r = rmdir(cpath);
#endif
        free(cpath);
        return r == 0;
    }
    PenguMaybe m_entries = pengu_c_archivum_read_dir(path);
    if (m_entries.is_present && m_entries.value) {
        PenguList *entries = (PenguList*)m_entries.value;
        for (int i = 0; i < entries->len; ++i) {
            PenguString *name = (PenguString*)pengu_list_at(entries, i);
            char sep =
#if PENGU_WINDOWS
                '\\';
#else
                '/';
#endif
            char subpath[4096];
            snprintf(subpath, sizeof(subpath), "%.*s%c%.*s", path.len, path.data, sep, name->len, name->data);
            PenguString sub_str = pengu_string_from_cstr(subpath);
            if (pengu_c_archivum_is_dir(sub_str)) {
                pengu_c_archivum_remove_dir(sub_str, true);
            } else {
                pengu_c_archivum_delete_file(sub_str);
            }
        }
        free(m_entries.value);
    }
    return pengu_c_archivum_remove_dir(path, false);
}

static inline PenguMaybe pengu_c_archivum_read_dir(PenguString path) {
    if (!path.data || path.len == 0) return pengu_maybe_none();
    PenguList *list = (PenguList*)malloc(sizeof(PenguList));
    if (!list) return pengu_maybe_none();
    *list = pengu_list_new(sizeof(PenguString), 16);

#if PENGU_WINDOWS
    char pattern[4096];
    snprintf(pattern, sizeof(pattern), "%.*s\\*", path.len, path.data);
    WIN32_FIND_DATAA fd;
    HANDLE hFind = FindFirstFileA(pattern, &fd);
    if (hFind == INVALID_HANDLE_VALUE) {
        free(list);
        return pengu_maybe_none();
    }
    do {
        if (strcmp(fd.cFileName, ".") != 0 && strcmp(fd.cFileName, "..") != 0) {
            PenguString name = pengu_string_new(fd.cFileName);
            pengu_list_push(list, &name);
        }
    } while (FindNextFileA(hFind, &fd));
    FindClose(hFind);
#else
    char *cpath = (char*)malloc((size_t)path.len + 1);
    if (!cpath) { free(list); return pengu_maybe_none(); }
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
    DIR *d = opendir(cpath);
    free(cpath);
    if (!d) { free(list); return pengu_maybe_none(); }
    struct dirent *dir;
    while ((dir = readdir(d)) != NULL) {
        if (strcmp(dir->d_name, ".") != 0 && strcmp(dir->d_name, "..") != 0) {
            PenguString name = pengu_string_new(dir->d_name);
            pengu_list_push(list, &name);
        }
    }
    closedir(d);
#endif
    return pengu_maybe_some(list);
}

static inline bool pengu_c_archivum_copy_file(PenguString src, PenguString dst, bool overwrite) {
    if (!src.data || !dst.data) return false;
    if (!overwrite && pengu_c_archivum_exists(dst)) return false;
    PenguMaybe m_content = pengu_c_archivum_read_file(src);
    if (!m_content.is_present || !m_content.value) return false;
    PenguString *content = (PenguString*)m_content.value;
    bool ok = pengu_c_archivum_write_file(dst, *content);
    pengu_banish_string(content);
    free(content);
    return ok;
}

static inline bool pengu_c_archivum_move_file(PenguString src, PenguString dst, bool overwrite) {
    if (!src.data || !dst.data) return false;
    if (!overwrite && pengu_c_archivum_exists(dst)) return false;
    char *csrc = (char*)malloc((size_t)src.len + 1);
    char *cdst = (char*)malloc((size_t)dst.len + 1);
    if (!csrc || !cdst) { free(csrc); free(cdst); return false; }
    memcpy(csrc, src.data, (size_t)src.len); csrc[src.len] = '\0';
    memcpy(cdst, dst.data, (size_t)dst.len); cdst[dst.len] = '\0';
    if (overwrite) remove(cdst);
    int r = rename(csrc, cdst);
    free(csrc); free(cdst);
    if (r == 0) return true;
    if (pengu_c_archivum_copy_file(src, dst, overwrite)) {
        pengu_c_archivum_delete_file(src);
        return true;
    }
    return false;
}

static inline bool pengu_c_archivum_rename(PenguString old_p, PenguString new_p) {
    return pengu_c_archivum_move_file(old_p, new_p, true);
}

static inline PenguMaybe pengu_c_archivum_metadata(PenguString path) {
    if (!path.data || path.len == 0) return pengu_maybe_none();
    char *cpath = (char*)malloc((size_t)path.len + 1);
    if (!cpath) return pengu_maybe_none();
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
    struct stat st;
    int r = stat(cpath, &st);
    free(cpath);
    if (r != 0) return pengu_maybe_none();

    PenguMap *map = (PenguMap*)malloc(sizeof(PenguMap));
    if (!map) return pengu_maybe_none();
    *map = pengu_map_new(sizeof(PenguString), sizeof(PenguString));

    char buf[64];
    PenguString k, v;

    k = pengu_string_from_cstr("size");
    snprintf(buf, sizeof(buf), "%lld", (long long)st.st_size);
    v = pengu_string_from_cstr(buf);
    pengu_map_put(map, &k, &v);

    k = pengu_string_from_cstr("is_file");
    v = S_ISREG(st.st_mode) ? pengu_string_from_cstr("true") : pengu_string_from_cstr("false");
    pengu_map_put(map, &k, &v);

    k = pengu_string_from_cstr("is_dir");
    v = S_ISDIR(st.st_mode) ? pengu_string_from_cstr("true") : pengu_string_from_cstr("false");
    pengu_map_put(map, &k, &v);

    k = pengu_string_from_cstr("is_symlink");
    v = pengu_c_archivum_is_symlink(path) ? pengu_string_from_cstr("true") : pengu_string_from_cstr("false");
    pengu_map_put(map, &k, &v);

    k = pengu_string_from_cstr("modified");
    snprintf(buf, sizeof(buf), "%lld", (long long)st.st_mtime);
    v = pengu_string_from_cstr(buf);
    pengu_map_put(map, &k, &v);

    k = pengu_string_from_cstr("created");
    snprintf(buf, sizeof(buf), "%lld", (long long)st.st_ctime);
    v = pengu_string_from_cstr(buf);
    pengu_map_put(map, &k, &v);

    k = pengu_string_from_cstr("accessed");
    snprintf(buf, sizeof(buf), "%lld", (long long)st.st_atime);
    v = pengu_string_from_cstr(buf);
    pengu_map_put(map, &k, &v);

    k = pengu_string_from_cstr("permissions");
    snprintf(buf, sizeof(buf), "%d", (int)(st.st_mode & 0777));
    v = pengu_string_from_cstr(buf);
    pengu_map_put(map, &k, &v);

    return pengu_maybe_some(map);
}

static inline PenguMaybe pengu_c_archivum_read_lines(PenguString path) {
    PenguMaybe m_content = pengu_c_archivum_read_file(path);
    if (!m_content.is_present || !m_content.value) return pengu_maybe_none();
    PenguString *content = (PenguString*)m_content.value;
    PenguList *lines = (PenguList*)malloc(sizeof(PenguList));
    if (!lines) {
        pengu_banish_string(content);
        free(content);
        return pengu_maybe_none();
    }
    *lines = pengu_list_new(sizeof(PenguString), 16);
    int start = 0;
    for (int i = 0; i <= content->len; ++i) {
        if (i == content->len || content->data[i] == '\n') {
            int end = i;
            if (end > start && content->data[end - 1] == '\r') end--;
            int len = end - start;
            char *line_buf = (char*)malloc((size_t)len + 1);
            if (line_buf) {
                if (len > 0) memcpy(line_buf, content->data + start, (size_t)len);
                line_buf[len] = '\0';
                PenguString s = { line_buf, len };
                pengu_list_push(lines, &s);
            }
            start = i + 1;
        }
    }
    pengu_banish_string(content);
    free(content);
    return pengu_maybe_some(lines);
}

static inline bool pengu_c_archivum_write_lines(PenguString path, PenguList lines) {
    if (!path.data) return false;
    char *cpath = (char*)malloc((size_t)path.len + 1);
    if (!cpath) return false;
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
    FILE *f = fopen(cpath, "wb");
    free(cpath);
    if (!f) return false;
    for (int i = 0; i < lines.len; ++i) {
        PenguString *s = (PenguString*)pengu_list_at(&lines, i);
        if (s && s->data && s->len > 0) {
            fwrite(s->data, 1, (size_t)s->len, f);
        }
        fputc('\n', f);
    }
    fclose(f);
    return true;
}

static inline bool pengu_c_archivum_append_lines(PenguString path, PenguList lines) {
    if (!path.data) return false;
    char *cpath = (char*)malloc((size_t)path.len + 1);
    if (!cpath) return false;
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
    FILE *f = fopen(cpath, "ab");
    free(cpath);
    if (!f) return false;
    for (int i = 0; i < lines.len; ++i) {
        PenguString *s = (PenguString*)pengu_list_at(&lines, i);
        if (s && s->data && s->len > 0) {
            fwrite(s->data, 1, (size_t)s->len, f);
        }
        fputc('\n', f);
    }
    fclose(f);
    return true;
}

static inline void pengu_c_archivum_glob_rec(const char *dir_path, const char *pattern, PenguList *res) {
    PenguString p_str = pengu_string_from_cstr(dir_path);
    PenguMaybe m_entries = pengu_c_archivum_read_dir(p_str);
    if (!m_entries.is_present || !m_entries.value) return;
    PenguList *entries = (PenguList*)m_entries.value;
    for (int i = 0; i < entries->len; ++i) {
        PenguString *name = (PenguString*)pengu_list_at(entries, i);
        char full[4096];
        snprintf(full, sizeof(full), "%s/%s", dir_path, name->data);
        PenguString full_s = pengu_string_from_cstr(full);
        if (pengu_c_archivum_is_dir(full_s)) {
            pengu_c_archivum_glob_rec(full, pattern, res);
        }
        bool match = false;
        if (strcmp(pattern, "*") == 0 || strcmp(pattern, "**") == 0) {
            match = true;
        } else if (pattern[0] == '*' && pattern[1] == '.') {
            const char *ext = pattern + 1;
            if (name->len >= (int)strlen(ext) && strcmp(name->data + name->len - strlen(ext), ext) == 0) {
                match = true;
            }
        } else if (strstr(full, pattern) != NULL || strcmp(name->data, pattern) == 0) {
            match = true;
        }
        if (match) {
            PenguString match_str = pengu_string_new(full);
            pengu_list_push(res, &match_str);
        }
    }
    free(m_entries.value);
}

static inline PenguList pengu_c_archivum_glob(PenguString pattern) {
    PenguList list = pengu_list_new(sizeof(PenguString), 16);
    char *cpat = (char*)malloc((size_t)pattern.len + 1);
    if (!cpat) return list;
    memcpy(cpat, pattern.data, (size_t)pattern.len);
    cpat[pattern.len] = '\0';
    pengu_c_archivum_glob_rec(".", cpat, &list);
    free(cpat);
    return list;
}

static inline void pengu_c_archivum_walk_rec(const char *dir_path, PenguList *res) {
    PenguString p_str = pengu_string_from_cstr(dir_path);
    PenguMaybe m_entries = pengu_c_archivum_read_dir(p_str);
    if (!m_entries.is_present || !m_entries.value) return;
    PenguList *entries = (PenguList*)m_entries.value;

    PenguList node = pengu_list_new(sizeof(PenguString), 4);
    PenguString d_str = pengu_string_new(dir_path);
    pengu_list_push(&node, &d_str);

    for (int i = 0; i < entries->len; ++i) {
        PenguString *name = (PenguString*)pengu_list_at(entries, i);
        char sub[4096];
        snprintf(sub, sizeof(sub), "%s/%s", dir_path, name->data);
        PenguString sub_s = pengu_string_from_cstr(sub);
        if (pengu_c_archivum_is_dir(sub_s)) {
            pengu_c_archivum_walk_rec(sub, res);
        }
        PenguString item = pengu_string_new(name->data);
        pengu_list_push(&node, &item);
    }
    free(m_entries.value);
    pengu_list_push(res, &node);
}

static inline PenguList pengu_c_archivum_walk(PenguString root) {
    PenguList list = pengu_list_new(sizeof(PenguList), 8);
    char *croot = (char*)malloc((size_t)root.len + 1);
    if (!croot) return list;
    memcpy(croot, root.data, (size_t)root.len);
    croot[root.len] = '\0';
    pengu_c_archivum_walk_rec(croot, &list);
    free(croot);
    return list;
}

static inline bool pengu_c_archivum_touch(PenguString path) {
    if (!path.data || path.len == 0) return false;
    char *cpath = (char*)malloc((size_t)path.len + 1);
    if (!cpath) return false;
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
    FILE *f = fopen(cpath, "ab");
    if (f) {
        fclose(f);
#if PENGU_WINDOWS
        _utime(cpath, NULL);
#else
        utime(cpath, NULL);
#endif
        free(cpath);
        return true;
    }
    free(cpath);
    return false;
}

static inline bool pengu_c_archivum_symlink(PenguString target, PenguString link_p) {
    if (!target.data || !link_p.data) return false;
    char *ctarget = (char*)malloc((size_t)target.len + 1);
    char *clink = (char*)malloc((size_t)link_p.len + 1);
    if (!ctarget || !clink) { free(ctarget); free(clink); return false; }
    memcpy(ctarget, target.data, (size_t)target.len); ctarget[target.len] = '\0';
    memcpy(clink, link_p.data, (size_t)link_p.len); clink[link_p.len] = '\0';
#if PENGU_WINDOWS
    DWORD flags = pengu_c_archivum_is_dir(target) ? 1 : 0;
    BOOLEAN r = CreateSymbolicLinkA(clink, ctarget, flags);
    free(ctarget); free(clink);
    return r != 0;
#else
    int r = symlink(ctarget, clink);
    free(ctarget); free(clink);
    return r == 0;
#endif
}

static inline PenguMaybe pengu_c_archivum_read_symlink(PenguString path) {
    if (!path.data || path.len == 0) return pengu_maybe_none();
#if !PENGU_WINDOWS
    char *cpath = (char*)malloc((size_t)path.len + 1);
    if (!cpath) return pengu_maybe_none();
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
    char buf[4096];
    ssize_t len = readlink(cpath, buf, sizeof(buf) - 1);
    free(cpath);
    if (len >= 0) {
        buf[len] = '\0';
        PenguString *res = (PenguString*)malloc(sizeof(PenguString));
        if (res) {
            *res = pengu_string_new(buf);
            return pengu_maybe_some(res);
        }
    }
#endif
    return pengu_maybe_none();
}

static inline PenguMaybe pengu_c_archivum_realpath(PenguString path) {
    if (!path.data || path.len == 0) return pengu_maybe_none();
    char *cpath = (char*)malloc((size_t)path.len + 1);
    if (!cpath) return pengu_maybe_none();
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
    char buf[4096];
#if PENGU_WINDOWS
    DWORD len = GetFullPathNameA(cpath, sizeof(buf), buf, NULL);
    free(cpath);
    if (len > 0) {
        PenguString *res = (PenguString*)malloc(sizeof(PenguString));
        if (res) {
            *res = pengu_string_new(buf);
            return pengu_maybe_some(res);
        }
    }
#else
    char *res_ptr = realpath(cpath, buf);
    free(cpath);
    if (res_ptr) {
        PenguString *res = (PenguString*)malloc(sizeof(PenguString));
        if (res) {
            *res = pengu_string_new(buf);
            return pengu_maybe_some(res);
        }
    }
#endif
    return pengu_maybe_none();
}

/* =========================================================================
 * 10. Cipher (JSON & Base64 Encoding)
 * ========================================================================= */

static const char PENGU_B64_CHARS[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

static inline PenguString pengu_c_cipher_encode_base64(PenguString data) {
    if (!data.data || data.len == 0) return pengu_string_from_cstr("");
    size_t out_len = 4 * (((size_t)data.len + 2) / 3);
    char *out = (char*)malloc(out_len + 1);
    if (!out) return pengu_string_from_cstr("");
    size_t i = 0, j = 0;
    const unsigned char *bytes = (const unsigned char*)data.data;
    while (i < (size_t)data.len) {
        uint32_t octet_a = i < (size_t)data.len ? bytes[i++] : 0;
        uint32_t octet_b = i < (size_t)data.len ? bytes[i++] : 0;
        uint32_t octet_c = i < (size_t)data.len ? bytes[i++] : 0;
        uint32_t triple = (octet_a << 16) | (octet_b << 8) | octet_c;
        out[j++] = PENGU_B64_CHARS[(triple >> 18) & 0x3F];
        out[j++] = PENGU_B64_CHARS[(triple >> 12) & 0x3F];
        out[j++] = (i > (size_t)data.len + 1) ? '=' : PENGU_B64_CHARS[(triple >> 6) & 0x3F];
        out[j++] = (i > (size_t)data.len) ? '=' : PENGU_B64_CHARS[triple & 0x3F];
    }
    out[j] = '\0';
    return (PenguString){ out, (int)j };
}

static inline int pengu_b64_char_val(char c) {
    if (c >= 'A' && c <= 'Z') return c - 'A';
    if (c >= 'a' && c <= 'z') return c - 'a' + 26;
    if (c >= '0' && c <= '9') return c - '0' + 52;
    if (c == '+') return 62;
    if (c == '/') return 63;
    if (c == '=') return -1;
    return -2;
}

static inline PenguMaybe pengu_c_cipher_decode_base64(PenguString data) {
    if (!data.data || data.len == 0) {
        PenguString *res = (PenguString*)malloc(sizeof(PenguString));
        if (res) { *res = pengu_string_from_cstr(""); return pengu_maybe_some(res); }
        return pengu_maybe_none();
    }
    char *clean = (char*)malloc((size_t)data.len + 1);
    if (!clean) return pengu_maybe_none();
    int clen = 0;
    for (int i = 0; i < data.len; ++i) {
        if (!isspace((unsigned char)data.data[i])) {
            clean[clen++] = data.data[i];
        }
    }
    clean[clen] = '\0';
    if (clen % 4 != 0) { free(clean); return pengu_maybe_none(); }
    size_t out_len = ((size_t)clen / 4) * 3;
    if (clen > 0 && clean[clen - 1] == '=') out_len--;
    if (clen > 1 && clean[clen - 2] == '=') out_len--;
    char *out = (char*)malloc(out_len + 1);
    if (!out) { free(clean); return pengu_maybe_none(); }
    size_t j = 0;
    for (int i = 0; i < clen; i += 4) {
        int v0 = pengu_b64_char_val(clean[i]);
        int v1 = pengu_b64_char_val(clean[i + 1]);
        int v2 = pengu_b64_char_val(clean[i + 2]);
        int v3 = pengu_b64_char_val(clean[i + 3]);
        if (v0 < 0 || v1 < 0 || (v2 < 0 && clean[i+2] != '=') || (v3 < 0 && clean[i+3] != '=')) {
            free(clean); free(out); return pengu_maybe_none();
        }
        uint32_t triple = ((uint32_t)v0 << 18) | ((uint32_t)v1 << 12) | ((uint32_t)(v2 < 0 ? 0 : v2) << 6) | (uint32_t)(v3 < 0 ? 0 : v3);
        if (j < out_len) out[j++] = (char)((triple >> 16) & 0xFF);
        if (clean[i + 2] != '=' && j < out_len) out[j++] = (char)((triple >> 8) & 0xFF);
        if (clean[i + 3] != '=' && j < out_len) out[j++] = (char)(triple & 0xFF);
    }
    free(clean);
    out[j] = '\0';
    PenguString *res = (PenguString*)malloc(sizeof(PenguString));
    if (!res) { free(out); return pengu_maybe_none(); }
    res->data = out;
    res->len = (int)j;
    return pengu_maybe_some(res);
}

static inline void pengu_json_skip_ws(const char *s, int *idx, int len) {
    while (*idx < len && isspace((unsigned char)s[*idx])) (*idx)++;
}

static inline PenguString pengu_json_parse_str(const char *s, int *idx, int len) {
    if (*idx >= len || s[*idx] != '"') return pengu_string_from_cstr("");
    (*idx)++;
    char buf[4096];
    int blen = 0;
    while (*idx < len && s[*idx] != '"') {
        if (s[*idx] == '\\' && *idx + 1 < len) {
            (*idx)++;
            char esc = s[*idx];
            if (esc == 'n') buf[blen++] = '\n';
            else if (esc == 't') buf[blen++] = '\t';
            else if (esc == 'r') buf[blen++] = '\r';
            else if (esc == '"') buf[blen++] = '"';
            else if (esc == '\\') buf[blen++] = '\\';
            else if (esc == '/') buf[blen++] = '/';
            else buf[blen++] = esc;
        } else {
            buf[blen++] = s[*idx];
        }
        (*idx)++;
    }
    if (*idx < len && s[*idx] == '"') (*idx)++;
    buf[blen] = '\0';
    return pengu_string_new(buf);
}

static inline PenguString pengu_json_parse_val_str(const char *s, int *idx, int len) {
    pengu_json_skip_ws(s, idx, len);
    if (*idx >= len) return pengu_string_from_cstr("");
    if (s[*idx] == '"') {
        return pengu_json_parse_str(s, idx, len);
    }
    int start = *idx;
    if (s[*idx] == '{' || s[*idx] == '[') {
        char open = s[*idx];
        char close = (open == '{') ? '}' : ']';
        int depth = 0;
        bool in_q = false;
        while (*idx < len) {
            if (s[*idx] == '"' && (*idx == 0 || s[*idx - 1] != '\\')) in_q = !in_q;
            if (!in_q) {
                if (s[*idx] == open) depth++;
                else if (s[*idx] == close) {
                    depth--;
                    if (depth == 0) { (*idx)++; break; }
                }
            }
            (*idx)++;
        }
    } else {
        while (*idx < len && s[*idx] != ',' && s[*idx] != '}' && s[*idx] != ']' && !isspace((unsigned char)s[*idx])) {
            (*idx)++;
        }
    }
    int vlen = *idx - start;
    char *buf = (char*)malloc((size_t)vlen + 1);
    if (buf) {
        memcpy(buf, s + start, (size_t)vlen);
        buf[vlen] = '\0';
        return (PenguString){ buf, vlen };
    }
    return pengu_string_from_cstr("");
}

static inline PenguMaybe pengu_c_cipher_parse_json(PenguString json) {
    if (!json.data || json.len == 0) return pengu_maybe_none();
    int idx = 0;
    pengu_json_skip_ws(json.data, &idx, json.len);
    if (idx >= json.len || json.data[idx] != '{') return pengu_maybe_none();
    idx++;
    PenguMap *map = (PenguMap*)malloc(sizeof(PenguMap));
    if (!map) return pengu_maybe_none();
    *map = pengu_map_new(sizeof(PenguString), sizeof(PenguString));

    while (idx < json.len) {
        pengu_json_skip_ws(json.data, &idx, json.len);
        if (idx < json.len && json.data[idx] == '}') { idx++; break; }
        if (json.data[idx] != '"') { free(map); return pengu_maybe_none(); }
        PenguString key = pengu_json_parse_str(json.data, &idx, json.len);
        pengu_json_skip_ws(json.data, &idx, json.len);
        if (idx >= json.len || json.data[idx] != ':') { free(map); return pengu_maybe_none(); }
        idx++;
        PenguString val = pengu_json_parse_val_str(json.data, &idx, json.len);
        pengu_map_put(map, &key, &val);
        pengu_json_skip_ws(json.data, &idx, json.len);
        if (idx < json.len && json.data[idx] == ',') idx++;
        else if (idx < json.len && json.data[idx] == '}') { idx++; break; }
    }
    return pengu_maybe_some(map);
}

static inline PenguMaybe pengu_c_cipher_stringify_json(PenguMap data) {
    char buf[65536];
    buf[0] = '{';
    int blen = 1;
    bool first = true;
    for (int i = 0; i < data.cap; ++i) {
        if (data.entries[i].occupied) {
            if (!first) { buf[blen++] = ','; }
            first = false;
            PenguString *k = (PenguString*)data.entries[i].key;
            PenguString *v = (PenguString*)data.entries[i].val;
            buf[blen++] = '"';
            if (k && k->data) {
                memcpy(buf + blen, k->data, (size_t)k->len);
                blen += k->len;
            }
            buf[blen++] = '"';
            buf[blen++] = ':';
            if (v && v->data) {
                bool is_literal = false;
                if (v->len > 0 && (v->data[0] == '{' || v->data[0] == '[' || strcmp(v->data, "true") == 0 || strcmp(v->data, "false") == 0 || strcmp(v->data, "null") == 0 || isdigit((unsigned char)v->data[0]) || (v->data[0] == '-' && v->len > 1 && isdigit((unsigned char)v->data[1])))) {
                    is_literal = true;
                }
                if (is_literal) {
                    memcpy(buf + blen, v->data, (size_t)v->len);
                    blen += v->len;
                } else {
                    buf[blen++] = '"';
                    memcpy(buf + blen, v->data, (size_t)v->len);
                    blen += v->len;
                    buf[blen++] = '"';
                }
            } else {
                buf[blen++] = '"'; buf[blen++] = '"';
            }
        }
    }
    buf[blen++] = '}';
    buf[blen] = '\0';
    PenguString *res = (PenguString*)malloc(sizeof(PenguString));
    if (!res) return pengu_maybe_none();
    *res = pengu_string_new(buf);
    return pengu_maybe_some(res);
}

static inline PenguMaybe pengu_c_cipher_parse_value(PenguString json) {
    if (!json.data || json.len == 0) return pengu_maybe_none();
    int idx = 0;
    PenguString val = pengu_json_parse_val_str(json.data, &idx, json.len);
    PenguString *res = (PenguString*)malloc(sizeof(PenguString));
    if (!res) return pengu_maybe_none();
    *res = val;
    return pengu_maybe_some(res);
}

static inline PenguMaybe pengu_c_cipher_stringify_value(PenguString value) {
    PenguString *res = (PenguString*)malloc(sizeof(PenguString));
    if (!res) return pengu_maybe_none();
    *res = pengu_string_new(value.data ? value.data : "");
    return pengu_maybe_some(res);
}

static inline PenguMaybe pengu_c_cipher_pretty_json(PenguMap data, int indent) {
    char buf[65536];
    buf[0] = '{';
    buf[1] = '\n';
    int blen = 2;
    bool first = true;
    for (int i = 0; i < data.cap; ++i) {
        if (data.entries[i].occupied) {
            if (!first) { buf[blen++] = ','; buf[blen++] = '\n'; }
            first = false;
            for (int k = 0; k < indent; ++k) buf[blen++] = ' ';
            PenguString *k_str = (PenguString*)data.entries[i].key;
            PenguString *v_str = (PenguString*)data.entries[i].val;
            buf[blen++] = '"';
            if (k_str && k_str->data) {
                memcpy(buf + blen, k_str->data, (size_t)k_str->len);
                blen += k_str->len;
            }
            buf[blen++] = '"';
            buf[blen++] = ':';
            buf[blen++] = ' ';
            if (v_str && v_str->data) {
                bool is_literal = false;
                if (v_str->len > 0 && (v_str->data[0] == '{' || v_str->data[0] == '[' || strcmp(v_str->data, "true") == 0 || strcmp(v_str->data, "false") == 0 || strcmp(v_str->data, "null") == 0 || isdigit((unsigned char)v_str->data[0]) || (v_str->data[0] == '-' && v_str->len > 1 && isdigit((unsigned char)v_str->data[1])))) {
                    is_literal = true;
                }
                if (is_literal) {
                    memcpy(buf + blen, v_str->data, (size_t)v_str->len);
                    blen += v_str->len;
                } else {
                    buf[blen++] = '"';
                    memcpy(buf + blen, v_str->data, (size_t)v_str->len);
                    blen += v_str->len;
                    buf[blen++] = '"';
                }
            } else {
                buf[blen++] = '"'; buf[blen++] = '"';
            }
        }
    }
    buf[blen++] = '\n';
    buf[blen++] = '}';
    buf[blen] = '\0';
    PenguString *res = (PenguString*)malloc(sizeof(PenguString));
    if (!res) return pengu_maybe_none();
    *res = pengu_string_new(buf);
    return pengu_maybe_some(res);
}

/* =========================================================================
 * 11. Ledger (CSV / TSV Processing)
 * ========================================================================= */

static inline PenguString pengu_c_ledger_escape_field(PenguString field, PenguString delimiter) {
    if (!field.data || field.len == 0) return pengu_string_from_cstr("");
    char d = (delimiter.data && delimiter.len > 0) ? delimiter.data[0] : ',';
    bool needs_quotes = false;
    for (int i = 0; i < field.len; ++i) {
        if (field.data[i] == d || field.data[i] == '"' || field.data[i] == '\n' || field.data[i] == '\r') {
            needs_quotes = true;
            break;
        }
    }
    if (!needs_quotes) return field;
    char buf[4096];
    int blen = 0;
    buf[blen++] = '"';
    for (int i = 0; i < field.len; ++i) {
        if (field.data[i] == '"') {
            buf[blen++] = '"';
            buf[blen++] = '"';
        } else {
            buf[blen++] = field.data[i];
        }
    }
    buf[blen++] = '"';
    buf[blen] = '\0';
    return pengu_string_new(buf);
}

static inline PenguMaybe pengu_c_ledger_parse_line(PenguString line, PenguString delimiter) {
    if (!line.data) return pengu_maybe_none();
    char d = (delimiter.data && delimiter.len > 0) ? delimiter.data[0] : ',';
    PenguList *fields = (PenguList*)malloc(sizeof(PenguList));
    if (!fields) return pengu_maybe_none();
    *fields = pengu_list_new(sizeof(PenguString), 8);

    char buf[4096];
    int blen = 0;
    bool in_quotes = false;
    for (int i = 0; i <= line.len; ++i) {
        if (i == line.len) {
            buf[blen] = '\0';
            PenguString s = pengu_string_new(buf);
            pengu_list_push(fields, &s);
            break;
        }
        char c = line.data[i];
        if (c == '"') {
            if (in_quotes && i + 1 < line.len && line.data[i + 1] == '"') {
                buf[blen++] = '"';
                i++;
            } else {
                in_quotes = !in_quotes;
            }
        } else if (c == d && !in_quotes) {
            buf[blen] = '\0';
            PenguString s = pengu_string_new(buf);
            pengu_list_push(fields, &s);
            blen = 0;
        } else if ((c == '\r' || c == '\n') && !in_quotes) {
            buf[blen] = '\0';
            PenguString s = pengu_string_new(buf);
            pengu_list_push(fields, &s);
            break;
        } else {
            buf[blen++] = c;
        }
    }
    return pengu_maybe_some(fields);
}

static inline PenguMaybe pengu_c_ledger_parse_csv(PenguString data, PenguString delimiter, bool has_header) {
    (void)has_header;
    if (!data.data || data.len == 0) {
        PenguList *empty = (PenguList*)malloc(sizeof(PenguList));
        if (!empty) return pengu_maybe_none();
        *empty = pengu_list_new(sizeof(PenguList), 4);
        return pengu_maybe_some(empty);
    }
    char d = (delimiter.data && delimiter.len > 0) ? delimiter.data[0] : ',';
    PenguList *rows = (PenguList*)malloc(sizeof(PenguList));
    if (!rows) return pengu_maybe_none();
    *rows = pengu_list_new(sizeof(PenguList), 16);

    PenguList cur_row = pengu_list_new(sizeof(PenguString), 8);
    char buf[4096];
    int blen = 0;
    bool in_quotes = false;

    for (int i = 0; i <= data.len; ++i) {
        if (i == data.len) {
            if (blen > 0 || cur_row.len > 0) {
                buf[blen] = '\0';
                PenguString s = pengu_string_new(buf);
                pengu_list_push(&cur_row, &s);
                pengu_list_push(rows, &cur_row);
            }
            break;
        }
        char c = data.data[i];
        if (c == '"') {
            if (in_quotes && i + 1 < data.len && data.data[i + 1] == '"') {
                buf[blen++] = '"';
                i++;
            } else {
                in_quotes = !in_quotes;
            }
        } else if (c == d && !in_quotes) {
            buf[blen] = '\0';
            PenguString s = pengu_string_new(buf);
            pengu_list_push(&cur_row, &s);
            blen = 0;
        } else if (c == '\n' && !in_quotes) {
            if (blen > 0 && buf[blen - 1] == '\r') blen--;
            buf[blen] = '\0';
            PenguString s = pengu_string_new(buf);
            pengu_list_push(&cur_row, &s);
            pengu_list_push(rows, &cur_row);
            cur_row = pengu_list_new(sizeof(PenguString), 8);
            blen = 0;
        } else if (c == '\r' && !in_quotes) {
            if (i + 1 < data.len && data.data[i + 1] == '\n') {
                // Handled on newline
            } else {
                buf[blen] = '\0';
                PenguString s = pengu_string_new(buf);
                pengu_list_push(&cur_row, &s);
                pengu_list_push(rows, &cur_row);
                cur_row = pengu_list_new(sizeof(PenguString), 8);
                blen = 0;
            }
        } else {
            buf[blen++] = c;
        }
    }
    return pengu_maybe_some(rows);
}

static inline PenguMaybe pengu_c_ledger_generate_csv(PenguList rows, PenguString delimiter) {
    char d = (delimiter.data && delimiter.len > 0) ? delimiter.data[0] : ',';
    char buf[65536];
    int blen = 0;
    buf[0] = '\0';

    for (int r = 0; r < rows.len; ++r) {
        PenguList *row = (PenguList*)pengu_list_at(&rows, r);
        if (!row) continue;
        for (int c = 0; c < row->len; ++c) {
            if (c > 0) buf[blen++] = d;
            PenguString *field = (PenguString*)pengu_list_at(row, c);
            if (field) {
                PenguString esc = pengu_c_ledger_escape_field(*field, delimiter);
                if (esc.data && esc.len > 0) {
                    memcpy(buf + blen, esc.data, (size_t)esc.len);
                    blen += esc.len;
                }
            }
        }
        buf[blen++] = '\n';
    }
    buf[blen] = '\0';
    PenguString *res = (PenguString*)malloc(sizeof(PenguString));
    if (!res) return pengu_maybe_none();
    *res = pengu_string_new(buf);
    return pengu_maybe_some(res);
}

static inline PenguMaybe pengu_c_ledger_read_file(PenguString path, PenguString delimiter, bool has_header) {
    PenguMaybe m_content = pengu_c_archivum_read_file(path);
    if (!m_content.is_present || !m_content.value) return pengu_maybe_none();
    PenguString *content = (PenguString*)m_content.value;
    PenguMaybe res = pengu_c_ledger_parse_csv(*content, delimiter, has_header);
    pengu_banish_string(content);
    free(content);
    return res;
}

static inline bool pengu_c_ledger_write_file(PenguString path, PenguList rows, PenguString delimiter) {
    PenguMaybe m_csv = pengu_c_ledger_generate_csv(rows, delimiter);
    if (!m_csv.is_present || !m_csv.value) return false;
    PenguString *csv = (PenguString*)m_csv.value;
    bool ok = pengu_c_archivum_write_file(path, *csv);
    pengu_banish_string(csv);
    free(csv);
    return ok;
}

static inline PenguMaybe pengu_c_ledger_detect_delimiter(PenguString data) {
    if (!data.data || data.len == 0) return pengu_maybe_none();
    int commas = 0, tabs = 0, semis = 0, pipes = 0;
    bool in_q = false;
    for (int i = 0; i < data.len && data.data[i] != '\n'; ++i) {
        if (data.data[i] == '"') in_q = !in_q;
        if (!in_q) {
            if (data.data[i] == ',') commas++;
            else if (data.data[i] == '\t') tabs++;
            else if (data.data[i] == ';') semis++;
            else if (data.data[i] == '|') pipes++;
        }
    }
    const char *chosen = ",";
    int max_c = commas;
    if (tabs > max_c) { max_c = tabs; chosen = "\t"; }
    if (semis > max_c) { max_c = semis; chosen = ";"; }
    if (pipes > max_c) { max_c = pipes; chosen = "|"; }
    PenguString *res = (PenguString*)malloc(sizeof(PenguString));
    if (!res) return pengu_maybe_none();
    *res = pengu_string_from_cstr(chosen);
    return pengu_maybe_some(res);
}

/* =========================================================================
 * 12. Filum (Concurrency Primitives)
 * ========================================================================= */

void pengu_c_filum_go(void* f);
void* pengu_c_filum_chan_new(int elem_size, int cap);
bool pengu_c_filum_chan_send(void* c, void* value);
bool pengu_c_filum_chan_recv(void* c, void* out);
void pengu_c_filum_chan_close(void* c);
int pengu_c_filum_chan_len(void* c);
int pengu_c_filum_chan_cap(void* c);

void* pengu_c_filum_mutex_new(void);
void pengu_c_filum_mutex_lock(void* m);
void pengu_c_filum_mutex_unlock(void* m);
bool pengu_c_filum_mutex_try_lock(void* m);

void* pengu_c_filum_wait_group_new(void);
void pengu_c_filum_wait_group_add(void* wg, int delta);
void pengu_c_filum_wait_group_done(void* wg);
void pengu_c_filum_wait_group_wait(void* wg);

void* pengu_c_filum_once_new(void);
void pengu_c_filum_once_do(void* o, void* f);

void* pengu_c_filum_cond_new(void);
void pengu_c_filum_cond_wait(void* c, void* m);
void pengu_c_filum_cond_signal(void* c);
void pengu_c_filum_cond_broadcast(void* c);

void* pengu_c_filum_atomic_int_new(int initial);
int pengu_c_filum_atomic_int_load(void* a);
void pengu_c_filum_atomic_int_store(void* a, int val);
int pengu_c_filum_atomic_int_add(void* a, int delta);
int pengu_c_filum_atomic_int_swap(void* a, int new_val);
bool pengu_c_filum_atomic_int_compare_swap(void* a, int old_val, int new_val);

void pengu_c_filum_sleep(int ms);
int pengu_c_filum_num_cpu(void);
int pengu_c_filum_goroutine_id(void);

/* =========================================================================
 * 13. Regulus (Regular Expressions)
 * ========================================================================= */

typedef struct {
    int32_t start;
    int32_t end;
    PenguString matched;
} PenguRegulusMatch;

typedef struct {
    PenguString pattern;
    PenguString flags;
    void* _ptr;
} PenguRegulusRegex;

PenguMaybe pengu_c_regulus_compile(PenguString pattern, PenguString flags);
PenguMaybe pengu_c_regulus_match(void* regex, PenguString text);
PenguMaybe pengu_c_regulus_search(void* regex, PenguString text);
PenguList pengu_c_regulus_find_all(void* regex, PenguString text);
PenguString pengu_c_regulus_replace(void* regex, PenguString text, PenguString replacement);
PenguList pengu_c_regulus_split(void* regex, PenguString text, int limit);
static inline PenguString pengu_c_regulus_escape(PenguString text) { return text; }
static inline bool pengu_c_regulus_is_valid(void* regex) { return regex != NULL; }

/* =========================================================================
 * 14. Parchment (XML / HTML Processing)
 * ========================================================================= */

typedef struct {
    PenguString tag;
    PenguString text;
    void* _ptr;
} PenguParchmentNode;

typedef struct {
    PenguParchmentNode root;
    PenguString version;
    PenguString encoding;
} PenguParchmentDocument;

PenguMaybe pengu_c_parchment_parse_xml(PenguString data);
PenguMaybe pengu_c_parchment_parse_html(PenguString data);
PenguMaybe pengu_c_parchment_to_string(void* node, bool pretty);
PenguMaybe pengu_c_parchment_find(void* node, PenguString query);
PenguList pengu_c_parchment_find_all(void* node, PenguString query);
PenguMaybe pengu_c_parchment_attr(void* node, PenguString name);
void pengu_c_parchment_set_attr(void* node, PenguString name, PenguString value);
PenguMaybe pengu_c_parchment_text(void* node);
void pengu_c_parchment_set_text(void* node, PenguString text);
void* pengu_c_parchment_create_element(PenguString tag);
void* pengu_c_parchment_create_text(PenguString text);
void pengu_c_parchment_append_child(void* parent, void* child);
static inline PenguString pengu_c_parchment_escape_text(PenguString text) { return text; }
static inline PenguString pengu_c_parchment_unescape_text(PenguString text) { return text; }

/* =========================================================================
 * 15. Seal (Compression & Hashing)
 * ========================================================================= */

int pengu_c_seal_crc32(PenguString data);
PenguString pengu_c_seal_md5(PenguString data);
PenguString pengu_c_seal_sha1(PenguString data);
PenguString pengu_c_seal_sha256(PenguString data);
PenguString pengu_c_seal_sha512(PenguString data);
PenguMaybe pengu_c_seal_gzip(PenguString data);
PenguMaybe pengu_c_seal_unzip(PenguString data);
PenguMaybe pengu_c_seal_zlib_compress(PenguString data);
PenguMaybe pengu_c_seal_zlib_decompress(PenguString data);
PenguMaybe pengu_c_seal_hash_file(PenguString path, PenguString hash_type);

/* =========================================================================
 * 16. Precis (Networking & HTTP)
 * ========================================================================= */

typedef struct {
    int status_code;
    PenguMap headers;
    PenguMaybe body;
    PenguString url;
} PenguPrecisClientResponse;

typedef struct {
    PenguString method;
    PenguString path;
    PenguMap headers;
    PenguMaybe body;
    PenguMap query;
} PenguPrecisRequest;

typedef struct {
    int status_code;
    PenguMap headers;
    PenguMaybe body;
} PenguPrecisResponse;

typedef struct {
    void* _ptr;
} PenguPrecisTCPSocket;

PenguMaybe pengu_c_precis_http_get(PenguString url, PenguMap headers);
PenguMaybe pengu_c_precis_http_post(PenguString url, PenguMap headers, PenguString body);
PenguMaybe pengu_c_precis_http_put(PenguString url, PenguMap headers, PenguString body);
PenguMaybe pengu_c_precis_http_delete(PenguString url, PenguMap headers);
PenguMaybe pengu_c_precis_http_request(PenguString method, PenguString url, PenguMap headers, PenguMaybe body);

void pengu_c_precis_serve_http(int port, void* handler);

PenguMaybe pengu_c_precis_tcp_connect(PenguString host, int port);
bool pengu_c_precis_tcp_send(void* sock, PenguString data);
PenguMaybe pengu_c_precis_tcp_recv(void* sock, int size);
void pengu_c_precis_tcp_close(void* sock);

PenguMaybe pengu_c_precis_dns_lookup(PenguString host);

PenguString pengu_c_precis_url_encode(PenguString s);
PenguString pengu_c_precis_url_decode(PenguString s);
PenguMap pengu_c_precis_parse_query(PenguString s);

#ifdef __cplusplus
}
#endif

#endif /* PENGU_RUNTIME_H */


