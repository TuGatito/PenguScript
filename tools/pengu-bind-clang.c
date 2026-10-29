/*
 * pengu-bind-clang — build-time C header to .d.pengu generator.
 *
 * This is the libclang-based replacement path for the historical Python
 * pengu-bind helper.  It is a build tool only: the compiler/runtime never link
 * libclang.  It handles the declarations the stdlib needs (functions, structs,
 * unions, enums, typedefs and object-like numeric/string macros); complex C++
 * templates and variadic function-pointer typedefs are intentionally out of
 * scope and are reported as warnings.
 */
#include <clang-c/Index.h>
#include <ctype.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static FILE *g_out;
static int g_no_comments;
static int g_system_includes;
static int g_warnings;
static int g_field_count;

static void warn(const char *fmt, ...) {
  va_list ap;
  va_start(ap, fmt);
  fprintf(stderr, "pengu-bind-clang: warning: ");
  vfprintf(stderr, fmt, ap);
  fputc('\n', stderr);
  va_end(ap);
  g_warnings++;
}

static void out(const char *fmt, ...) {
  va_list ap;
  va_start(ap, fmt);
  vfprintf(g_out, fmt, ap);
  va_end(ap);
  fputc('\n', g_out);
}

static char *xstr(const char *s) {
  size_t n = strlen(s) + 1;
  char *p = (char *)malloc(n);
  if (!p) abort();
  memcpy(p, s, n);
  return p;
}

static void trim(char *s) {
  char *p = s;
  while (*p && isspace((unsigned char)*p)) p++;
  if (p != s) memmove(s, p, strlen(p) + 1);
  size_t n = strlen(s);
  while (n && isspace((unsigned char)s[n - 1])) s[--n] = '\0';
}

static int starts(const char *s, const char *pre) {
  return strncmp(s, pre, strlen(pre)) == 0;
}

static void replace_all(char *s, const char *from, const char *to) {
  size_t fl = strlen(from), tl = strlen(to);
  char *p = s;
  while ((p = strstr(p, from)) != NULL) {
    size_t rest = strlen(p + fl);
    if (tl > fl) memmove(p + tl, p + fl, rest + 1);
    else if (tl < fl) memmove(p + tl, p + fl, rest + 1);
    memcpy(p, to, tl);
    p += tl;
  }
}

static const char *primitive(const char *spelling) {
  static char buf[256];
  snprintf(buf, sizeof buf, "%s", spelling);
  trim(buf);
  replace_all(buf, "const ", "");
  replace_all(buf, "volatile ", "");
  replace_all(buf, "struct ", "");
  replace_all(buf, "enum ", "");
  replace_all(buf, "union ", "");
  replace_all(buf, "signed ", "");
  if (!strcmp(buf, "int") || !strcmp(buf, "signed int")) return "int";
  if (!strcmp(buf, "unsigned int") || !strcmp(buf, "unsigned")) return "u32";
  if (!strcmp(buf, "long") || !strcmp(buf, "long int") || !strcmp(buf, "signed long")) return "i64";
  if (!strcmp(buf, "unsigned long")) return "u64";
  if (!strcmp(buf, "long long") || !strcmp(buf, "long long int")) return "i64";
  if (!strcmp(buf, "unsigned long long")) return "u64";
  if (!strcmp(buf, "short") || !strcmp(buf, "short int")) return "i16";
  if (!strcmp(buf, "unsigned short")) return "u16";
  if (!strcmp(buf, "char") || !strcmp(buf, "signed char")) return "char";
  if (!strcmp(buf, "unsigned char")) return "byte";
  if (!strcmp(buf, "float")) return "f32";
  if (!strcmp(buf, "double") || !strcmp(buf, "long double")) return "f64";
  if (!strcmp(buf, "bool") || !strcmp(buf, "_Bool")) return "bool";
  if (!strcmp(buf, "void")) return "void";
  if (!strcmp(buf, "size_t")) return "size_t";
  if (!strcmp(buf, "ssize_t") || !strcmp(buf, "ptrdiff_t")) return "isize";
  if (!strcmp(buf, "int8_t")) return "i8";
  if (!strcmp(buf, "uint8_t")) return "byte";
  if (!strcmp(buf, "int16_t")) return "i16";
  if (!strcmp(buf, "uint16_t")) return "u16";
  if (!strcmp(buf, "int32_t")) return "int";
  if (!strcmp(buf, "uint32_t")) return "u32";
  if (!strcmp(buf, "int64_t")) return "i64";
  if (!strcmp(buf, "uint64_t")) return "u64";
  if (!strcmp(buf, "intptr_t")) return "isize";
  if (!strcmp(buf, "uintptr_t")) return "usize";
  if (!strcmp(buf, "va_list") || !strcmp(buf, "__builtin_va_list")) return "va_list";
  return NULL;
}

