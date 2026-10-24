/*
 * toml_min.h - a small, dependency-free TOML 1.0 reader for std.toml.
 *
 * The parser produces a flat list of entries:
 *
 *   key                     value      kind
 *   package                 ""         6 (table marker)
 *   package.name            "demo"     1 (string)
 *   package.version         "0.1.0"    1
 *   dependencies            ""         6
 *   dependencies.spark      "^1.0"     1
 *   package[0]              ""         6 (array-of-tables element)
 *   package[0].name         "leaf"     1
 *   build.links[0]          "m"        1
 *
 * Kinds: 1 string, 2 int, 3 float, 4 bool, 5 array, 6 table,
 *        7 array-of-tables root.  Every array/table marker is emitted before
 * its members, so consumers can reconstruct nesting by key prefix.
 *
 * Supported syntax: comments, bare/quoted/dotted keys, basic/literal and
 * multiline strings with the standard escapes, integers (decimal/hex/octal/
 * binary with underscores), floats (including inf/nan), booleans, arrays
 * (nested and multiline), inline tables, [tables] and [[arrays of tables]].
 * Date/time values are returned as strings (kind 1), which is enough for
 * manifests and lockfiles and avoids a second calendar implementation.
 *
 * This header is intentionally self-contained: std/toml.pengu includes it, and
 * build_runtime.py copies the headers in std_c into build/include, so a released Pengu
 * install compiles the module without Python or an external TOML library.
 */
#ifndef PENGU_TOML_MIN_H
#define PENGU_TOML_MIN_H

#include <ctype.h>
#include <errno.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define PENGU_TOML_STRING 1
#define PENGU_TOML_INT 2
#define PENGU_TOML_FLOAT 3
#define PENGU_TOML_BOOL 4
#define PENGU_TOML_ARRAY 5
#define PENGU_TOML_TABLE 6
#define PENGU_TOML_ARRAY_TABLE 7

typedef struct PenguTomlEntry
{
  char *key;
  char *value;
  int kind;
  int line;
} PenguTomlEntry;

typedef struct PenguTomlDoc
{
  PenguTomlEntry *entries;
  int count;
  int cap;
  char error[256];
} PenguTomlDoc;

typedef struct PenguTomlCounter
{
  char *path;
  int count;
  struct PenguTomlCounter *next;
} PenguTomlCounter;

typedef struct PenguTomlBuf
{
  char *data;
  size_t len;
  size_t cap;
  int oom;
} PenguTomlBuf;

typedef struct PenguTomlParser
{
  const char *src;
  size_t len;
  size_t pos;
  int line;
  int col;
  int failed;
  PenguTomlDoc *doc;
  char *prefix;
  PenguTomlCounter *counters;
} PenguTomlParser;

static void pengu_toml_buf_init(PenguTomlBuf *b)
{
  b->data = NULL;
  b->len = 0;
  b->cap = 0;
  b->oom = 0;
}

static void pengu_toml_buf_free(PenguTomlBuf *b)
{
  free(b->data);
  b->data = NULL;
  b->len = 0;
  b->cap = 0;
}

static int pengu_toml_buf_reserve(PenguTomlBuf *b, size_t extra)
{
  if (b->oom)
    return 0;
  if (b->len + extra + 1 > b->cap)
  {
    size_t cap = (b->cap > 0) ? b->cap : 32;
    while (cap < b->len + extra + 1)
      cap *= 2;
    char *nd = (char *)realloc(b->data, cap);
    if (!nd)
    {
      b->oom = 1;
      return 0;
    }
    b->data = nd;
    b->cap = cap;
  }
  return 1;
}

static void pengu_toml_buf_putc(PenguTomlBuf *b, char c)
{
  if (!pengu_toml_buf_reserve(b, 1))
    return;
  b->data[b->len++] = c;
  b->data[b->len] = '\0';
}

