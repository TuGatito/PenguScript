/* PenguScript bridge for the vendored vaqt high-precision time library. */
#include "pengu_runtime.h"
#include "vaqt.h"

static PenguString pengu_vaqt_buf_string(char *buf, size_t n)
{
  if (!buf || n == 0)
    return pengu_string_from_cstr("");
  return pengu_string_owned(buf, (int)n);
}

void pengu_vaqt_now(int64_t *sec, int32_t *nsec)
{
  Time t = time_now();
  if (sec)
    *sec = t.sec;
  if (nsec)
    *nsec = t.nsec;
}

void pengu_vaqt_from_unix(int64_t sec, int32_t nsec, int64_t *out_sec, int32_t *out_nsec)
{
  Time t = time_unix(sec, nsec);
  if (out_sec)
    *out_sec = t.sec;
  if (out_nsec)
    *out_nsec = t.nsec;
}

void pengu_vaqt_to_unix(int64_t sec, int32_t nsec, int64_t *out_sec, int32_t *out_nsec)
{
  Time t = {sec, nsec};
  if (out_sec)
    *out_sec = time_to_unix(t);
  if (out_nsec)
    *out_nsec = time_get_nano(t);
}

int pengu_vaqt_year(int64_t sec, int32_t nsec) { Time t = {sec, nsec}; return time_get_year(t); }
int pengu_vaqt_month(int64_t sec, int32_t nsec) { Time t = {sec, nsec}; return (int)time_get_month(t); }
int pengu_vaqt_day(int64_t sec, int32_t nsec) { Time t = {sec, nsec}; return time_get_day(t); }
int pengu_vaqt_hour(int64_t sec, int32_t nsec) { Time t = {sec, nsec}; return time_get_hour(t); }
int pengu_vaqt_minute(int64_t sec, int32_t nsec) { Time t = {sec, nsec}; return time_get_minute(t); }
int pengu_vaqt_second(int64_t sec, int32_t nsec) { Time t = {sec, nsec}; return time_get_second(t); }
int pengu_vaqt_nano(int64_t sec, int32_t nsec) { Time t = {sec, nsec}; return time_get_nano(t); }
int pengu_vaqt_weekday(int64_t sec, int32_t nsec) { Time t = {sec, nsec}; return (int)time_get_weekday(t); }
int pengu_vaqt_yearday(int64_t sec, int32_t nsec) { Time t = {sec, nsec}; return time_get_yearday(t); }

int pengu_vaqt_compare(int64_t asec, int32_t ansec, int64_t bsec, int32_t bnsec)
{
  Time a = {asec, ansec};
  Time b = {bsec, bnsec};
  return time_compare(a, b);
}

void pengu_vaqt_add(int64_t sec, int32_t nsec, int64_t add_sec, int32_t add_nsec, int64_t *out_sec, int32_t *out_nsec)
{
  Time t = time_add((Time){sec, nsec}, (Duration)(add_sec * TIME_SECOND + add_nsec));
  if (out_sec)
    *out_sec = t.sec;
  if (out_nsec)
    *out_nsec = t.nsec;
}

void pengu_vaqt_add_date(int64_t sec, int32_t nsec, int years, int months, int days, int64_t *out_sec, int32_t *out_nsec)
{
  Time t = time_add_date((Time){sec, nsec}, years, months, days);
  if (out_sec)
    *out_sec = t.sec;
  if (out_nsec)
    *out_nsec = t.nsec;
}

PenguString pengu_vaqt_format_iso(int64_t sec, int32_t nsec, int offset)
{
  char buf[128];
  size_t n = time_fmt_iso((Time){sec, nsec}, offset, buf, sizeof(buf));
  return pengu_vaqt_buf_string(buf, n);
}

PenguString pengu_vaqt_format_date(int64_t sec, int32_t nsec, int offset)
{
  char buf[64];
  size_t n = time_fmt_date((Time){sec, nsec}, offset, buf, sizeof(buf));
  return pengu_vaqt_buf_string(buf, n);
}

PenguString pengu_vaqt_format_datetime(int64_t sec, int32_t nsec, int offset)
{
  char buf[64];
  size_t n = time_fmt_datetime((Time){sec, nsec}, offset, buf, sizeof(buf));
  return pengu_vaqt_buf_string(buf, n);
}

bool pengu_vaqt_parse_iso(PenguString s, int64_t *out_sec, int32_t *out_nsec)
{
  if (!s.data || s.len <= 0)
    return false;
  char *tmp = (char *)malloc((size_t)s.len + 1);
  if (!tmp)
    return false;
  memcpy(tmp, s.data, (size_t)s.len);
  tmp[s.len] = '\0';
  Time t = time_parse(tmp);
  free(tmp);
  if (time_is_zero(t))
    return false;
  if (out_sec)
    *out_sec = t.sec;
  if (out_nsec)
    *out_nsec = t.nsec;
  return true;
}