static const char *clean_tag(const char *s, char *tmp, size_t n) {
  snprintf(tmp, n, "%s", s ? s : "");
  trim(tmp);
  replace_all(tmp, "const ", "");
  replace_all(tmp, "volatile ", "");
  replace_all(tmp, "struct ", "");
  replace_all(tmp, "enum ", "");
  replace_all(tmp, "union ", "");
  if (!tmp[0]) snprintf(tmp, n, "opaque");
  return tmp;
}

static void type_text(CXType ty, char *buf, size_t n, int param) {
  CXType canonical = clang_getCanonicalType(ty);
  enum CXTypeKind k = canonical.kind;
  CXString s = clang_getTypeSpelling(ty);
  if (ty.kind == CXType_Typedef) {
    const char *tn = clang_getCString(s);
    if (tn && *tn) {
      snprintf(buf, n, "%s", tn);
      clang_disposeString(s);
      return;
    }
  }
  const char *sp = clang_getCString(s);
  const char *p = primitive(sp);
  if (k == CXType_Pointer) {
    CXType pointee = clang_getPointeeType(ty);
    CXString ps = clang_getTypeSpelling(pointee);
    const char *psp = clang_getCString(ps);
    const char *pp = primitive(psp);
    int frozen = strstr(sp, "const ") != NULL;
    char ptmp[256];
    if (!pp) pp = clean_tag(psp, ptmp, sizeof ptmp);
    if (!strcmp(pp, "void")) snprintf(buf, n, "ref to void");
    else snprintf(buf, n, "ref to %s%s", frozen ? "frozen " : "", pp);
    clang_disposeString(ps);
  } else if (k == CXType_ConstantArray || k == CXType_IncompleteArray) {
    CXType elem = clang_getArrayElementType(ty);
    char tmp[256];
    type_text(elem, tmp, sizeof tmp, param);
    char refbuf[256];
    snprintf(refbuf, sizeof refbuf, "ref to %s", tmp);
    snprintf(buf, n, "%s", refbuf);
  } else if (k == CXType_Typedef) {
    CXString tn = clang_getTypeSpelling(ty);
    const char *t = clang_getCString(tn);
    if (!strcmp(t, "size_t")) snprintf(buf, n, "size_t");
    else snprintf(buf, n, "%s", t);
    clang_disposeString(tn);
  } else if (p) {
    snprintf(buf, n, "%s", p);
  } else {
    /* Preserve user typedef/struct names; fall back to opaque. */
    if (sp && *sp) snprintf(buf, n, "%s", sp);
    else snprintf(buf, n, "opaque");
    replace_all(buf, "const ", "");
    replace_all(buf, "volatile ", "");
    replace_all(buf, "struct ", "");
    replace_all(buf, "enum ", "");
    replace_all(buf, "union ", "");
  }
  (void)param;
  clang_disposeString(s);
}