static void pengu_toml_buf_put_utf8(PenguTomlBuf *b, uint32_t cp)
{
  if (cp <= 0x7f)
    pengu_toml_buf_putc(b, (char)cp);
  else if (cp <= 0x7ff)
  {
    pengu_toml_buf_putc(b, (char)(0xc0 | (cp >> 6)));
    pengu_toml_buf_putc(b, (char)(0x80 | (cp & 0x3f)));
  }
  else if (cp <= 0xffff)
  {
    pengu_toml_buf_putc(b, (char)(0xe0 | (cp >> 12)));
    pengu_toml_buf_putc(b, (char)(0x80 | ((cp >> 6) & 0x3f)));
    pengu_toml_buf_putc(b, (char)(0x80 | (cp & 0x3f)));
  }
  else
  {
    pengu_toml_buf_putc(b, (char)(0xf0 | (cp >> 18)));
    pengu_toml_buf_putc(b, (char)(0x80 | ((cp >> 12) & 0x3f)));
    pengu_toml_buf_putc(b, (char)(0x80 | ((cp >> 6) & 0x3f)));
    pengu_toml_buf_putc(b, (char)(0x80 | (cp & 0x3f)));
  }
}

static char *pengu_toml_buf_steal(PenguTomlBuf *b)
{
  if (!pengu_toml_buf_reserve(b, 0))
  {
    pengu_toml_buf_free(b);
    return NULL;
  }
  b->data[b->len] = '\0';
  char *out = b->data;
  b->data = NULL;
  b->len = 0;
  b->cap = 0;
  return out;
}

static void pengu_toml_error(PenguTomlParser *p, const char *fmt, ...)
{
  if (p->failed)
    return;
  p->failed = 1;
  va_list ap;
  va_start(ap, fmt);
  vsnprintf(p->doc->error, sizeof(p->doc->error), fmt, ap);
  va_end(ap);
}

static int pengu_toml_peek(PenguTomlParser *p)
{
  return (p->pos < p->len) ? (unsigned char)p->src[p->pos] : -1;
}

static void pengu_toml_advance(PenguTomlParser *p)
{
  if (p->pos >= p->len)
    return;
  if (p->src[p->pos] == '\n')
  {
    p->line++;
    p->col = 1;
  }
  else
  {
    p->col++;
  }
  p->pos++;
}

static void pengu_toml_skip_inline(PenguTomlParser *p)
{
  while (p->pos < p->len)
  {
    char c = p->src[p->pos];
    if (c == ' ' || c == '\t' || c == '\r')
    {
      pengu_toml_advance(p);
      continue;
    }
    break;
  }
}

static void pengu_toml_skip_comment(PenguTomlParser *p)
{
  if (pengu_toml_peek(p) == '#')
  {
    while (p->pos < p->len && p->src[p->pos] != '\n')
      pengu_toml_advance(p);
  }
}

static void pengu_toml_skip_ws(PenguTomlParser *p)
{
  for (;;)
  {
    pengu_toml_skip_inline(p);
    if (pengu_toml_peek(p) == '#')
    {
      pengu_toml_skip_comment(p);
      continue;
    }
    if (pengu_toml_peek(p) == '\n')
    {
      pengu_toml_advance(p);
      continue;
    }
    break;
  }
}

static void pengu_toml_skip_to_newline(PenguTomlParser *p)
{
  pengu_toml_skip_inline(p);
  pengu_toml_skip_comment(p);
  if (pengu_toml_peek(p) == '\r')
    pengu_toml_advance(p);
  if (pengu_toml_peek(p) == '\n')
    pengu_toml_advance(p);
}

static char *pengu_toml_strdup(const char *s)
{
  if (!s)
    s = "";
  size_t n = strlen(s);
  char *out = (char *)malloc(n + 1);
  if (!out)
    return NULL;
  memcpy(out, s, n + 1);
  return out;
}

static void pengu_toml_add(PenguTomlParser *p, const char *key, const char *value, int kind)
{
  PenguTomlDoc *doc = p->doc;
  if (doc->count >= doc->cap)
  {
    int cap = doc->cap ? doc->cap * 2 : 32;
    PenguTomlEntry *ne = (PenguTomlEntry *)realloc(doc->entries, (size_t)cap * sizeof(PenguTomlEntry));
    if (!ne)
    {
      pengu_toml_error(p, "out of memory while parsing TOML");
      return;
    }
    doc->entries = ne;
    doc->cap = cap;
  }
  doc->entries[doc->count].key = key ? pengu_toml_strdup(key) : pengu_toml_strdup("");
  doc->entries[doc->count].value = value ? pengu_toml_strdup(value) : pengu_toml_strdup("");
  doc->entries[doc->count].kind = kind;
  doc->entries[doc->count].line = p->line;
  if (!doc->entries[doc->count].key || !doc->entries[doc->count].value)
  {
    pengu_toml_error(p, "out of memory while parsing TOML");
    return;
  }
  doc->count++;
}