static int is_public(CXCursor c) {
  enum CXCursorKind k = clang_getCursorKind(c);
  if (k == CXCursor_MacroDefinition) {
    CXSourceLocation loc = clang_getCursorLocation(c);
    return clang_Location_isFromMainFile(loc) ? 1 : 0;
  }
  CXSourceLocation loc = clang_getCursorLocation(c);
  if (clang_Location_isFromMainFile(loc)) return 1;
  if (g_system_includes) return 1;
  CXFile file;
  clang_getFileLocation(loc, &file, NULL, NULL, NULL);
  if (!file) return 0;
  CXString fn = clang_getFileName(file);
  const char *name = clang_getCString(fn);
  int keep = name && strstr(name, "/std_c/") != NULL;
  clang_disposeString(fn);
  return keep;
}

static void emit_comment(CXCursor c) {
  if (g_no_comments) return;
  CXString raw = clang_Cursor_getRawCommentText(c);
  const char *s = clang_getCString(raw);
  if (s && *s) {
    char *tmp = xstr(s);
    char *line = strtok(tmp, "\n");
    while (line) {
      char *p = line;
      while (*p && isspace((unsigned char)*p)) p++;
      if (starts(p, "/*")) p += 2;
      while (*p == '*' || *p == '!' || *p == ' ' || *p == '\t') p++;
      char *e = p + strlen(p);
      while (e > p && isspace((unsigned char)e[-1])) *--e = '\0';
      if (*p) out("# %s", p);
      line = strtok(NULL, "\n");
    }
    free(tmp);
  }
  clang_disposeString(raw);
}

static enum CXChildVisitResult field_visitor(CXCursor child, CXCursor parent, CXClientData data) {
  (void)parent; (void)data;
  if (clang_getCursorKind(child) != CXCursor_FieldDecl) return CXChildVisit_Continue;
  g_field_count++;
  CXString fn = clang_getCursorSpelling(child);
  const char *f = clang_getCString(fn);
  char ty[256];
  type_text(clang_getCursorType(child), ty, sizeof ty, 0);
  out("    %s as %s", f, ty);
  clang_disposeString(fn);
  return CXChildVisit_Continue;
}

static enum CXChildVisitResult enum_visitor(CXCursor child, CXCursor parent, CXClientData data) {
  (void)parent; (void)data;
  if (clang_getCursorKind(child) != CXCursor_EnumConstantDecl) return CXChildVisit_Continue;
  CXString fn = clang_getCursorSpelling(child);
  out("    %s is %lld", clang_getCString(fn), (long long)clang_getEnumConstantDeclValue(child));
  clang_disposeString(fn);
  return CXChildVisit_Continue;
}

static void emit_struct(CXCursor c, int is_union) {
  CXString nm = clang_getCursorSpelling(c);
  const char *name = clang_getCString(nm);
  if (!name || !*name) { clang_disposeString(nm); return; }
  if (!is_public(c)) { clang_disposeString(nm); return; }
  g_field_count = 0;
  clang_visitChildren(c, field_visitor, NULL);
  if (g_field_count == 0) {
    out("alias %s as opaque", name);
  } else {
    emit_comment(c);
    out("%s %s:", is_union ? "echo" : "rune", name);
    /* Re-visit to print fields now that we know the struct is not empty. */
    g_field_count = 0;
    clang_visitChildren(c, field_visitor, NULL);
    out("");
  }
  clang_disposeString(nm);
}

static void emit_enum(CXCursor c) {
  CXString nm = clang_getCursorSpelling(c);
  const char *name = clang_getCString(nm);
  if (!name || !*name) { clang_disposeString(nm); return; }
  if (!is_public(c)) { clang_disposeString(nm); return; }
  emit_comment(c);
  out("omen %s:", name);
  clang_visitChildren(c, enum_visitor, NULL);
  out("");
  clang_disposeString(nm);
}