static char *pengu_toml_join(const char *prefix, const char *key)
{
  if (!prefix || !prefix[0])
    return pengu_toml_strdup(key ? key : "");
  size_t a = strlen(prefix);
  size_t b = key ? strlen(key) : 0;
  char *out = (char *)malloc(a + b + 2);
  if (!out)
    return NULL;
  memcpy(out, prefix, a);
  out[a] = '.';
  if (b)
    memcpy(out + a + 1, key, b);
  out[a + 1 + b] = '\0';
  return out;
}

static void pengu_toml_set_prefix(PenguTomlParser *p, const char *prefix)
{
  char *copy = pengu_toml_strdup(prefix ? prefix : "");
  if (!copy)
  {
    pengu_toml_error(p, "out of memory while parsing TOML");
    return;
  }
  free(p->prefix);
  p->prefix = copy;
}

static int pengu_toml_counter_next(PenguTomlParser *p, const char *path)
{
  PenguTomlCounter *c = p->counters;
  while (c)
  {
    if (strcmp(c->path, path) == 0)
      return c->count++;
    c = c->next;
  }
  c = (PenguTomlCounter *)calloc(1, sizeof(PenguTomlCounter));
  if (!c)
    return 0;
  c->path = pengu_toml_strdup(path);
  if (!c->path)
  {
    free(c);
    return 0;
  }
  c->count = 1;
  c->next = p->counters;
  p->counters = c;
  return 0;
}

static int pengu_toml_hexval(int c)
{
  if (c >= '0' && c <= '9')
    return c - '0';
  if (c >= 'a' && c <= 'f')
    return c - 'a' + 10;
  if (c >= 'A' && c <= 'F')
    return c - 'A' + 10;
  return -1;
}

static void pengu_toml_parse_escape(PenguTomlParser *p, PenguTomlBuf *out)
{
  pengu_toml_advance(p); /* backslash */
  int c = pengu_toml_peek(p);
  if (c < 0)
  {
    pengu_toml_error(p, "unterminated escape sequence at line %d", p->line);
    return;
  }
  pengu_toml_advance(p);
  switch (c)
  {
  case 'b': pengu_toml_buf_putc(out, '\b'); return;
  case 't': pengu_toml_buf_putc(out, '\t'); return;
  case 'n': pengu_toml_buf_putc(out, '\n'); return;
  case 'f': pengu_toml_buf_putc(out, '\f'); return;
  case 'r': pengu_toml_buf_putc(out, '\r'); return;
  case '"': pengu_toml_buf_putc(out, '"'); return;
  case '\\': pengu_toml_buf_putc(out, '\\'); return;
  case '/': pengu_toml_buf_putc(out, '/'); return;
  case 'u':
  case 'U':
  {
    int digits = (c == 'u') ? 4 : 8;
    uint32_t cp = 0;
    for (int i = 0; i < digits; i++)
    {
      int h = pengu_toml_hexval(pengu_toml_peek(p));
      if (h < 0)
      {
        pengu_toml_error(p, "invalid \\%c escape at line %d", (char)c, p->line);
        return;
      }
      cp = (cp << 4) | (uint32_t)h;
      pengu_toml_advance(p);
    }
    pengu_toml_buf_put_utf8(out, cp);
    return;
  }
  default:
    pengu_toml_error(p, "unknown escape \\%c at line %d", (char)c, p->line);
    return;
  }
}

/* Parses a TOML string.  The opening quote is at the current position. */
static int pengu_toml_parse_string(PenguTomlParser *p, PenguTomlBuf *out)
{
  int q = pengu_toml_peek(p);
  if (q != '"' && q != '\'')
  {
    pengu_toml_error(p, "expected a string at line %d", p->line);
    return 0;
  }
  int literal = (q == '\'');
  int triple = 0;
  if (p->pos + 2 < p->len && p->src[p->pos + 1] == (char)q && p->src[p->pos + 2] == (char)q)
    triple = 1;
  pengu_toml_advance(p);
  if (triple)
  {
    pengu_toml_advance(p);
    pengu_toml_advance(p);
    /* A newline immediately after the opening delimiter is trimmed. */
    if (pengu_toml_peek(p) == '\r')
      pengu_toml_advance(p);
    if (pengu_toml_peek(p) == '\n')
      pengu_toml_advance(p);
  }
  for (;;)
  {
    if (p->pos >= p->len)
    {
      pengu_toml_error(p, "unterminated string at line %d", p->line);
      return 0;
    }
    if (triple)
    {
      if (p->pos + 2 < p->len && p->src[p->pos] == (char)q &&
          p->src[p->pos + 1] == (char)q && p->src[p->pos + 2] == (char)q)
      {
        pengu_toml_advance(p);
        pengu_toml_advance(p);
        pengu_toml_advance(p);
        return 1;
      }
    }
    else if (pengu_toml_peek(p) == q)
    {
      pengu_toml_advance(p);
      return 1;
    }
    if (!literal && pengu_toml_peek(p) == '\\')
    {
      if (triple && p->pos + 1 < p->len && (p->src[p->pos + 1] == '\n' || p->src[p->pos + 1] == '\r'))
      {
        /* Line-ending backslash: trim the newline and leading whitespace. */
        pengu_toml_advance(p);
        if (pengu_toml_peek(p) == '\r')
          pengu_toml_advance(p);
        if (pengu_toml_peek(p) == '\n')
          pengu_toml_advance(p);
        while (pengu_toml_peek(p) == ' ' || pengu_toml_peek(p) == '\t')
          pengu_toml_advance(p);
        continue;
      }
      pengu_toml_parse_escape(p, out);
      if (p->failed)
        return 0;
      continue;
    }
    pengu_toml_buf_putc(out, (char)pengu_toml_peek(p));
    pengu_toml_advance(p);
  }
}

/* Parses one bare or quoted key segment. */
static int pengu_toml_parse_key_segment(PenguTomlParser *p, PenguTomlBuf *out)
{
  pengu_toml_skip_inline(p);
  int c = pengu_toml_peek(p);
  if (c == '"' || c == '\'')
    return pengu_toml_parse_string(p, out);
  int any = 0;
  while (p->pos < p->len)
  {
    c = pengu_toml_peek(p);
    if (isalnum(c) || c == '_' || c == '-')
    {
      pengu_toml_buf_putc(out, (char)c);
      pengu_toml_advance(p);
      any = 1;
      continue;
    }
    break;
  }
  if (!any)
  {
    pengu_toml_error(p, "expected a key at line %d", p->line);
    return 0;
  }
  return 1;
}

/* Parses a dotted key path into `out` (no leading/trailing dot). */
static int pengu_toml_parse_key_path(PenguTomlParser *p, PenguTomlBuf *out)
{
  for (;;)
  {
    if (!pengu_toml_parse_key_segment(p, out))
      return 0;
    pengu_toml_skip_inline(p);
    if (pengu_toml_peek(p) != '.')
      return 1;
    pengu_toml_advance(p);
    pengu_toml_buf_putc(out, '.');
  }
}

static int pengu_toml_token_is_int(const char *s)
{
  if (!s || !*s)
    return 0;
  const char *q = s;
  if (*q == '+' || *q == '-')
    q++;
  if (q[0] == '0' && (q[1] == 'x' || q[1] == 'X'))
  {
    q += 2;
    if (!*q)
      return 0;
    while (*q)
    {
      if (!isxdigit((unsigned char)*q) && *q != '_')
        return 0;
      q++;
    }
    return 1;
  }
  if (q[0] == '0' && (q[1] == 'o' || q[1] == 'O'))
  {
    q += 2;
    if (!*q)
      return 0;
    while (*q)
    {
      if ((*q < '0' || *q > '7') && *q != '_')
        return 0;
      q++;
    }
    return 1;
  }
  if (q[0] == '0' && (q[1] == 'b' || q[1] == 'B'))
  {
    q += 2;
    if (!*q)
      return 0;
    while (*q)
    {
      if ((*q != '0' && *q != '1') && *q != '_')
        return 0;
      q++;
    }
    return 1;
  }
  if (!isdigit((unsigned char)*q))
    return 0;
  while (*q)
  {
    if (!isdigit((unsigned char)*q) && *q != '_')
      return 0;
    q++;
  }
  return 1;
}

static int pengu_toml_token_is_float(const char *s)
{
  if (!s || !*s)
    return 0;
  char *end = NULL;
  errno = 0;
  (void)strtod(s, &end);
  return end && *end == '\0' && end != s;
}

static void pengu_toml_strip_underscores(const char *src, char *dst, size_t cap)
{
  size_t j = 0;
  for (size_t i = 0; src[i] && j + 1 < cap; i++)
    if (src[i] != '_')
      dst[j++] = src[i];
  dst[j] = '\0';
}