static void emit_typedef(CXCursor c) {
  CXString nm = clang_getCursorSpelling(c);
  const char *name = clang_getCString(nm);
  if (!name || !*name || !is_public(c)) { clang_disposeString(nm); return; }
  CXType ty = clang_getTypedefDeclUnderlyingType(c);
  CXType canon = clang_getCanonicalType(ty);
  char t[256];
  if (canon.kind == CXType_Record) {
    CXString ts = clang_getTypeSpelling(ty);
    const char *tsp = clang_getCString(ts);
    char tmp[256];
    clean_tag(tsp, tmp, sizeof tmp);
    if (!strcmp(tmp, "opaque") || strstr(tsp, "struct ") == tsp || strstr(tsp, "union ") == tsp) {
      snprintf(t, sizeof t, "opaque");
    } else {
      type_text(ty, t, sizeof t, 0);
    }
    clang_disposeString(ts);
  } else {
    type_text(ty, t, sizeof t, 0);
  }
  if (strstr(t, "(*)")) {
    warn("skipping function-pointer typedef '%s' (not yet supported)", name);
  } else {
    emit_comment(c);
    out("alias %s as %s", name, t);
  }
  clang_disposeString(nm);
}

static void emit_function(CXCursor c) {
  if (!is_public(c)) return;
  CXString nm = clang_getCursorSpelling(c);
  const char *name = clang_getCString(nm);
  if (!name || !*name) { clang_disposeString(nm); return; }
  emit_comment(c);
  char ret[256];
  type_text(clang_getCursorResultType(c), ret, sizeof ret, 0);
  fprintf(g_out, "declare %s with ", name);
  int argc = clang_Cursor_getNumArguments(c);
  if (argc != 0) {
    for (int i = 0; i < argc; i++) {
      CXCursor arg = clang_Cursor_getArgument(c, i);
      CXString an = clang_getCursorSpelling(arg);
      char at[256];
      type_text(clang_getCursorType(arg), at, sizeof at, 1);
      fprintf(g_out, "%s%s as %s", i ? ", " : "", clang_getCString(an), at);
      clang_disposeString(an);
    }
  }
  if (clang_isFunctionTypeVariadic(clang_getCursorType(c))) {
    fprintf(g_out, "%s...", argc ? ", " : "");
  }
  fprintf(g_out, " into %s", ret);
  out("");
  clang_disposeString(nm);
}

static void emit_macro(CXCursor c) {
  if (!is_public(c)) return;
  CXString nm = clang_getCursorSpelling(c);
  const char *name = clang_getCString(nm);
  if (!name || !*name) { clang_disposeString(nm); return; }
  CXSourceRange range = clang_getCursorExtent(c);
  CXToken *toks = NULL;
  unsigned nt = 0;
  clang_tokenize(clang_Cursor_getTranslationUnit(c), range, &toks, &nt);
  if (nt < 2) { clang_disposeTokens(clang_Cursor_getTranslationUnit(c), toks, nt); clang_disposeString(nm); return; }
  CXString first = clang_getTokenSpelling(clang_Cursor_getTranslationUnit(c), toks[0]);
  const char *f = clang_getCString(first);
  int is_num = (nt == 2);
  char val[512] = {0};
  if (is_num) {
    CXString v = clang_getTokenSpelling(clang_Cursor_getTranslationUnit(c), toks[1]);
    const char *vs = clang_getCString(v);
    if (vs) snprintf(val, sizeof val, "%s", vs);
    clang_disposeString(v);
    if (!(isdigit((unsigned char)val[0]) || val[0] == '-' || val[0] == '+' || val[0] == '"' || starts(val, "0x"))) is_num = 0;
  }
  if (is_num && strcmp(f, name) == 0) {
    out("const %s as i64 is %s", name, val);
  }
  clang_disposeString(first);
  clang_disposeTokens(clang_Cursor_getTranslationUnit(c), toks, nt);
  clang_disposeString(nm);
}

static enum CXChildVisitResult visitor(CXCursor c, CXCursor parent, CXClientData data) {
  (void)parent; (void)data;
  if (!is_public(c)) return CXChildVisit_Continue;
  switch (clang_getCursorKind(c)) {
    case CXCursor_StructDecl: emit_struct(c, 0); break;
    case CXCursor_UnionDecl: emit_struct(c, 1); break;
    case CXCursor_EnumDecl: emit_enum(c); break;
    case CXCursor_TypedefDecl: emit_typedef(c); break;
    case CXCursor_FunctionDecl: emit_function(c); break;
    case CXCursor_MacroDefinition: emit_macro(c); break;
    default: break;
  }
  return CXChildVisit_Continue;
}