static int pengu_toml_parse_value(PenguTomlParser *p, const char *key, int depth);

static int pengu_toml_parse_array(PenguTomlParser *p, const char *key, int depth)
{
  pengu_toml_add(p, key, "", PENGU_TOML_ARRAY);
  pengu_toml_advance(p); /* [ */
  int index = 0;
  for (;;)
  {
    pengu_toml_skip_ws(p);
    if (pengu_toml_peek(p) == ']')
    {
      pengu_toml_advance(p);
      return 1;
    }
    char subkey[512];
    snprintf(subkey, sizeof(subkey), "%s[%d]", key, index);
    if (!pengu_toml_parse_value(p, subkey, depth + 1))
      return 0;
    index++;
    pengu_toml_skip_ws(p);
    if (pengu_toml_peek(p) == ',')
    {
      pengu_toml_advance(p);
      continue;
    }
    if (pengu_toml_peek(p) == ']')
    {
      pengu_toml_advance(p);
      return 1;
    }
    pengu_toml_error(p, "expected ',' or ']' in array at line %d", p->line);
    return 0;
  }
}

static int pengu_toml_parse_inline_table(PenguTomlParser *p, const char *key, int depth)
{
  pengu_toml_add(p, key, "", PENGU_TOML_TABLE);
  pengu_toml_advance(p); /* { */
  for (;;)
  {
    pengu_toml_skip_ws(p);
    if (pengu_toml_peek(p) == '}')
    {
      pengu_toml_advance(p);
      return 1;
    }
    PenguTomlBuf k;
    pengu_toml_buf_init(&k);
    if (!pengu_toml_parse_key_path(p, &k))
    {
      pengu_toml_buf_free(&k);
      return 0;
    }
    pengu_toml_skip_inline(p);
    if (pengu_toml_peek(p) != '=')
    {
      pengu_toml_error(p, "expected '=' in inline table at line %d", p->line);
      pengu_toml_buf_free(&k);
      return 0;
    }
    pengu_toml_advance(p);
    pengu_toml_skip_inline(p);
    char *kstr = pengu_toml_buf_steal(&k);
    if (!kstr)
      return 0;
    char *full = pengu_toml_join(key, kstr);
    free(kstr);
    if (!full)
    {
      pengu_toml_error(p, "out of memory while parsing TOML");
      return 0;
    }
    int ok = pengu_toml_parse_value(p, full, depth + 1);
    free(full);
    if (!ok)
      return 0;
    pengu_toml_skip_ws(p);
    if (pengu_toml_peek(p) == ',')
    {
      pengu_toml_advance(p);
      continue;
    }
    if (pengu_toml_peek(p) == '}')
    {
      pengu_toml_advance(p);
      return 1;
    }
    pengu_toml_error(p, "expected ',' or '}' in inline table at line %d", p->line);
    return 0;
  }
}

static int pengu_toml_parse_value(PenguTomlParser *p, const char *key, int depth)
{
  if (depth > 64)
  {
    pengu_toml_error(p, "TOML nesting is too deep at line %d", p->line);
    return 0;
  }
  pengu_toml_skip_inline(p);
  int c = pengu_toml_peek(p);
  if (c == '"' || c == '\'')
  {
    PenguTomlBuf v;
    pengu_toml_buf_init(&v);
    if (!pengu_toml_parse_string(p, &v))
    {
      pengu_toml_buf_free(&v);
      return 0;
    }
    char *s = pengu_toml_buf_steal(&v);
    if (!s)
    {
      pengu_toml_error(p, "out of memory while parsing TOML");
      return 0;
    }
    pengu_toml_add(p, key, s, PENGU_TOML_STRING);
    free(s);
    return 1;
  }
  if (c == '[')
    return pengu_toml_parse_array(p, key, depth);
  if (c == '{')
    return pengu_toml_parse_inline_table(p, key, depth);
  if (c == 't' || c == 'f')
  {
    char tok[16];
    size_t n = 0;
    while (p->pos < p->len && (isalpha(pengu_toml_peek(p))) && n + 1 < sizeof(tok))
    {
      tok[n++] = (char)pengu_toml_peek(p);
      pengu_toml_advance(p);
    }
    tok[n] = '\0';
    if (strcmp(tok, "true") == 0 || strcmp(tok, "false") == 0)
    {
      pengu_toml_add(p, key, tok, PENGU_TOML_BOOL);
      return 1;
    }
    pengu_toml_error(p, "invalid boolean '%s' at line %d", tok, p->line);
    return 0;
  }
  /* Numbers and date/time literals: read until a structural delimiter. */
  char tok[512];
  size_t n = 0;
  while (p->pos < p->len)
  {
    c = pengu_toml_peek(p);
    if (c == ',' || c == ']' || c == '}' || c == '#' || c == '\n' || c == '\r')
      break;
    if ((c == ' ' || c == '\t') && n > 0)
    {
      /* Trailing spaces are not part of the token; a date/time may contain
       * one space between date and time, so keep internal spaces. */
      size_t save = p->pos;
      int save_line = p->line, save_col = p->col;
      pengu_toml_skip_inline(p);
      int nxt = pengu_toml_peek(p);
      if (nxt == ',' || nxt == ']' || nxt == '}' || nxt == '#' || nxt == '\n' || nxt == '\r' || nxt < 0)
        break;
      p->pos = save;
      p->line = save_line;
      p->col = save_col;
    }
    if (n + 1 < sizeof(tok))
      tok[n++] = (char)c;
    pengu_toml_advance(p);
  }
  tok[n] = '\0';
  while (n > 0 && (tok[n - 1] == ' ' || tok[n - 1] == '\t'))
    tok[--n] = '\0';
  if (n == 0)
  {
    pengu_toml_error(p, "missing value at line %d", p->line);
    return 0;
  }
  char clean[512];
  pengu_toml_strip_underscores(tok, clean, sizeof(clean));
  if (pengu_toml_token_is_int(tok))
  {
    if (clean[0] == '0' && (clean[1] == 'x' || clean[1] == 'X'))
    {
      long long v = strtoll(clean, NULL, 16);
      char dec[64];
      snprintf(dec, sizeof(dec), "%lld", v);
      pengu_toml_add(p, key, dec, PENGU_TOML_INT);
      return 1;
    }
    if (clean[0] == '0' && (clean[1] == 'o' || clean[1] == 'O'))
    {
      long long v = strtoll(clean + 2, NULL, 8);
      char dec[64];
      snprintf(dec, sizeof(dec), "%lld", v);
      pengu_toml_add(p, key, dec, PENGU_TOML_INT);
      return 1;
    }
    if (clean[0] == '0' && (clean[1] == 'b' || clean[1] == 'B'))
    {
      long long v = strtoll(clean + 2, NULL, 2);
      char dec[64];
      snprintf(dec, sizeof(dec), "%lld", v);
      pengu_toml_add(p, key, dec, PENGU_TOML_INT);
      return 1;
    }
    pengu_toml_add(p, key, clean, PENGU_TOML_INT);
    return 1;
  }
  if (pengu_toml_token_is_float(tok))
  {
    pengu_toml_add(p, key, clean, PENGU_TOML_FLOAT);
    return 1;
  }
  /* Dates and times are preserved verbatim as strings. */
  pengu_toml_add(p, key, tok, PENGU_TOML_STRING);
  return 1;
}

static int pengu_toml_parse_table_header(PenguTomlParser *p)
{
  int array_table = 0;
  pengu_toml_advance(p); /* [ */
  if (pengu_toml_peek(p) == '[')
  {
    array_table = 1;
    pengu_toml_advance(p);
  }
  pengu_toml_skip_inline(p);
  PenguTomlBuf path;
  pengu_toml_buf_init(&path);
  if (!pengu_toml_parse_key_path(p, &path))
  {
    pengu_toml_buf_free(&path);
    return 0;
  }
  pengu_toml_skip_inline(p);
  if (pengu_toml_peek(p) != ']')
  {
    pengu_toml_error(p, "expected ']' after table name at line %d", p->line);
    pengu_toml_buf_free(&path);
    return 0;
  }
  pengu_toml_advance(p);
  if (array_table)
  {
    if (pengu_toml_peek(p) != ']')
    {
      pengu_toml_error(p, "expected ']]' after array-of-tables name at line %d", p->line);
      pengu_toml_buf_free(&path);
      return 0;
    }
    pengu_toml_advance(p);
  }
  char *pathstr = pengu_toml_buf_steal(&path);
  if (!pathstr)
    return 0;
  if (array_table)
  {
    int idx = pengu_toml_counter_next(p, pathstr);
    char full[512];
    snprintf(full, sizeof(full), "%s[%d]", pathstr, idx);
    pengu_toml_set_prefix(p, full);
    if (idx == 0)
      pengu_toml_add(p, pathstr, "", PENGU_TOML_ARRAY_TABLE);
    pengu_toml_add(p, full, "", PENGU_TOML_TABLE);
  }
  else
  {
    pengu_toml_set_prefix(p, pathstr);
    pengu_toml_add(p, pathstr, "", PENGU_TOML_TABLE);
  }
  free(pathstr);
  pengu_toml_skip_to_newline(p);
  return !p->failed;
}