static void usage(void) {
  fprintf(stderr,
    "Usage: pengu-bind-clang HEADER [--output PATH|-] [--prefix P]\n"
    "  [--links L...] [--include-paths D...] [--define NAME[=V]]\n"
    "  [--system-includes] [--no-comments] [--version]\n");
}

int main(int argc, char **argv) {
  const char *header = NULL, *output = NULL, *prefix = NULL;
  const char *links[64]; int nlinks = 0;
  const char *incs[64]; int nincs = 0;
  const char *defs[64]; int ndefs = 0;
  for (int i = 1; i < argc; i++) {
    const char *a = argv[i];
    if (!strcmp(a, "--help") || !strcmp(a, "-h")) { usage(); return 0; }
    if (!strcmp(a, "--version")) { puts("pengu-bind-clang 1.0.0 (libclang)"); return 0; }
    if (!strcmp(a, "--output") && i + 1 < argc) { output = argv[++i]; continue; }
    if (!strcmp(a, "--prefix") && i + 1 < argc) { prefix = argv[++i]; continue; }
    if (!strcmp(a, "--links")) { while (i + 1 < argc && argv[i+1][0] != '-') links[nlinks++] = argv[++i]; continue; }
    if (!strcmp(a, "--include-paths")) { while (i + 1 < argc && argv[i+1][0] != '-') incs[nincs++] = argv[++i]; continue; }
    if (!strcmp(a, "--define") && i + 1 < argc) { defs[ndefs++] = argv[++i]; continue; }
    if (!strncmp(a, "--define=", 9)) { defs[ndefs++] = a + 9; continue; }
    if (!strcmp(a, "--system-includes")) { g_system_includes = 1; continue; }
    if (!strcmp(a, "--no-comments")) { g_no_comments = 1; continue; }
    if (!strcmp(a, "--no-cpp") || !strcmp(a, "--no-blank-extensions") || !strcmp(a, "--auto-import") || starts(a, "--auto-import=")) continue;
    if (starts(a, "-")) { warn("unknown option '%s'", a); continue; }
    if (!header) header = a;
  }
  if (!header) { usage(); return 2; }
  g_out = (output && strcmp(output, "-")) ? fopen(output, "w") : stdout;
  if (!g_out) { perror(output); return 2; }

  const char *base = strrchr(header, '/');
  base = base ? base + 1 : header;
  out("## Generated by pengu-bind-clang (libclang). Do not edit.");
  out("include \"%s\"", base);
  for (int i = 0; i < nlinks; i++) out("link \"%s\"", links[i]);
  if (prefix && *prefix) out("insignia %s_", prefix);
  out("");

  CXIndex index = clang_createIndex(0, 0);
  const char *args[256]; int na = 0;
  args[na++] = "-x"; args[na++] = "c";
  args[na++] = "-std=c11";
  for (int i = 0; i < nincs; i++) { args[na++] = "-I"; args[na++] = incs[i]; }
  for (int i = 0; i < ndefs; i++) { args[na++] = "-D"; args[na++] = defs[i]; }
  CXTranslationUnit tu = clang_parseTranslationUnit(index, header, args, na, NULL, 0,
      CXTranslationUnit_DetailedPreprocessingRecord | CXTranslationUnit_SkipFunctionBodies);
  if (!tu) { fprintf(stderr, "pengu-bind-clang: failed to parse %s\n", header); return 1; }
  clang_visitChildren(clang_getTranslationUnitCursor(tu), visitor, NULL);
  clang_disposeTranslationUnit(tu);
  clang_disposeIndex(index);
  if (g_out != stdout) fclose(g_out);
  if (g_warnings) fprintf(stderr, "pengu-bind-clang: %d warning(s)\n", g_warnings);
  return 0;
}