static int pengu_toml_parse_document(PenguTomlParser *p)
{
  pengu_toml_set_prefix(p, "");
  for (;;)
  {
    pengu_toml_skip_ws(p);
    if (p->pos >= p->len)
      return !p->failed;
    if (pengu_toml_peek(p) == '[')
    {
      if (!pengu_toml_parse_table_header(p))
        return 0;
      continue;
    }
    PenguTomlBuf keybuf;
    pengu_toml_buf_init(&keybuf);
    if (!pengu_toml_parse_key_path(p, &keybuf))
    {
      pengu_toml_buf_free(&keybuf);
      return 0;
    }
    pengu_toml_skip_inline(p);
    if (pengu_toml_peek(p) != '=')
    {
      pengu_toml_error(p, "expected '=' after key at line %d", p->line);
      pengu_toml_buf_free(&keybuf);
      return 0;
    }
    pengu_toml_advance(p);
    char *key = pengu_toml_buf_steal(&keybuf);
    if (!key)
      return 0;
    char *full = pengu_toml_join(p->prefix, key);
    free(key);
    if (!full)
    {
      pengu_toml_error(p, "out of memory while parsing TOML");
      return 0;
    }
    int ok = pengu_toml_parse_value(p, full, 0);
    free(full);
    if (!ok)
      return 0;
    pengu_toml_skip_inline(p);
    pengu_toml_skip_comment(p);
    if (pengu_toml_peek(p) == '\r')
      pengu_toml_advance(p);
    if (pengu_toml_peek(p) == '\n')
      pengu_toml_advance(p);
    else if (p->pos < p->len)
    {
      pengu_toml_error(p, "unexpected character after value at line %d", p->line);
      return 0;
    }
  }
}

static PenguTomlDoc *pengu_toml_parse(const char *src, int len)
{
  PenguTomlDoc *doc = (PenguTomlDoc *)calloc(1, sizeof(PenguTomlDoc));
  if (!doc)
    return NULL;
  PenguTomlParser p;
  memset(&p, 0, sizeof(p));
  p.src = src ? src : "";
  p.len = (len > 0) ? (size_t)len : 0;
  p.line = 1;
  p.col = 1;
  p.doc = doc;
  p.prefix = pengu_toml_strdup("");
  if (!p.prefix)
  {
    snprintf(doc->error, sizeof(doc->error), "out of memory while parsing TOML");
    return doc;
  }
  pengu_toml_parse_document(&p);
  free(p.prefix);
  PenguTomlCounter *c = p.counters;
  while (c)
  {
    PenguTomlCounter *next = c->next;
    free(c->path);
    free(c);
    c = next;
  }
  return doc;
}

static void pengu_toml_free(PenguTomlDoc *doc)
{
  if (!doc)
    return;
  for (int i = 0; i < doc->count; i++)
  {
    free(doc->entries[i].key);
    free(doc->entries[i].value);
  }
  free(doc->entries);
  free(doc);
}

static int pengu_toml_count(PenguTomlDoc *doc)
{
  return doc ? doc->count : 0;
}

static const char *pengu_toml_key(PenguTomlDoc *doc, int i)
{
  if (!doc || i < 0 || i >= doc->count)
    return "";
  return doc->entries[i].key;
}

static const char *pengu_toml_value(PenguTomlDoc *doc, int i)
{
  if (!doc || i < 0 || i >= doc->count)
    return "";
  return doc->entries[i].value;
}

static int pengu_toml_kind(PenguTomlDoc *doc, int i)
{
  if (!doc || i < 0 || i >= doc->count)
    return 0;
  return doc->entries[i].kind;
}

static const char *pengu_toml_error_text(PenguTomlDoc *doc)
{
  if (!doc)
    return "out of memory while parsing TOML";
  return doc->error;
}

#endif /* PENGU_TOML_MIN_H */
