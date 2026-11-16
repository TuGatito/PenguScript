//! Runtime de los intrínsecos de `std`, embebido en el código generado.
//!
//! Este archivo **no** se compila como módulo de `pengu-codegen`: se incluye
//! con `include_str!` y se emite dentro de `mod __pengu_std { ... }` en la
//! fuente generada (D4 de `scratch/STDLIB_PLAN.md`).
//!
//! Cada función corresponde a una firma declarada con `foreign "pengu"` en
//! `std/`. Los nombres y los tipos deben coincidir exactamente.

pub fn int_pow(base: i32, exp: u32) -> i32 {
    base.pow(exp)
}

pub fn int_from_str(s: &str) -> Option<i32> {
    s.trim().parse().ok()
}

pub fn int_from_str_radix(s: &str, radix: u32) -> Option<i32> {
    i32::from_str_radix(s.trim(), radix).ok()
}

pub fn int_to_string(value: i32) -> String {
    value.to_string()
}

pub fn int_to_float(value: i32) -> f64 {
    f64::from(value)
}

pub fn int_to_radix(value: i32, radix: u32) -> String {
    const DIGITS: &[u8; 36] = b"0123456789abcdefghijklmnopqrstuvwxyz";
    let radix = radix.clamp(2, 36);
    let mut magnitude = value.unsigned_abs();
    let mut buffer = Vec::new();
    loop {
        buffer.push(DIGITS[(magnitude % radix) as usize]);
        magnitude /= radix;
        if magnitude == 0 {
            break;
        }
    }
    if value < 0 {
        buffer.push(b'-');
    }
    buffer.reverse();
    String::from_utf8(buffer).unwrap_or_default()
}

pub fn int_digits(value: i32) -> Vec<u8> {
    value.unsigned_abs().to_string().into_bytes()
}

pub fn int_div_ceil(a: i32, b: i32) -> i32 {
    let quotient = a / b;
    let remainder = a % b;
    if remainder != 0 && ((remainder > 0) == (b > 0)) {
        quotient + 1
    } else {
        quotient
    }
}

pub fn int_div_euclid(a: i32, b: i32) -> i32 {
    a.div_euclid(b)
}

pub fn int_rem_euclid(a: i32, b: i32) -> i32 {
    a.rem_euclid(b)
}

pub fn int_abs_diff(a: i32, b: i32) -> u32 {
    a.abs_diff(b)
}

pub fn int_unsigned_abs(value: i32) -> u32 {
    value.unsigned_abs()
}

pub fn int_is_power_of_two(value: i32) -> bool {
    value > 0 && value.count_ones() == 1
}

pub fn int_count_ones(value: i32) -> u32 {
    value.count_ones()
}

pub fn int_count_zeros(value: i32) -> u32 {
    value.count_zeros()
}

pub fn int_leading_zeros(value: i32) -> u32 {
    value.leading_zeros()
}

pub fn int_trailing_zeros(value: i32) -> u32 {
    value.trailing_zeros()
}

pub fn int_rotate_left(value: i32, n: u32) -> i32 {
    value.rotate_left(n)
}

pub fn int_rotate_right(value: i32, n: u32) -> i32 {
    value.rotate_right(n)
}

pub fn int_swap_bytes(value: i32) -> i32 {
    value.swap_bytes()
}

pub fn int_reverse_bits(value: i32) -> i32 {
    value.reverse_bits()
}

pub fn int_ilog2(value: i32) -> u32 {
    value.ilog2()
}

pub fn int_ilog10(value: i32) -> u32 {
    value.ilog10()
}

pub fn int_next_power_of_two(value: i32) -> i32 {
    if value <= 1 {
        return 1;
    }
    let mut power = 1i32;
    while power < value {
        power = power.wrapping_mul(2);
        if power <= 0 {
            panic!("el siguiente múltiplo de dos no cabe en `Int`");
        }
    }
    power
}

pub fn int_checked_next_power_of_two(value: i32) -> Option<i32> {
    if value < 0 {
        return None;
    }
    if value <= 1 {
        return Some(1);
    }
    let mut power = 1i32;
    while power < value {
        power = power.checked_mul(2)?;
    }
    Some(power)
}

pub fn int_checked_add(a: i32, b: i32) -> Option<i32> {
    a.checked_add(b)
}

pub fn int_checked_sub(a: i32, b: i32) -> Option<i32> {
    a.checked_sub(b)
}

pub fn int_checked_mul(a: i32, b: i32) -> Option<i32> {
    a.checked_mul(b)
}

pub fn int_checked_div(a: i32, b: i32) -> Option<i32> {
    a.checked_div(b)
}

pub fn int_checked_rem(a: i32, b: i32) -> Option<i32> {
    a.checked_rem(b)
}

pub fn int_checked_neg(a: i32) -> Option<i32> {
    a.checked_neg()
}

pub fn int_checked_abs(a: i32) -> Option<i32> {
    a.checked_abs()
}

pub fn int_checked_pow(a: i32, exp: u32) -> Option<i32> {
    a.checked_pow(exp)
}

pub fn int_checked_div_euclid(a: i32, b: i32) -> Option<i32> {
    a.checked_div_euclid(b)
}

pub fn int_checked_rem_euclid(a: i32, b: i32) -> Option<i32> {
    a.checked_rem_euclid(b)
}

pub fn int_wrapping_add(a: i32, b: i32) -> i32 {
    a.wrapping_add(b)
}

pub fn int_wrapping_sub(a: i32, b: i32) -> i32 {
    a.wrapping_sub(b)
}

pub fn int_wrapping_mul(a: i32, b: i32) -> i32 {
    a.wrapping_mul(b)
}

pub fn int_wrapping_div(a: i32, b: i32) -> i32 {
    a.wrapping_div(b)
}

pub fn int_wrapping_rem(a: i32, b: i32) -> i32 {
    a.wrapping_rem(b)
}

pub fn int_wrapping_neg(a: i32) -> i32 {
    a.wrapping_neg()
}

pub fn int_wrapping_pow(a: i32, exp: u32) -> i32 {
    a.wrapping_pow(exp)
}

pub fn int_wrapping_div_euclid(a: i32, b: i32) -> i32 {
    a.wrapping_div_euclid(b)
}

pub fn int_wrapping_rem_euclid(a: i32, b: i32) -> i32 {
    a.wrapping_rem_euclid(b)
}

pub fn int_saturating_add(a: i32, b: i32) -> i32 {
    a.saturating_add(b)
}

pub fn int_saturating_sub(a: i32, b: i32) -> i32 {
    a.saturating_sub(b)
}

pub fn int_saturating_mul(a: i32, b: i32) -> i32 {
    a.saturating_mul(b)
}

pub fn int_saturating_div(a: i32, b: i32) -> i32 {
    a.saturating_div(b)
}

pub fn int_saturating_pow(a: i32, exp: u32) -> i32 {
    a.saturating_pow(exp)
}

pub fn int_overflowing_add(a: i32, b: i32) -> (i32, bool) {
    a.overflowing_add(b)
}

pub fn int_overflowing_sub(a: i32, b: i32) -> (i32, bool) {
    a.overflowing_sub(b)
}

pub fn int_overflowing_mul(a: i32, b: i32) -> (i32, bool) {
    a.overflowing_mul(b)
}

pub fn int_overflowing_neg(a: i32) -> (i32, bool) {
    a.overflowing_neg()
}

// ---------------------------------------------------------------------------
// `floatem`: intrínsecos de `Float` (f64).
// ---------------------------------------------------------------------------

pub fn f_abs(x: f64) -> f64 {
    x.abs()
}

pub fn f_sqrt(x: f64) -> f64 {
    x.sqrt()
}

pub fn f_pow(x: f64, exp: f64) -> f64 {
    x.powf(exp)
}

pub fn f_powi(x: f64, exp: i32) -> f64 {
    x.powi(exp)
}

pub fn f_sin(x: f64) -> f64 {
    x.sin()
}

pub fn f_cos(x: f64) -> f64 {
    x.cos()
}

pub fn f_tan(x: f64) -> f64 {
    x.tan()
}

pub fn f_asin(x: f64) -> f64 {
    x.asin()
}

pub fn f_acos(x: f64) -> f64 {
    x.acos()
}

pub fn f_atan(x: f64) -> f64 {
    x.atan()
}

pub fn f_atan2(y: f64, x: f64) -> f64 {
    y.atan2(x)
}

pub fn f_sinh(x: f64) -> f64 {
    x.sinh()
}

pub fn f_cosh(x: f64) -> f64 {
    x.cosh()
}

pub fn f_tanh(x: f64) -> f64 {
    x.tanh()
}

pub fn f_asinh(x: f64) -> f64 {
    x.asinh()
}

pub fn f_acosh(x: f64) -> f64 {
    x.acosh()
}

pub fn f_atanh(x: f64) -> f64 {
    x.atanh()
}

pub fn f_floor(x: f64) -> f64 {
    x.floor()
}

pub fn f_ceil(x: f64) -> f64 {
    x.ceil()
}

pub fn f_round(x: f64) -> f64 {
    x.round()
}

pub fn f_trunc(x: f64) -> f64 {
    x.trunc()
}

pub fn f_fract(x: f64) -> f64 {
    x.fract()
}

pub fn f_round_ties_even(x: f64) -> f64 {
    x.round_ties_even()
}

pub fn f_min(a: f64, b: f64) -> f64 {
    a.min(b)
}

pub fn f_max(a: f64, b: f64) -> f64 {
    a.max(b)
}

pub fn f_exp(x: f64) -> f64 {
    x.exp()
}

pub fn f_exp2(x: f64) -> f64 {
    x.exp2()
}

pub fn f_exp_m1(x: f64) -> f64 {
    x.exp_m1()
}

pub fn f_ln(x: f64) -> f64 {
    x.ln()
}

pub fn f_log2(x: f64) -> f64 {
    x.log2()
}

pub fn f_log10(x: f64) -> f64 {
    x.log10()
}

pub fn f_ln_1p(x: f64) -> f64 {
    x.ln_1p()
}

pub fn f_cbrt(x: f64) -> f64 {
    x.cbrt()
}

pub fn f_hypot(a: f64, b: f64) -> f64 {
    a.hypot(b)
}

pub fn f_recip(x: f64) -> f64 {
    x.recip()
}

pub fn f_signum(x: f64) -> f64 {
    x.signum()
}

pub fn f_copysign(x: f64, sign: f64) -> f64 {
    x.copysign(sign)
}

pub fn f_mul_add(a: f64, b: f64, c: f64) -> f64 {
    a.mul_add(b, c)
}

pub fn f_sin_cos(x: f64) -> (f64, f64) {
    x.sin_cos()
}

pub fn f_is_infinite(x: f64) -> bool {
    x.is_infinite()
}

pub fn f_is_finite(x: f64) -> bool {
    x.is_finite()
}

pub fn f_is_sign_positive(x: f64) -> bool {
    x.is_sign_positive()
}

pub fn f_is_sign_negative(x: f64) -> bool {
    x.is_sign_negative()
}

pub fn f_to_bits(x: f64) -> u64 {
    x.to_bits()
}

pub fn f_from_str(s: &str) -> Option<f64> {
    s.trim().parse().ok()
}

pub fn f_from_bits(bits: u64) -> f64 {
    f64::from_bits(bits)
}

pub fn f_next_up(x: f64) -> f64 {
    x.next_up()
}

pub fn f_next_down(x: f64) -> f64 {
    x.next_down()
}

pub fn f_total_cmp(a: f64, b: f64) -> ::std::cmp::Ordering {
    a.total_cmp(&b)
}

pub fn f_to_int(x: f64) -> i32 {
    x as i32
}

pub fn f_to_string(x: f64) -> String {
    x.to_string()
}

// ---------------------------------------------------------------------------
// `littera`: intrínsecos de `Char` (char).
// ---------------------------------------------------------------------------

pub fn c_is_ascii(c: char) -> bool {
    c.is_ascii()
}

pub fn c_is_alphabetic(c: char) -> bool {
    c.is_alphabetic()
}

pub fn c_is_numeric(c: char) -> bool {
    c.is_numeric()
}

pub fn c_is_alphanumeric(c: char) -> bool {
    c.is_alphanumeric()
}

pub fn c_is_whitespace(c: char) -> bool {
    c.is_whitespace()
}

pub fn c_is_uppercase(c: char) -> bool {
    c.is_uppercase()
}

pub fn c_is_lowercase(c: char) -> bool {
    c.is_lowercase()
}

pub fn c_to_uppercase(c: char) -> char {
    c.to_uppercase().next().unwrap_or(c)
}

pub fn c_to_lowercase(c: char) -> char {
    c.to_lowercase().next().unwrap_or(c)
}

pub fn c_to_digit(c: char, radix: u32) -> Option<u32> {
    c.to_digit(radix)
}

pub fn c_to_string(c: char) -> String {
    c.to_string()
}

pub fn c_len_utf8(c: char) -> usize {
    c.len_utf8()
}

pub fn c_len_utf16(c: char) -> usize {
    c.len_utf16()
}

pub fn c_escape_default(c: char) -> String {
    c.escape_default().to_string()
}

pub fn c_escape_unicode(c: char) -> String {
    c.escape_unicode().to_string()
}

pub fn c_is_control(c: char) -> bool {
    c.is_control()
}

pub fn c_is_punctuation(c: char) -> bool {
    is_unicode_category(c, &['P'])
}

pub fn c_is_symbol(c: char) -> bool {
    is_unicode_category(c, &['S'])
}

pub fn c_is_math(c: char) -> bool {
    matches!(c as u32, 0x2200..=0x22FF | 0x27C0..=0x27EF | 0x2980..=0x29FF | 0x2A00..=0x2AFF)
}

pub fn c_is_currency(c: char) -> bool {
    matches!(c as u32, 0x24 | 0xA2..=0xA5 | 0x20A0..=0x20CF)
}

pub fn c_is_ascii_digit(c: char) -> bool {
    c.is_ascii_digit()
}

pub fn c_is_ascii_alphabetic(c: char) -> bool {
    c.is_ascii_alphabetic()
}

pub fn c_is_ascii_alphanumeric(c: char) -> bool {
    c.is_ascii_alphanumeric()
}

pub fn c_is_ascii_whitespace(c: char) -> bool {
    c.is_ascii_whitespace()
}

pub fn c_is_ascii_control(c: char) -> bool {
    c.is_ascii_control()
}

pub fn c_is_ascii_punctuation(c: char) -> bool {
    c.is_ascii_punctuation()
}

pub fn c_is_ascii_hexdigit(c: char) -> bool {
    c.is_ascii_hexdigit()
}

pub fn c_is_ascii_graphic(c: char) -> bool {
    c.is_ascii_graphic()
}

pub fn c_is_ascii_uppercase(c: char) -> bool {
    c.is_ascii_uppercase()
}

pub fn c_is_ascii_lowercase(c: char) -> bool {
    c.is_ascii_lowercase()
}

pub fn c_to_ascii_uppercase(c: char) -> char {
    c.to_ascii_uppercase()
}

pub fn c_to_ascii_lowercase(c: char) -> char {
    c.to_ascii_lowercase()
}

pub fn c_eq_ignore_ascii_case(a: char, b: char) -> bool {
    a.eq_ignore_ascii_case(&b)
}

pub fn c_from_u32(code: u32) -> Option<char> {
    char::from_u32(code)
}

pub fn c_from_digit(digit: u32, radix: u32) -> Option<char> {
    char::from_digit(digit, radix)
}

/// Clasificación aproximada por categoría general de Unicode.
///
/// La biblioteca estándar de Rust no expone la categoría general de un `char`,
/// así que se usan tablas de rangos para las categorías que la superficie
/// necesita. Los rangos cubren los bloques habituales; no pretenden ser una
/// implementación completa de UAX #44.
fn is_unicode_category(c: char, categories: &[char]) -> bool {
    let code = c as u32;
    categories.iter().any(|category| match category {
        'P' => matches!(
            code,
            0x21..=0x2F
                | 0x3A..=0x40
                | 0x5B..=0x60
                | 0x7B..=0x7E
                | 0xA1
                | 0xA7
                | 0xAB
                | 0xB6
                | 0xB7
                | 0xBB
                | 0xBF
                | 0x2010..=0x2027
                | 0x2030..=0x205E
                | 0x3001..=0x3003
                | 0x3008..=0x3011
                | 0xFF01..=0xFF0F
                | 0xFF1A..=0xFF20
        ),
        'S' => matches!(
            code,
            0x24
                | 0x2B
                | 0x3C..=0x3E
                | 0x5E
                | 0x60
                | 0x7C
                | 0x7E
                | 0xA2..=0xA6
                | 0xA8..=0xA9
                | 0xAC
                | 0xAE..=0xB1
                | 0xB4
                | 0xB8
                | 0xD7
                | 0xF7
                | 0x2190..=0x2BFF
        ),
        _ => false,
    })
}

pub fn b_to_string(value: bool) -> String {
    if value {
        "true".to_owned()
    } else {
        "false".to_owned()
    }
}

// --- verbum: Str ---------------------------------------------------------

pub fn s_len(value: &str) -> usize {
    value.len()
}

pub fn s_is_empty(value: &str) -> bool {
    value.is_empty()
}

pub fn s_to_string(value: &str) -> String {
    value.to_owned()
}

pub fn s_chars_count(value: &str) -> usize {
    value.chars().count()
}

pub fn s_trim(value: &str) -> &str {
    value.trim()
}

pub fn s_trim_start(value: &str) -> &str {
    value.trim_start()
}

pub fn s_trim_end(value: &str) -> &str {
    value.trim_end()
}

pub fn s_split<'a>(value: &'a str, sep: &str) -> Vec<&'a str> {
    value.split(sep).collect()
}

pub fn s_rsplit<'a>(value: &'a str, sep: &str) -> Vec<&'a str> {
    value.rsplit(sep).collect()
}

pub fn s_splitn<'a>(value: &'a str, n: usize, sep: &str) -> Vec<&'a str> {
    value.splitn(n, sep).collect()
}

pub fn s_rsplitn<'a>(value: &'a str, n: usize, sep: &str) -> Vec<&'a str> {
    value.rsplitn(n, sep).collect()
}

pub fn s_split_terminator<'a>(value: &'a str, sep: &str) -> Vec<&'a str> {
    value.split_terminator(sep).collect()
}

pub fn s_split_whitespace(value: &str) -> Vec<&str> {
    value.split_whitespace().collect()
}

pub fn s_split_ascii_whitespace(value: &str) -> Vec<&str> {
    value.split_ascii_whitespace().collect()
}

pub fn s_lines(value: &str) -> Vec<&str> {
    value.lines().collect()
}

pub fn s_splitlines(value: &str) -> Vec<&str> {
    value.lines().collect()
}

pub fn s_starts_with(value: &str, prefix: &str) -> bool {
    value.starts_with(prefix)
}

pub fn s_ends_with(value: &str, suffix: &str) -> bool {
    value.ends_with(suffix)
}

pub fn s_contains(value: &str, pat: &str) -> bool {
    value.contains(pat)
}

pub fn s_find(value: &str, pat: &str) -> Option<usize> {
    value.find(pat)
}

pub fn s_rfind(value: &str, pat: &str) -> Option<usize> {
    value.rfind(pat)
}

pub fn s_replace(value: &str, from: &str, to: &str) -> String {
    value.replace(from, to)
}

pub fn s_replacen(value: &str, from: &str, to: &str, n: usize) -> String {
    value.replacen(from, to, n)
}

pub fn s_to_lowercase(value: &str) -> String {
    value.to_lowercase()
}

pub fn s_to_uppercase(value: &str) -> String {
    value.to_uppercase()
}

pub fn s_to_ascii_lowercase(value: &str) -> String {
    value.to_ascii_lowercase()
}

pub fn s_to_ascii_uppercase(value: &str) -> String {
    value.to_ascii_uppercase()
}

pub fn s_eq_ignore_ascii_case(value: &str, other: &str) -> bool {
    value.eq_ignore_ascii_case(other)
}

pub fn s_starts_with_ignore_case(value: &str, prefix: &str) -> bool {
    value
        .get(..prefix.len())
        .is_some_and(|head| head.eq_ignore_ascii_case(prefix))
}

pub fn s_strip_prefix<'a>(value: &'a str, prefix: &str) -> Option<&'a str> {
    value.strip_prefix(prefix)
}

pub fn s_strip_suffix<'a>(value: &'a str, suffix: &str) -> Option<&'a str> {
    value.strip_suffix(suffix)
}

pub fn s_partition<'a>(value: &'a str, sep: &str) -> (&'a str, &'a str, &'a str) {
    match value.find(sep) {
        Some(index) => (
            &value[..index],
            &value[index..index + sep.len()],
            &value[index + sep.len()..],
        ),
        None => (value, "", ""),
    }
}

pub fn s_rpartition<'a>(value: &'a str, sep: &str) -> (&'a str, &'a str, &'a str) {
    match value.rfind(sep) {
        Some(index) => (
            &value[..index],
            &value[index..index + sep.len()],
            &value[index + sep.len()..],
        ),
        None => ("", "", value),
    }
}

pub fn s_trim_matches<'a>(value: &'a str, ch: char) -> &'a str {
    value.trim_matches(ch)
}

pub fn s_trim_start_matches<'a>(value: &'a str, ch: char) -> &'a str {
    value.trim_start_matches(ch)
}

pub fn s_trim_end_matches<'a>(value: &'a str, ch: char) -> &'a str {
    value.trim_end_matches(ch)
}

pub fn s_is_char_boundary(value: &str, index: usize) -> bool {
    value.is_char_boundary(index)
}

pub fn s_isalpha(value: &str) -> bool {
    !value.is_empty() && value.chars().all(char::is_alphabetic)
}

pub fn s_isdigit(value: &str) -> bool {
    !value.is_empty() && value.chars().all(char::is_numeric)
}

pub fn s_isalnum(value: &str) -> bool {
    !value.is_empty() && value.chars().all(char::is_alphanumeric)
}

pub fn s_isspace(value: &str) -> bool {
    !value.is_empty() && value.chars().all(char::is_whitespace)
}

pub fn s_islower(value: &str) -> bool {
    value.chars().any(char::is_lowercase) && !value.chars().any(char::is_uppercase)
}

pub fn s_isupper(value: &str) -> bool {
    value.chars().any(char::is_uppercase) && !value.chars().any(char::is_lowercase)
}

pub fn s_istitle(value: &str) -> bool {
    if value.is_empty() {
        return false;
    }
    let mut previous_alphabetic = false;
    for ch in value.chars() {
        if ch.is_alphabetic() {
            let upper = ch.is_uppercase();
            if previous_alphabetic == upper {
                return false;
            }
            previous_alphabetic = true;
        } else {
            previous_alphabetic = false;
        }
    }
    true
}

pub fn s_capitalize(value: &str) -> String {
    let mut chars = value.chars();
    match chars.next() {
        Some(first) => {
            let mut out = String::new();
            out.extend(first.to_uppercase());
            out.extend(chars.flat_map(char::to_lowercase));
            out
        }
        None => String::new(),
    }
}

pub fn s_title(value: &str) -> String {
    let mut out = String::new();
    let mut start_word = true;
    for ch in value.chars() {
        if ch.is_alphanumeric() {
            if start_word {
                out.extend(ch.to_uppercase());
            } else {
                out.extend(ch.to_lowercase());
            }
            start_word = false;
        } else {
            out.push(ch);
            start_word = true;
        }
    }
    out
}

fn pad(value: &str, width: usize, fill: char, mode: u8) -> String {
    let len = value.chars().count();
    if len >= width {
        return value.to_owned();
    }
    let total = width - len;
    let (left, right) = match mode {
        0 => (total / 2, total - total / 2),
        1 => (0, total),
        2 => (total, 0),
        _ => (total, 0),
    };
    let mut out = String::new();
    out.extend(std::iter::repeat_n(fill, left));
    out.push_str(value);
    out.extend(std::iter::repeat_n(fill, right));
    out
}

pub fn s_center(value: &str, width: usize, fill: char) -> String {
    pad(value, width, fill, 0)
}

pub fn s_ljust(value: &str, width: usize, fill: char) -> String {
    pad(value, width, fill, 1)
}

pub fn s_rjust(value: &str, width: usize, fill: char) -> String {
    pad(value, width, fill, 2)
}

pub fn s_zfill(value: &str, width: usize) -> String {
    let negative = value.starts_with('-') || value.starts_with('+');
    let digits = value.chars().count() - usize::from(negative);
    if digits >= width {
        return value.to_owned();
    }
    let zeros = width - digits;
    let mut out = String::new();
    if negative {
        out.push(value.chars().next().unwrap_or('-'));
        out.extend(std::iter::repeat_n('0', zeros));
        out.push_str(&value[1..]);
    } else {
        out.extend(std::iter::repeat_n('0', zeros));
        out.push_str(value);
    }
    out
}

// --- verbum: String ------------------------------------------------------

pub fn str_new() -> String {
    String::new()
}

pub fn str_with_capacity(n: usize) -> String {
    String::with_capacity(n)
}

pub fn str_from(value: &str) -> String {
    value.to_owned()
}

pub fn str_clone(value: &String) -> String {
    value.clone()
}

pub fn str_len(value: &String) -> usize {
    value.len()
}

pub fn str_push(value: &mut String, ch: char) {
    value.push(ch);
}

pub fn str_push_str(value: &mut String, other: &str) {
    value.push_str(other);
}

pub fn str_pop(value: &mut String) -> Option<char> {
    value.pop()
}

pub fn str_clear(value: &mut String) {
    value.clear();
}

pub fn str_insert(value: &mut String, index: usize, ch: char) {
    value.insert(index, ch);
}

pub fn str_insert_str(value: &mut String, index: usize, other: &str) {
    value.insert_str(index, other);
}

pub fn str_remove(value: &mut String, index: usize) -> char {
    value.remove(index)
}

pub fn str_truncate(value: &mut String, new_len: usize) {
    value.truncate(new_len);
}

pub fn str_as_str<'a>(value: &'a String) -> &'a str {
    value.as_str()
}

pub fn str_into_bytes(value: String) -> Vec<u8> {
    value.into_bytes()
}

pub fn str_repeat(value: &String, n: usize) -> String {
    value.repeat(n)
}

pub fn str_reserve(value: &mut String, additional: usize) {
    value.reserve(additional);
}

pub fn str_shrink_to_fit(value: &mut String) {
    value.shrink_to_fit();
}

pub fn str_capacity(value: &String) -> usize {
    value.capacity()
}

pub fn str_split_off(value: &mut String, at: usize) -> String {
    value.split_off(at)
}

pub fn str_replace_range_bounds(value: &mut String, range: std::ops::Range<usize>, replacement: &str) {
    value.replace_range(range, replacement);
}

pub fn s_get_range(value: &str, range: std::ops::Range<usize>) -> Option<&str> {
    value.get(range)
}

pub fn s_split_at(value: &str, mid: usize) -> (&str, &str) {
    value.split_at(mid)
}

pub fn s_as_bytes(value: &str) -> Vec<u8> {
    value.as_bytes().to_vec()
}

#[allow(dead_code)]
pub fn str_replace_range(value: &mut String, start: usize, end: usize, replacement: &str) {
    value.replace_range(start..end, replacement);
}

pub fn str_extend(value: &mut String, other: &str) {
    value.push_str(other);
}

// ---------------------------------------------------------------------------
// Ayudantes genéricos de colecciones (métodos que `Vec` no expone directamente).
// ---------------------------------------------------------------------------

pub fn vec_sum<T>(value: Vec<T>) -> T
where
    T: std::iter::Sum<T>,
{
    value.into_iter().sum()
}

pub fn vec_product<T>(value: Vec<T>) -> T
where
    T: std::iter::Product<T>,
{
    value.into_iter().product()
}

pub fn vec_join<T: AsRef<str>>(value: &[T], sep: &str) -> String {
    value
        .iter()
        .map(AsRef::as_ref)
        .collect::<Vec<_>>()
        .join(sep)
}

pub fn vec_concat<T: Clone>(value: &[Vec<T>]) -> Vec<T> {
    let mut out = Vec::new();
    for item in value {
        out.extend(item.iter().cloned());
    }
    out
}

pub fn vec_min<T: PartialOrd>(value: &[T]) -> Option<&T> {
    let mut best: Option<&T> = None;
    for item in value {
        match best {
            Some(current) if current <= item => {}
            _ => best = Some(item),
        }
    }
    best
}

pub fn vec_max<T: PartialOrd>(value: &[T]) -> Option<&T> {
    let mut best: Option<&T> = None;
    for item in value {
        match best {
            Some(current) if current >= item => {}
            _ => best = Some(item),
        }
    }
    best
}

pub fn vec_clone<T: Clone>(value: &[T]) -> Vec<T> {
    value.to_vec()
}

pub fn vec_to_string<T: crate::Show>(value: &[T]) -> String {
    let mut out = String::from("[");
    for (index, item) in value.iter().enumerate() {
        if index > 0 {
            out.push_str(", ");
        }
        out.push_str(&crate::Show::show(item));
    }
    out.push(']');
    out
}

pub fn vec_retain<T: Clone, F: FnMut(T) -> bool>(value: &mut Vec<T>, mut f: F) {
    value.retain(|item| f(item.clone()));
}

pub fn vec_sort_by<T: Clone, F: FnMut(T, T) -> std::cmp::Ordering>(
    value: &mut Vec<T>,
    mut f: F,
) {
    value.sort_by(|a, b| f(a.clone(), b.clone()));
}

pub fn vec_sort_unstable_by<T: Clone, F: FnMut(T, T) -> std::cmp::Ordering>(
    value: &mut Vec<T>,
    mut f: F,
) {
    value.sort_unstable_by(|a, b| f(a.clone(), b.clone()));
}

pub fn vec_is_sorted_by<T: Clone, F: FnMut(T, T) -> std::cmp::Ordering>(
    value: &[T],
    mut f: F,
) -> bool {
    value.windows(2).all(|w| f(w[0].clone(), w[1].clone()) != std::cmp::Ordering::Greater)
}

pub fn vec_dedup_by<T: Clone, F: FnMut(T, T) -> bool>(value: &mut Vec<T>, mut f: F) {
    value.dedup_by(|a, b| f(a.clone(), b.clone()));
}

pub fn vec_binary_search_by<T: Clone, F: FnMut(T) -> std::cmp::Ordering>(
    value: &[T],
    mut f: F,
) -> Result<usize, usize> {
    value.binary_search_by(|probe| f(probe.clone()))
}

pub fn vec_partition_point<T: Clone, F: FnMut(T) -> bool>(value: &[T], mut f: F) -> usize {
    value.partition_point(|item| f(item.clone()))
}

// ---------------------------------------------------------------------------
// `Map[K, V]` / `Set[T]`.
// ---------------------------------------------------------------------------

pub fn map_retain<K, V, F>(value: &mut std::collections::HashMap<K, V>, mut f: F)
where
    K: Clone + std::hash::Hash + Eq,
    V: Clone,
    F: FnMut(K, V) -> bool,
{
    value.retain(|key, item| f(key.clone(), item.clone()));
}

pub fn map_get_or_insert<K, V>(
    value: &mut std::collections::HashMap<K, V>,
    key: K,
    default: V,
) -> &mut V
where
    K: std::hash::Hash + Eq,
{
    value.entry(key).or_insert(default)
}

pub fn map_get_or_insert_with<K, V, F>(
    value: &mut std::collections::HashMap<K, V>,
    key: K,
    f: F,
) -> &mut V
where
    K: std::hash::Hash + Eq,
    F: FnOnce() -> V,
{
    value.entry(key).or_insert_with(f)
}

pub fn map_to_string<K: crate::Show, V: crate::Show>(
    value: &std::collections::HashMap<K, V>,
) -> String {
    let mut items = value
        .iter()
        .map(|(key, item)| format!("{}: {}", crate::Show::show(key), crate::Show::show(item)))
        .collect::<Vec<_>>();
    items.sort();
    format!("{{{}}}", items.join(", "))
}

pub fn set_retain<T, F>(value: &mut std::collections::HashSet<T>, mut f: F)
where
    T: Clone + std::hash::Hash + Eq,
    F: FnMut(T) -> bool,
{
    value.retain(|item| f(item.clone()));
}

pub fn set_union<T>(a: &std::collections::HashSet<T>, b: &std::collections::HashSet<T>) -> std::collections::HashSet<T>
where
    T: Clone + std::hash::Hash + Eq,
{
    a | b
}

pub fn set_intersection<T>(a: &std::collections::HashSet<T>, b: &std::collections::HashSet<T>) -> std::collections::HashSet<T>
where
    T: Clone + std::hash::Hash + Eq,
{
    a & b
}

pub fn set_difference<T>(a: &std::collections::HashSet<T>, b: &std::collections::HashSet<T>) -> std::collections::HashSet<T>
where
    T: Clone + std::hash::Hash + Eq,
{
    a - b
}

pub fn set_symmetric_difference<T>(a: &std::collections::HashSet<T>, b: &std::collections::HashSet<T>) -> std::collections::HashSet<T>
where
    T: Clone + std::hash::Hash + Eq,
{
    a ^ b
}

pub fn set_difference_update<T>(a: &mut std::collections::HashSet<T>, b: &std::collections::HashSet<T>)
where
    T: Clone + std::hash::Hash + Eq,
{
    a.retain(|item| !b.contains(item));
}

pub fn set_intersection_update<T>(a: &mut std::collections::HashSet<T>, b: &std::collections::HashSet<T>)
where
    T: Clone + std::hash::Hash + Eq,
{
    a.retain(|item| b.contains(item));
}

pub fn set_symmetric_difference_update<T>(a: &mut std::collections::HashSet<T>, b: &std::collections::HashSet<T>)
where
    T: Clone + std::hash::Hash + Eq,
{
    let diff = &*a ^ b;
    *a = diff;
}

pub fn set_to_string<T: crate::Show>(value: &std::collections::HashSet<T>) -> String {
    let mut items = value
        .iter()
        .map(|item| crate::Show::show(item))
        .collect::<Vec<_>>();
    items.sort();
    format!("{{{}}}", items.join(", "))
}

// ---------------------------------------------------------------------------
// `numerus`: funciones matemáticas libres.
// ---------------------------------------------------------------------------

pub fn num_sqrt(x: f64) -> f64 {
    x.sqrt()
}

pub fn num_cbrt(x: f64) -> f64 {
    x.cbrt()
}

pub fn num_pow(x: f64, y: f64) -> f64 {
    x.powf(y)
}

pub fn num_exp(x: f64) -> f64 {
    x.exp()
}

pub fn num_exp2(x: f64) -> f64 {
    x.exp2()
}

pub fn num_exp_m1(x: f64) -> f64 {
    x.exp_m1()
}

pub fn num_ln(x: f64) -> f64 {
    x.ln()
}

pub fn num_ln_1p(x: f64) -> f64 {
    x.ln_1p()
}

pub fn num_log10(x: f64) -> f64 {
    x.log10()
}

pub fn num_log2(x: f64) -> f64 {
    x.log2()
}

pub fn num_sin(x: f64) -> f64 {
    x.sin()
}

pub fn num_cos(x: f64) -> f64 {
    x.cos()
}

pub fn num_tan(x: f64) -> f64 {
    x.tan()
}

pub fn num_asin(x: f64) -> f64 {
    x.asin()
}

pub fn num_acos(x: f64) -> f64 {
    x.acos()
}

pub fn num_atan(x: f64) -> f64 {
    x.atan()
}

pub fn num_atan2(y: f64, x: f64) -> f64 {
    y.atan2(x)
}

pub fn num_sinh(x: f64) -> f64 {
    x.sinh()
}

pub fn num_cosh(x: f64) -> f64 {
    x.cosh()
}

pub fn num_tanh(x: f64) -> f64 {
    x.tanh()
}

pub fn num_asinh(x: f64) -> f64 {
    x.asinh()
}

pub fn num_acosh(x: f64) -> f64 {
    x.acosh()
}

pub fn num_atanh(x: f64) -> f64 {
    x.atanh()
}

pub fn num_floor(x: f64) -> f64 {
    x.floor()
}

pub fn num_ceil(x: f64) -> f64 {
    x.ceil()
}

pub fn num_round(x: f64) -> f64 {
    x.round()
}

pub fn num_trunc(x: f64) -> f64 {
    x.trunc()
}

pub fn num_fract(x: f64) -> f64 {
    x.fract()
}

pub fn num_copysign(x: f64, y: f64) -> f64 {
    x.copysign(y)
}

pub fn num_hypot(x: f64, y: f64) -> f64 {
    x.hypot(y)
}

pub fn num_mul_add(a: f64, b: f64, c: f64) -> f64 {
    a.mul_add(b, c)
}

pub fn num_sin_cos(x: f64) -> (f64, f64) {
    x.sin_cos()
}

pub fn num_fmod(x: f64, y: f64) -> f64 {
    x % y
}

pub fn num_remainder(x: f64, y: f64) -> f64 {
    if y == 0.0 || !x.is_finite() {
        return f64::NAN;
    }
    x - (x / y).round() * y
}

pub fn num_modf(x: f64) -> (f64, f64) {
    (x.trunc(), x.fract())
}

pub fn num_frexp(x: f64) -> (f64, i32) {
    if x == 0.0 || !x.is_finite() {
        return (x, 0);
    }
    let mut mantissa = x;
    let mut exponent = 0;
    while mantissa.abs() >= 1.0 {
        mantissa /= 2.0;
        exponent += 1;
    }
    while mantissa.abs() < 0.5 {
        mantissa *= 2.0;
        exponent -= 1;
    }
    (mantissa, exponent)
}

pub fn num_ldexp(x: f64, exp: i32) -> f64 {
    x * 2f64.powi(exp)
}

pub fn num_nextafter(x: f64, y: f64) -> f64 {
    if y > x {
        x.next_up()
    } else if y < x {
        x.next_down()
    } else {
        y
    }
}

/// Aproximación de Abramowitz–Stegun 7.1.26 (error < 1.5e-7).
pub fn num_erf(x: f64) -> f64 {
    let sign = if x < 0.0 { -1.0 } else { 1.0 };
    let x = x.abs();
    let t = 1.0 / (1.0 + 0.327_591_1 * x);
    let y = 1.0
        - (((((1.061_405_429 * t - 1.453_152_027) * t) + 1.421_413_741) * t - 0.284_496_736) * t
            + 0.254_829_592)
            * t
            * (-x * x).exp();
    sign * y
}

pub fn num_erfc(x: f64) -> f64 {
    1.0 - num_erf(x)
}

/// Lanczos (g = 7, n = 9), error relativo ~1e-15.
pub fn num_gamma(x: f64) -> f64 {
    const COEFFS: [f64; 9] = [
        0.999_999_999_999_809_9,
        676.520_368_121_885_1,
        -1_259.139_216_722_402_8,
        771.323_428_777_653_1,
        -176.615_029_162_140_6,
        12.507_343_278_686_905,
        -0.138_571_095_265_720_12,
        9.984_369_578_019_572e-6,
        1.505_632_735_149_311_6e-7,
    ];
    if x < 0.5 {
        return std::f64::consts::PI / ((std::f64::consts::PI * x).sin() * num_gamma(1.0 - x));
    }
    let x = x - 1.0;
    let mut a = COEFFS[0];
    let t = x + 7.5;
    for (index, coeff) in COEFFS.iter().enumerate().skip(1) {
        a += coeff / (x + index as f64);
    }
    (2.0 * std::f64::consts::PI).sqrt() * t.powf(x + 0.5) * (-t).exp() * a
}

pub fn num_lgamma(x: f64) -> f64 {
    num_gamma(x).ln()
}

pub fn num_isqrt(n: u32) -> u32 {
    let mut root = (n as f64).sqrt() as u32;
    while root > 0 && root.saturating_mul(root) > n {
        root -= 1;
    }
    while (root + 1).saturating_mul(root + 1) <= n {
        root += 1;
    }
    root
}

// --- std.proba -------------------------------------------------------------

/// `proba.assert`: aborta si la condición es falsa.
pub fn assert(condition: bool, message: &str) {
    if !condition {
        panic!("assertion failed: {message}");
    }
}

/// `proba.assert_eq`: aborta si los valores difieren.
pub fn assert_eq<T: crate::Show + std::cmp::PartialEq>(actual: T, expected: T) {
    if actual != expected {
        panic!(
            "assertion failed: expected {} but got {}",
            crate::Show::show(&expected),
            crate::Show::show(&actual)
        );
    }
}

/// `proba.assert_ne`: aborta si los valores coinciden.
pub fn assert_ne<T: crate::Show + std::cmp::PartialEq>(actual: T, unexpected: T) {
    if actual == unexpected {
        panic!(
            "assertion failed: expected a value different from {}",
            crate::Show::show(&actual)
        );
    }
}

/// `proba.assert_approx_eq`: aborta si la diferencia supera la tolerancia.
pub fn assert_approx_eq(actual: f64, expected: f64, tolerance: f64) {
    let difference = (actual - expected).abs();
    if !(difference <= tolerance) {
        panic!(
            "assertion failed: expected {expected} ± {tolerance} but got {actual}"
        );
    }
}

/// `proba.fail`: aborta siempre.
pub fn fail(message: &str) -> ! {
    panic!("{message}");
}

/// `proba.assert_eq_msg`: igualdad con mensaje del usuario.
pub fn assert_eq_msg<T: crate::Show + std::cmp::PartialEq>(
    actual: T,
    expected: T,
    message: &str,
) {
    if actual != expected {
        panic!(
            "{message}: expected {} but got {}",
            crate::Show::show(&expected),
            crate::Show::show(&actual)
        );
    }
}

/// `proba.assert_ne_msg`: desigualdad con mensaje del usuario.
pub fn assert_ne_msg<T: crate::Show + std::cmp::PartialEq>(
    actual: T,
    unexpected: T,
    message: &str,
) {
    if actual == unexpected {
        panic!(
            "{message}: expected a value different from {}",
            crate::Show::show(&actual)
        );
    }
}

// --- std.fluxus ------------------------------------------------------------

/// `fluxus.read_line`: lee una línea de la entrada estándar sin el salto final.
pub fn read_line() -> std::result::Result<String, crate::std::fluxus::IoError> {
    let mut line = std::string::String::new();
    match std::io::stdin().read_line(&mut line) {
        std::result::Result::Ok(0) => std::result::Result::Err(crate::std::fluxus::IoError {
            message: "EOF".to_owned(),
        }),
        std::result::Result::Ok(_) => {
            if line.ends_with('\n') {
                line.pop();
                if line.ends_with('\r') {
                    line.pop();
                }
            }
            std::result::Result::Ok(line)
        }
        std::result::Result::Err(error) => {
            std::result::Result::Err(crate::std::fluxus::IoError {
                message: error.to_string(),
            })
        }
    }
}

/// `fluxus.read_stdin_to_string`: consume toda la entrada estándar.
pub fn read_stdin_to_string() -> std::result::Result<String, crate::std::fluxus::IoError> {
    let mut text = std::string::String::new();
    match std::io::Read::read_to_string(&mut std::io::stdin(), &mut text) {
        std::result::Result::Ok(_) => std::result::Result::Ok(text),
        std::result::Result::Err(error) => {
            std::result::Result::Err(crate::std::fluxus::IoError {
                message: error.to_string(),
            })
        }
    }
}

/// `fluxus.write_stdout`: escribe en la salida estándar sin salto.
pub fn write_stdout(text: &str) -> std::result::Result<(), crate::std::fluxus::IoError> {
    use std::io::Write;
    match std::io::stdout().write_all(text.as_bytes()) {
        std::result::Result::Ok(()) => std::result::Result::Ok(()),
        std::result::Result::Err(error) => std::result::Result::Err(crate::std::fluxus::IoError {
            message: error.to_string(),
        }),
    }
}

/// `fluxus.write_stderr`: escribe en la salida de error sin salto.
pub fn write_stderr(text: &str) -> std::result::Result<(), crate::std::fluxus::IoError> {
    use std::io::Write;
    match std::io::stderr().write_all(text.as_bytes()) {
        std::result::Result::Ok(()) => std::result::Result::Ok(()),
        std::result::Result::Err(error) => std::result::Result::Err(crate::std::fluxus::IoError {
            message: error.to_string(),
        }),
    }
}

/// `fluxus.flush_stdout`: vacía el buffer de la salida estándar.
pub fn flush_stdout() -> std::result::Result<(), crate::std::fluxus::IoError> {
    use std::io::Write;
    match std::io::stdout().flush() {
        std::result::Result::Ok(()) => std::result::Result::Ok(()),
        std::result::Result::Err(error) => std::result::Result::Err(crate::std::fluxus::IoError {
            message: error.to_string(),
        }),
    }
}

/// `fluxus.flush_stderr`: vacía el buffer de la salida de error.
pub fn flush_stderr() -> std::result::Result<(), crate::std::fluxus::IoError> {
    use std::io::Write;
    match std::io::stderr().flush() {
        std::result::Result::Ok(()) => std::result::Result::Ok(()),
        std::result::Result::Err(error) => std::result::Result::Err(crate::std::fluxus::IoError {
            message: error.to_string(),
        }),
    }
}

// ---------------------------------------------------------------------------
// `std::via`: sistema de archivos.
// ---------------------------------------------------------------------------

use std::sync::{LazyLock, Mutex};

/// Descriptores abiertos por `via`. El lenguaje todavía no tiene tipos
/// opacos, así que `File` es un índice a esta tabla.
static VIA_FILES: LazyLock<Mutex<Vec<Option<std::fs::File>>>> =
    LazyLock::new(|| Mutex::new(Vec::new()));

fn via_error(error: impl std::fmt::Display) -> crate::std::via::IoError {
    crate::std::via::IoError {
        message: error.to_string(),
    }
}

fn via_register(file: std::fs::File) -> u64 {
    let mut files = VIA_FILES
        .lock()
        .unwrap_or_else(|poison| poison.into_inner());
    files.push(Some(file));
    (files.len() - 1) as u64
}

fn via_with_file<R>(
    handle: u64,
    operation: impl FnOnce(&mut std::fs::File) -> std::io::Result<R>,
) -> std::result::Result<R, crate::std::via::IoError> {
    let mut files = VIA_FILES
        .lock()
        .unwrap_or_else(|poison| poison.into_inner());
    let slot = files.get_mut(handle as usize).and_then(Option::as_mut);
    match slot {
        Some(file) => operation(file).map_err(via_error),
        None => std::result::Result::Err(via_error("descriptor cerrado")),
    }
}

fn via_info(metadata: &std::fs::Metadata) -> crate::std::via::FileInfo {
    let modified_ms = metadata
        .modified()
        .ok()
        .and_then(|time| time.duration_since(std::time::UNIX_EPOCH).ok())
        .and_then(|since| i64::try_from(since.as_millis()).ok());
    crate::std::via::FileInfo {
        len: metadata.len(),
        is_file: metadata.is_file(),
        is_dir: metadata.is_dir(),
        is_symlink: metadata.file_type().is_symlink(),
        readonly: metadata.permissions().readonly(),
        modified_ms,
    }
}

pub fn via_exists(path: &str) -> bool {
    std::path::Path::new(path).exists()
}

pub fn via_is_file(path: &str) -> bool {
    std::path::Path::new(path).is_file()
}

pub fn via_is_dir(path: &str) -> bool {
    std::path::Path::new(path).is_dir()
}

pub fn via_is_symlink(path: &str) -> bool {
    std::fs::symlink_metadata(path).is_ok_and(|metadata| metadata.file_type().is_symlink())
}

pub fn via_metadata(
    path: &str,
) -> std::result::Result<crate::std::via::FileInfo, crate::std::via::IoError> {
    match std::fs::symlink_metadata(path) {
        std::result::Result::Ok(metadata) => {
            let mut info = via_info(&metadata);
            if info.is_symlink {
                if let std::result::Result::Ok(target) = std::fs::metadata(path) {
                    info.len = target.len();
                    info.is_file = target.is_file();
                    info.is_dir = target.is_dir();
                    info.readonly = target.permissions().readonly();
                }
            }
            std::result::Result::Ok(info)
        }
        std::result::Result::Err(error) => std::result::Result::Err(via_error(error)),
    }
}

pub fn via_read_to_string(
    path: &str,
) -> std::result::Result<String, crate::std::via::IoError> {
    std::fs::read_to_string(path).map_err(via_error)
}

pub fn via_read_bytes(
    path: &str,
) -> std::result::Result<Vec<u8>, crate::std::via::IoError> {
    std::fs::read(path).map_err(via_error)
}

pub fn via_write_string(
    path: &str,
    contents: &str,
) -> std::result::Result<(), crate::std::via::IoError> {
    std::fs::write(path, contents).map_err(via_error)
}

pub fn via_write_bytes(
    path: &str,
    contents: Vec<u8>,
) -> std::result::Result<(), crate::std::via::IoError> {
    std::fs::write(path, contents).map_err(via_error)
}

pub fn via_append_string(
    path: &str,
    contents: &str,
) -> std::result::Result<(), crate::std::via::IoError> {
    use std::io::Write;
    let file = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
        .map_err(via_error)?;
    let mut file = file;
    file.write_all(contents.as_bytes()).map_err(via_error)
}

pub fn via_create_dir(path: &str) -> std::result::Result<(), crate::std::via::IoError> {
    std::fs::create_dir(path).map_err(via_error)
}

pub fn via_create_dir_all(path: &str) -> std::result::Result<(), crate::std::via::IoError> {
    std::fs::create_dir_all(path).map_err(via_error)
}

pub fn via_remove_file(path: &str) -> std::result::Result<(), crate::std::via::IoError> {
    std::fs::remove_file(path).map_err(via_error)
}

pub fn via_remove_dir(path: &str) -> std::result::Result<(), crate::std::via::IoError> {
    std::fs::remove_dir(path).map_err(via_error)
}

pub fn via_remove_dir_all(path: &str) -> std::result::Result<(), crate::std::via::IoError> {
    std::fs::remove_dir_all(path).map_err(via_error)
}

pub fn via_rename(
    from: &str,
    to: &str,
) -> std::result::Result<(), crate::std::via::IoError> {
    std::fs::rename(from, to).map_err(via_error)
}

pub fn via_copy(
    from: &str,
    to: &str,
) -> std::result::Result<u64, crate::std::via::IoError> {
    std::fs::copy(from, to).map_err(via_error)
}

pub fn via_canonicalize(
    path: &str,
) -> std::result::Result<String, crate::std::via::IoError> {
    match std::fs::canonicalize(path) {
        std::result::Result::Ok(path) => {
            std::result::Result::Ok(path.to_string_lossy().into_owned())
        }
        std::result::Result::Err(error) => std::result::Result::Err(via_error(error)),
    }
}

pub fn via_read_link(
    path: &str,
) -> std::result::Result<String, crate::std::via::IoError> {
    match std::fs::read_link(path) {
        std::result::Result::Ok(target) => {
            std::result::Result::Ok(target.to_string_lossy().into_owned())
        }
        std::result::Result::Err(error) => std::result::Result::Err(via_error(error)),
    }
}

pub fn via_symlink(
    target: &str,
    link: &str,
) -> std::result::Result<(), crate::std::via::IoError> {
    #[cfg(unix)]
    let result = std::os::unix::fs::symlink(target, link);
    #[cfg(windows)]
    let result = std::os::windows::fs::symlink_file(target, link);
    result.map_err(via_error)
}

pub fn via_hard_link(
    from: &str,
    to: &str,
) -> std::result::Result<(), crate::std::via::IoError> {
    std::fs::hard_link(from, to).map_err(via_error)
}

pub fn via_set_readonly(
    path: &str,
    readonly: bool,
) -> std::result::Result<(), crate::std::via::IoError> {
    let metadata = std::fs::metadata(path).map_err(via_error)?;
    let mut permissions = metadata.permissions();
    permissions.set_readonly(readonly);
    std::fs::set_permissions(path, permissions).map_err(via_error)
}

pub fn via_read_dir(
    path: &str,
) -> std::result::Result<Vec<crate::std::via::DirEntry>, crate::std::via::IoError> {
    let mut entries = Vec::new();
    for entry in std::fs::read_dir(path).map_err(via_error)? {
        let entry = entry.map_err(via_error)?;
        let file_type = entry.file_type().map_err(via_error)?;
        let metadata = entry.metadata().ok();
        entries.push(crate::std::via::DirEntry {
            path: entry.path().to_string_lossy().into_owned(),
            file_name: entry.file_name().to_string_lossy().into_owned(),
            is_dir: file_type.is_dir(),
            is_file: file_type.is_file(),
            is_symlink: file_type.is_symlink(),
            len: metadata.map_or(0, |metadata| metadata.len()),
        });
    }
    entries.sort_by(|left, right| left.path.cmp(&right.path));
    std::result::Result::Ok(entries)
}

fn via_walk_paths(
    root: &str,
    files: bool,
    dirs: bool,
) -> std::result::Result<Vec<String>, crate::std::via::IoError> {
    let mut result = Vec::new();
    let metadata = std::fs::symlink_metadata(root).map_err(via_error)?;
    if !metadata.is_dir() {
        if metadata.is_file() && files {
            result.push(root.to_owned());
        }
        return std::result::Result::Ok(result);
    }
    let mut stack = vec![root.to_owned()];
    while let Some(directory) = stack.pop() {
        if dirs {
            result.push(directory.clone());
        }
        for entry in std::fs::read_dir(&directory).map_err(via_error)? {
            let entry = entry.map_err(via_error)?;
            let file_type = entry.file_type().map_err(via_error)?;
            let path = entry.path().to_string_lossy().into_owned();
            if file_type.is_dir() {
                stack.push(path);
            } else if files {
                result.push(path);
            }
        }
    }
    result.sort();
    std::result::Result::Ok(result)
}

pub fn via_walk_names(
    path: &str,
) -> std::result::Result<Vec<String>, crate::std::via::IoError> {
    via_walk_paths(path, true, true)
}

pub fn via_walk_files(
    path: &str,
) -> std::result::Result<Vec<String>, crate::std::via::IoError> {
    via_walk_paths(path, true, false)
}

pub fn via_walk_dirs(
    path: &str,
) -> std::result::Result<Vec<String>, crate::std::via::IoError> {
    via_walk_paths(path, false, true)
}

pub fn via_current_dir() -> std::result::Result<String, crate::std::via::IoError> {
    match std::env::current_dir() {
        std::result::Result::Ok(path) => {
            std::result::Result::Ok(path.to_string_lossy().into_owned())
        }
        std::result::Result::Err(error) => std::result::Result::Err(via_error(error)),
    }
}

pub fn via_set_current_dir(
    path: &str,
) -> std::result::Result<(), crate::std::via::IoError> {
    std::env::set_current_dir(path).map_err(via_error)
}

pub fn via_temp_dir() -> String {
    std::env::temp_dir().to_string_lossy().into_owned()
}

pub fn via_which(program: &str) -> Option<String> {
    let candidate = std::path::Path::new(program);
    if candidate.components().count() > 1 {
        return candidate
            .is_file()
            .then(|| candidate.to_string_lossy().into_owned());
    }
    let paths = std::env::var_os("PATH")?;
    for directory in std::env::split_paths(&paths) {
        let direct = directory.join(program);
        if direct.is_file() {
            return Some(direct.to_string_lossy().into_owned());
        }
        #[cfg(windows)]
        for extension in ["exe", "bat", "cmd"] {
            let with_extension = directory.join(format!("{program}.{extension}"));
            if with_extension.is_file() {
                return Some(with_extension.to_string_lossy().into_owned());
            }
        }
    }
    None
}

pub fn via_join(base: &str, child: &str) -> String {
    std::path::Path::new(base)
        .join(child)
        .to_string_lossy()
        .into_owned()
}

pub fn via_parent(path: &str) -> Option<&str> {
    std::path::Path::new(path).parent().and_then(|it| it.to_str())
}

pub fn via_file_name(path: &str) -> Option<&str> {
    std::path::Path::new(path)
        .file_name()
        .and_then(|it| it.to_str())
}

pub fn via_extension(path: &str) -> Option<&str> {
    std::path::Path::new(path)
        .extension()
        .and_then(|it| it.to_str())
}

pub fn via_file_stem(path: &str) -> Option<&str> {
    std::path::Path::new(path)
        .file_stem()
        .and_then(|it| it.to_str())
}

pub fn via_is_absolute(path: &str) -> bool {
    std::path::Path::new(path).is_absolute()
}

pub fn via_file_open_read(
    path: &str,
) -> std::result::Result<crate::std::via::File, crate::std::via::IoError> {
    match std::fs::File::open(path) {
        std::result::Result::Ok(file) => std::result::Result::Ok(crate::std::via::File {
            handle: via_register(file),
        }),
        std::result::Result::Err(error) => std::result::Result::Err(via_error(error)),
    }
}

pub fn via_file_create(
    path: &str,
) -> std::result::Result<crate::std::via::File, crate::std::via::IoError> {
    match std::fs::File::create(path) {
        std::result::Result::Ok(file) => std::result::Result::Ok(crate::std::via::File {
            handle: via_register(file),
        }),
        std::result::Result::Err(error) => std::result::Result::Err(via_error(error)),
    }
}

pub fn via_file_append(
    path: &str,
) -> std::result::Result<crate::std::via::File, crate::std::via::IoError> {
    match std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
    {
        std::result::Result::Ok(file) => std::result::Result::Ok(crate::std::via::File {
            handle: via_register(file),
        }),
        std::result::Result::Err(error) => std::result::Result::Err(via_error(error)),
    }
}

pub fn via_file_read_to_string(
    handle: u64,
) -> std::result::Result<String, crate::std::via::IoError> {
    use std::io::Read;
    via_with_file(handle, |file| {
        let mut buffer = String::new();
        file.read_to_string(&mut buffer)?;
        std::result::Result::Ok(buffer)
    })
}

pub fn via_file_read_to_end(
    handle: u64,
) -> std::result::Result<Vec<u8>, crate::std::via::IoError> {
    use std::io::Read;
    via_with_file(handle, |file| {
        let mut buffer = Vec::new();
        file.read_to_end(&mut buffer)?;
        std::result::Result::Ok(buffer)
    })
}

pub fn via_file_write_str(
    handle: u64,
    text: &str,
) -> std::result::Result<usize, crate::std::via::IoError> {
    use std::io::Write;
    via_with_file(handle, |file| {
        file.write_all(text.as_bytes())?;
        file.flush()?;
        std::result::Result::Ok(text.len())
    })
}

pub fn via_file_write_all(
    handle: u64,
    bytes: Vec<u8>,
) -> std::result::Result<(), crate::std::via::IoError> {
    use std::io::Write;
    via_with_file(handle, |file| {
        file.write_all(&bytes)?;
        file.flush()
    })
}

pub fn via_file_flush(handle: u64) -> std::result::Result<(), crate::std::via::IoError> {
    use std::io::Write;
    via_with_file(handle, std::io::Write::flush)
}

pub fn via_file_seek(
    handle: u64,
    pos: u64,
) -> std::result::Result<u64, crate::std::via::IoError> {
    use std::io::Seek;
    via_with_file(handle, |file| file.seek(std::io::SeekFrom::Start(pos)))
}

pub fn via_file_seek_from_end(
    handle: u64,
    offset: u64,
) -> std::result::Result<u64, crate::std::via::IoError> {
    use std::io::Seek;
    let offset = i64::try_from(offset).unwrap_or(i64::MAX);
    via_with_file(handle, |file| file.seek(std::io::SeekFrom::End(-offset)))
}

pub fn via_file_set_len(
    handle: u64,
    len: u64,
) -> std::result::Result<(), crate::std::via::IoError> {
    via_with_file(handle, |file| file.set_len(len))
}

pub fn via_file_metadata(
    handle: u64,
) -> std::result::Result<crate::std::via::FileInfo, crate::std::via::IoError> {
    via_with_file(handle, |file| {
        let metadata = file.metadata()?;
        std::result::Result::Ok(via_info(&metadata))
    })
}

pub fn via_file_close(handle: u64) {
    let mut files = VIA_FILES
        .lock()
        .unwrap_or_else(|poison| poison.into_inner());
    if let Some(slot) = files.get_mut(handle as usize) {
        *slot = None;
    }
}

/// Proceso lanzado por `exsecutor`, con sus pipes si se pidieron `Stdio.piped()`.
struct ExsecChild {
    child: std::process::Child,
    stdin: Option<std::process::ChildStdin>,
    stdout: Option<std::process::ChildStdout>,
    stderr: Option<std::process::ChildStderr>,
}

/// Procesos lanzados por `exsecutor`. `Child` guarda un índice a esta tabla.
static EXSEC_CHILDREN: LazyLock<Mutex<Vec<Option<ExsecChild>>>> =
    LazyLock::new(|| Mutex::new(Vec::new()));

fn exsec_error(error: impl std::fmt::Display) -> crate::std::exsecutor::ExsecutorError {
    crate::std::exsecutor::ExsecutorError {
        message: error.to_string(),
    }
}

fn exsec_status_of(status: std::process::ExitStatus) -> crate::std::exsecutor::ExitStatus {
    crate::std::exsecutor::ExitStatus {
        code: status.code(),
        success: status.success(),
    }
}

fn exsec_output_of(output: std::process::Output) -> crate::std::exsecutor::Output {
    crate::std::exsecutor::Output {
        status: exsec_status_of(output.status),
        stdout: output.stdout,
        stderr: output.stderr,
    }
}

/// Modo de `Stdio`: 0 = el de Rust por defecto (lo decide `output()`/`spawn()`),
/// 1 = pipe, 2 = descartar, 3 = heredar.
fn exsec_stdio(mode: i32) -> Option<std::process::Stdio> {
    match mode {
        1 => Some(std::process::Stdio::piped()),
        2 => Some(std::process::Stdio::null()),
        3 => Some(std::process::Stdio::inherit()),
        _ => None,
    }
}

#[allow(clippy::too_many_arguments)]
fn exsec_command(
    program: &str,
    args: &[String],
    cwd: Option<String>,
    envs: &[String],
    clear_env: bool,
    stdin_mode: i32,
    stdout_mode: i32,
    stderr_mode: i32,
) -> std::process::Command {
    let mut command = std::process::Command::new(program);
    command.args(args);
    if let Some(directory) = cwd {
        command.current_dir(directory);
    }
    if clear_env {
        command.env_clear();
    }
    let mut pairs = envs.chunks_exact(2);
    for pair in &mut pairs {
        command.env(&pair[0], &pair[1]);
    }
    if let Some(stdio) = exsec_stdio(stdin_mode) {
        command.stdin(stdio);
    }
    if let Some(stdio) = exsec_stdio(stdout_mode) {
        command.stdout(stdio);
    }
    if let Some(stdio) = exsec_stdio(stderr_mode) {
        command.stderr(stdio);
    }
    command
}

#[allow(clippy::too_many_arguments)]
pub fn exsec_run(
    program: &str,
    args: Vec<String>,
    cwd: Option<String>,
    envs: Vec<String>,
    clear_env: bool,
    stdin_mode: i32,
    stdout_mode: i32,
    stderr_mode: i32,
) -> std::result::Result<crate::std::exsecutor::Output, crate::std::exsecutor::ExsecutorError> {
    let mut command = exsec_command(
        program, &args, cwd, &envs, clear_env, stdin_mode, stdout_mode, stderr_mode,
    );
    match command.output() {
        std::result::Result::Ok(output) => std::result::Result::Ok(exsec_output_of(output)),
        std::result::Result::Err(error) => std::result::Result::Err(exsec_error(error)),
    }
}

#[allow(clippy::too_many_arguments)]
pub fn exsec_status(
    program: &str,
    args: Vec<String>,
    cwd: Option<String>,
    envs: Vec<String>,
    clear_env: bool,
    stdin_mode: i32,
    stdout_mode: i32,
    stderr_mode: i32,
) -> std::result::Result<crate::std::exsecutor::ExitStatus, crate::std::exsecutor::ExsecutorError>
{
    let mut command = exsec_command(
        program, &args, cwd, &envs, clear_env, stdin_mode, stdout_mode, stderr_mode,
    );
    match command.status() {
        std::result::Result::Ok(status) => std::result::Result::Ok(exsec_status_of(status)),
        std::result::Result::Err(error) => std::result::Result::Err(exsec_error(error)),
    }
}

#[allow(clippy::too_many_arguments)]
pub fn exsec_spawn(
    program: &str,
    args: Vec<String>,
    cwd: Option<String>,
    envs: Vec<String>,
    clear_env: bool,
    stdin_mode: i32,
    stdout_mode: i32,
    stderr_mode: i32,
) -> std::result::Result<crate::std::exsecutor::Child, crate::std::exsecutor::ExsecutorError> {
    let mut command = exsec_command(
        program, &args, cwd, &envs, clear_env, stdin_mode, stdout_mode, stderr_mode,
    );
    match command.spawn() {
        std::result::Result::Ok(mut child) => {
            let stdin = child.stdin.take();
            let stdout = child.stdout.take();
            let stderr = child.stderr.take();
            let mut children = EXSEC_CHILDREN
                .lock()
                .unwrap_or_else(|poison| poison.into_inner());
            children.push(Some(ExsecChild {
                child,
                stdin,
                stdout,
                stderr,
            }));
            #[allow(clippy::cast_possible_truncation)]
            let handle = (children.len() - 1) as u64;
            std::result::Result::Ok(crate::std::exsecutor::Child { handle })
        }
        std::result::Result::Err(error) => std::result::Result::Err(exsec_error(error)),
    }
}

fn exsec_with_child<R>(
    handle: u64,
    operation: impl FnOnce(&mut ExsecChild) -> std::io::Result<R>,
) -> std::result::Result<R, crate::std::exsecutor::ExsecutorError> {
    let mut children = EXSEC_CHILDREN
        .lock()
        .unwrap_or_else(|poison| poison.into_inner());
    let slot = children.get_mut(handle as usize).and_then(Option::as_mut);
    match slot {
        Some(child) => operation(child).map_err(exsec_error),
        None => std::result::Result::Err(exsec_error("proceso inexistente")),
    }
}

pub fn exsec_child_wait(
    handle: u64,
) -> std::result::Result<crate::std::exsecutor::ExitStatus, crate::std::exsecutor::ExsecutorError>
{
    exsec_with_child(handle, |child| {
        child.child.wait().map(|status| exsec_status_of(status))
    })
}

pub fn exsec_child_try_wait(
    handle: u64,
) -> std::result::Result<
    Option<crate::std::exsecutor::ExitStatus>,
    crate::std::exsecutor::ExsecutorError,
> {
    exsec_with_child(handle, |child| {
        child.child.try_wait().map(|status| status.map(exsec_status_of))
    })
}

pub fn exsec_child_kill(
    handle: u64,
) -> std::result::Result<(), crate::std::exsecutor::ExsecutorError> {
    exsec_with_child(handle, |child| child.child.kill())
}

pub fn exsec_child_id(handle: u64) -> std::result::Result<u64, crate::std::exsecutor::ExsecutorError> {
    exsec_with_child(handle, |child| std::result::Result::Ok(u64::from(child.child.id())))
}

pub fn exsec_child_write_stdin(
    handle: u64,
    data: Vec<u8>,
) -> std::result::Result<u64, crate::std::exsecutor::ExsecutorError> {
    use std::io::Write;
    exsec_with_child(handle, |child| match child.stdin.as_mut() {
        Some(stdin) => stdin.write(&data).map(|written| written as u64),
        None => std::result::Result::Err(std::io::Error::new(
            std::io::ErrorKind::BrokenPipe,
            "stdin no está redirigido a un pipe",
        )),
    })
}

pub fn exsec_child_close_stdin(
    handle: u64,
) -> std::result::Result<(), crate::std::exsecutor::ExsecutorError> {
    exsec_with_child(handle, |child| {
        child.stdin = None;
        std::result::Result::Ok(())
    })
}

pub fn exsec_child_read_stdout(
    handle: u64,
    count: u64,
) -> std::result::Result<Vec<u8>, crate::std::exsecutor::ExsecutorError> {
    exsec_child_read(handle, count, true)
}

pub fn exsec_child_read_stderr(
    handle: u64,
    count: u64,
) -> std::result::Result<Vec<u8>, crate::std::exsecutor::ExsecutorError> {
    exsec_child_read(handle, count, false)
}

fn exsec_child_read(
    handle: u64,
    count: u64,
    stdout: bool,
) -> std::result::Result<Vec<u8>, crate::std::exsecutor::ExsecutorError> {
    use std::io::Read;
    #[allow(clippy::cast_possible_truncation)]
    let mut buffer = vec![0u8; usize::try_from(count).unwrap_or(0)];
    let read = exsec_with_child(handle, |child| {
        let pipe: Option<&mut dyn Read> = if stdout {
            child.stdout.as_mut().map(|pipe| pipe as &mut dyn Read)
        } else {
            child.stderr.as_mut().map(|pipe| pipe as &mut dyn Read)
        };
        match pipe {
            Some(pipe) => pipe.read(&mut buffer),
            None => std::result::Result::Ok(0),
        }
    })?;
    buffer.truncate(read);
    std::result::Result::Ok(buffer)
}

pub fn exsec_child_wait_with_output(
    handle: u64,
) -> std::result::Result<crate::std::exsecutor::Output, crate::std::exsecutor::ExsecutorError> {
    use std::io::Read;
    let (status, stdout, stderr) = exsec_with_child(handle, |child| {
        let mut stdout = Vec::new();
        if let Some(pipe) = child.stdout.as_mut() {
            pipe.read_to_end(&mut stdout)?;
        }
        let mut stderr = Vec::new();
        if let Some(pipe) = child.stderr.as_mut() {
            pipe.read_to_end(&mut stderr)?;
        }
        let status = child.child.wait()?;
        std::result::Result::Ok((status, stdout, stderr))
    })?;
    std::result::Result::Ok(crate::std::exsecutor::Output {
        status: exsec_status_of(status),
        stdout,
        stderr,
    })
}

pub fn exsec_which(program: &str) -> Option<String> {
    let candidate = std::path::Path::new(program);
    if candidate.components().count() > 1 {
        return candidate.is_file().then(|| candidate.to_string_lossy().into_owned());
    }
    let paths = std::env::var_os("PATH")?;
    for directory in std::env::split_paths(&paths) {
        let direct = directory.join(program);
        if direct.is_file() {
            return Some(direct.to_string_lossy().into_owned());
        }
        #[cfg(windows)]
        for extension in ["exe", "bat", "cmd"] {
            let with_extension = directory.join(format!("{program}.{extension}"));
            if with_extension.is_file() {
                return Some(with_extension.to_string_lossy().into_owned());
            }
        }
    }
    None
}

pub fn exsec_exit(code: i32) {
    std::process::exit(code);
}

pub fn exsec_argv() -> Vec<String> {
    std::env::args().collect()
}

fn ambitus_error(error: impl std::fmt::Display) -> crate::std::ambitus::VarError {
    crate::std::ambitus::VarError {
        message: error.to_string(),
    }
}

pub fn ambitus_var(
    key: &str,
) -> std::result::Result<String, crate::std::ambitus::VarError> {
    std::env::var(key).map_err(ambitus_error)
}

pub fn ambitus_set_var(key: &str, value: &str) {
    // Mutar el entorno es `unsafe` en Rust 2024 porque otros hilos pueden
    // estar leyéndolo. El lenguaje aún no tiene hilos: un solo hilo es seguro.
    unsafe { std::env::set_var(key, value) };
}

pub fn ambitus_remove_var(key: &str) {
    unsafe { std::env::remove_var(key) };
}

pub fn ambitus_vars() -> Vec<String> {
    let mut vars: Vec<String> = std::env::vars()
        .map(|(key, value)| format!("{key}={value}"))
        .collect();
    vars.sort();
    vars
}

pub fn ambitus_args() -> Vec<String> {
    std::env::args().collect()
}

pub fn ambitus_args_os() -> Vec<String> {
    std::env::args_os()
        .map(|value| value.to_string_lossy().into_owned())
        .collect()
}

pub fn ambitus_current_dir() -> std::result::Result<String, crate::std::ambitus::VarError> {
    std::env::current_dir()
        .map(|path| path.to_string_lossy().into_owned())
        .map_err(ambitus_error)
}

pub fn ambitus_set_current_dir(
    path: &str,
) -> std::result::Result<(), crate::std::ambitus::VarError> {
    std::env::set_current_dir(path).map_err(ambitus_error)
}

pub fn ambitus_temp_dir() -> String {
    std::env::temp_dir().to_string_lossy().into_owned()
}

pub fn ambitus_home_dir() -> Option<String> {
    std::env::var_os("HOME")
        .or_else(|| std::env::var_os("USERPROFILE"))
        .map(|value| value.to_string_lossy().into_owned())
}

pub fn ambitus_current_exe() -> std::result::Result<String, crate::std::ambitus::VarError> {
    std::env::current_exe()
        .map(|path| path.to_string_lossy().into_owned())
        .map_err(ambitus_error)
}

pub fn ambitus_join_paths(
    parts: Vec<String>,
) -> std::result::Result<String, crate::std::ambitus::VarError> {
    std::env::join_paths(parts)
        .map(|paths| paths.to_string_lossy().into_owned())
        .map_err(ambitus_error)
}

pub fn ambitus_split_paths(paths: &str) -> Vec<String> {
    std::env::split_paths(paths)
        .map(|path| path.to_string_lossy().into_owned())
        .collect()
}

pub fn ambitus_os() -> String {
    std::env::consts::OS.to_owned()
}

pub fn ambitus_arch() -> String {
    std::env::consts::ARCH.to_owned()
}

pub fn ambitus_family() -> String {
    std::env::consts::FAMILY.to_owned()
}

pub fn ambitus_exe_suffix() -> String {
    std::env::consts::EXE_SUFFIX.to_owned()
}

pub fn ambitus_dll_prefix() -> String {
    std::env::consts::DLL_PREFIX.to_owned()
}

pub fn ambitus_dll_suffix() -> String {
    std::env::consts::DLL_SUFFIX.to_owned()
}

pub fn ambitus_var_os(key: &str) -> Option<String> {
    std::env::var_os(key).map(|value| value.to_string_lossy().into_owned())
}

fn tempus_system_time() -> std::time::SystemTime {
    std::time::SystemTime::now()
}

pub fn tempus_now_millis() -> i32 {
    tempus_system_time()
        .duration_since(std::time::UNIX_EPOCH)
        .map_or(0, |elapsed| i32::try_from(elapsed.as_millis()).unwrap_or(i32::MAX))
}

pub fn tempus_now_micros() -> i32 {
    tempus_system_time()
        .duration_since(std::time::UNIX_EPOCH)
        .map_or(0, |elapsed| {
            i32::try_from(elapsed.as_micros()).unwrap_or(i32::MAX)
        })
}

static TEMPUS_START: LazyLock<std::time::Instant> = LazyLock::new(std::time::Instant::now);

pub fn tempus_monotonic_micros() -> i32 {
    i32::try_from(TEMPUS_START.elapsed().as_micros()).unwrap_or(i32::MAX)
}

pub fn tempus_sleep_millis(millis: i32) {
    if millis > 0 {
        std::thread::sleep(std::time::Duration::from_millis(millis as u64));
    }
}

pub fn tempus_sleep_nanos(nanos: u64) {
    std::thread::sleep(std::time::Duration::from_nanos(nanos));
}

pub fn nexus_cstring_new(text: &str) -> Option<std::ffi::CString> {
    std::ffi::CString::new(text).ok()
}

pub fn nexus_cstring_from_bytes(bytes: Vec<u8>) -> Option<std::ffi::CString> {
    std::ffi::CString::new(bytes).ok()
}

pub fn nexus_cstring_into_string(value: std::ffi::CString) -> Option<String> {
    value.into_string().ok()
}

pub fn nexus_cstring_as_bytes(value: &std::ffi::CString) -> Vec<u8> {
    value.as_bytes().to_vec()
}

pub fn nexus_cstring_len(value: &std::ffi::CString) -> usize {
    value.as_bytes().len()
}

pub fn nexus_cstring_to_str(value: &std::ffi::CString) -> Option<String> {
    value.to_str().ok().map(str::to_owned)
}

pub fn nexus_cstring_to_string_lossy(value: &std::ffi::CString) -> String {
    value.to_string_lossy().into_owned()
}

pub fn nexus_cstring_clone(value: &std::ffi::CString) -> std::ffi::CString {
    value.clone()
}

pub fn nexus_cstring_as_c_str(value: &std::ffi::CString) -> &std::ffi::CStr {
    value.as_c_str()
}

pub fn nexus_cstr_to_str(value: &std::ffi::CStr) -> Option<String> {
    value.to_str().ok().map(str::to_owned)
}

pub fn nexus_cstr_to_string_lossy(value: &std::ffi::CStr) -> String {
    value.to_string_lossy().into_owned()
}

pub fn nexus_cstr_as_bytes(value: &std::ffi::CStr) -> Vec<u8> {
    value.to_bytes().to_vec()
}

pub fn nexus_cstr_len(value: &std::ffi::CStr) -> usize {
    value.to_bytes().len()
}

pub fn nexus_cstr_equals_str(value: &std::ffi::CStr, text: &str) -> bool {
    value.to_bytes() == text.as_bytes()
}

pub fn nexus_cstr_to_cstring(value: &std::ffi::CStr) -> std::ffi::CString {
    value.to_owned()
}

fn versio_error(message: impl Into<String>) -> crate::std::versio::SemverError {
    crate::std::versio::SemverError {
        message: message.into(),
    }
}

fn versio_identifiers(text: &str) -> Vec<String> {
    if text.is_empty() {
        Vec::new()
    } else {
        text.split('.').map(str::to_owned).collect()
    }
}

fn versio_compare_identifiers(left: &str, right: &str) -> std::cmp::Ordering {
    use std::cmp::Ordering;
    if left.is_empty() && right.is_empty() {
        return Ordering::Equal;
    }
    if left.is_empty() {
        return Ordering::Greater;
    }
    if right.is_empty() {
        return Ordering::Less;
    }
    let left = versio_identifiers(left);
    let right = versio_identifiers(right);
    for (a, b) in left.iter().zip(right.iter()) {
        let ordering = match (a.parse::<u64>(), b.parse::<u64>()) {
            (Ok(x), Ok(y)) => x.cmp(&y),
            (Ok(_), Err(_)) => Ordering::Less,
            (Err(_), Ok(_)) => Ordering::Greater,
            (Err(_), Err(_)) => a.cmp(b),
        };
        if ordering != Ordering::Equal {
            return ordering;
        }
    }
    left.len().cmp(&right.len())
}

pub fn versio_parse(
    text: &str,
) -> std::result::Result<crate::std::versio::Version, crate::std::versio::SemverError> {
    let text = text.trim();
    let (rest, build) = match text.split_once('+') {
        Some((left, build)) => (left, build.to_owned()),
        None => (text, String::new()),
    };
    let (core, pre) = match rest.split_once('-') {
        Some((left, pre)) => (left, pre.to_owned()),
        None => (rest, String::new()),
    };
    if !build.is_empty() && versio_identifiers(&build).iter().any(|id| {
        id.is_empty() || !id.chars().all(|c| c.is_ascii_alphanumeric() || c == '-')
    }) {
        return std::result::Result::Err(versio_error("build inválido"));
    }
    if !pre.is_empty()
        && versio_identifiers(&pre)
            .iter()
            .any(|id| id.is_empty() || !id.chars().all(|c| c.is_ascii_alphanumeric() || c == '-'))
    {
        return std::result::Result::Err(versio_error("pre-release inválido"));
    }
    let parts: Vec<&str> = core.split('.').collect();
    if parts.len() != 3 {
        return std::result::Result::Err(versio_error("se esperaban major.minor.patch"));
    }
    let mut numbers = [0_i32; 3];
    for (index, part) in parts.iter().enumerate() {
        if part.is_empty() || !part.chars().all(|c| c.is_ascii_digit()) {
            return std::result::Result::Err(versio_error("componente no numérico"));
        }
        numbers[index] = part.parse().map_err(|_| versio_error("número fuera de rango"))?;
    }
    std::result::Result::Ok(crate::std::versio::Version {
        major: numbers[0],
        minor: numbers[1],
        patch: numbers[2],
        pre,
        build,
    })
}

pub fn versio_compare(
    left: &crate::std::versio::Version,
    right: &crate::std::versio::Version,
) -> i32 {
    use std::cmp::Ordering;
    let core = (left.major, left.minor, left.patch).cmp(&(right.major, right.minor, right.patch));
    let ordering = if core != Ordering::Equal {
        core
    } else {
        versio_compare_identifiers(&left.pre, &right.pre)
    };
    match ordering {
        Ordering::Less => -1,
        Ordering::Equal => 0,
        Ordering::Greater => 1,
    }
}

pub fn versio_satisfies(
    version: &crate::std::versio::Version,
    requirement: &str,
) -> std::result::Result<bool, crate::std::versio::SemverError> {
    // Unión: `^1.2 || ^2.0` — basta con que una alternativa se cumpla.
    for alternative in requirement.split("||") {
        if versio_satisfies_all(version, alternative.trim())? {
            return std::result::Result::Ok(true);
        }
    }
    std::result::Result::Ok(false)
}

/// Conjunción: `>=1.0.0 <2.0.0`. Cada comparador debe cumplirse.
fn versio_satisfies_all(
    version: &crate::std::versio::Version,
    requirement: &str,
) -> std::result::Result<bool, crate::std::versio::SemverError> {
    let requirement = requirement.trim();
    if requirement.is_empty() {
        return std::result::Result::Ok(true);
    }
    let mut comparators: Vec<String> = Vec::new();
    let mut pending: Option<String> = None;
    for token in requirement.split_whitespace() {
        if let Some(operator) = pending.take() {
            comparators.push(format!("{operator}{token}"));
        } else if matches!(token, ">=" | "<=" | ">" | "<" | "=" | "^" | "~") {
            pending = Some(token.to_owned());
        } else {
            comparators.push(token.to_owned());
        }
    }
    if let Some(operator) = pending {
        comparators.push(operator);
    }
    for comparator in comparators {
        if !versio_satisfies_one(version, &comparator)? {
            return std::result::Result::Ok(false);
        }
    }
    std::result::Result::Ok(true)
}

fn versio_satisfies_one(
    version: &crate::std::versio::Version,
    requirement: &str,
) -> std::result::Result<bool, crate::std::versio::SemverError> {
    let requirement = requirement.trim();
    let (operator, rest) = if let Some(rest) = requirement.strip_prefix(">=") {
        (">=", rest)
    } else if let Some(rest) = requirement.strip_prefix("<=") {
        ("<=", rest)
    } else if let Some(rest) = requirement.strip_prefix('>') {
        (">", rest)
    } else if let Some(rest) = requirement.strip_prefix('<') {
        ("<", rest)
    } else if let Some(rest) = requirement.strip_prefix('^') {
        ("^", rest)
    } else if let Some(rest) = requirement.strip_prefix('~') {
        ("~", rest)
    } else if let Some(rest) = requirement.strip_prefix('=') {
        ("=", rest)
    } else {
        ("=", requirement)
    };
    let rest = rest.trim();
    if rest == "*" || rest == "x" || rest == "X" {
        return std::result::Result::Ok(true);
    }
    // Comodines parciales: `1.x`, `1.2.x`, `1.2.*`.
    let mut prefix: Vec<i32> = Vec::new();
    let mut wildcard = false;
    for part in rest.split('.') {
        let part = part.trim();
        if part == "x" || part == "X" || part == "*" {
            wildcard = true;
            break;
        }
        match part.parse::<i32>() {
            std::result::Result::Ok(value) => prefix.push(value),
            std::result::Result::Err(_) => {
                wildcard = false;
                prefix.clear();
                break;
            }
        }
    }
    if wildcard || (operator == "=" && prefix.len() < 3 && !prefix.is_empty()) {
        let matched = match prefix.as_slice() {
            [] => true,
            [major] => version.major == *major,
            [major, minor] => version.major == *major && version.minor == *minor,
            _ => false,
        };
        return std::result::Result::Ok(matched);
    }
    // Versión incompleta con operador (`^1.2`, `>=1.0`): se rellena con ceros.
    let padded;
    let rest = if prefix.len() < 3 && !prefix.is_empty() {
        padded = format!(
            "{}.{}.{}",
            prefix.first().copied().unwrap_or(0),
            prefix.get(1).copied().unwrap_or(0),
            prefix.get(2).copied().unwrap_or(0)
        );
        padded.as_str()
    } else {
        rest
    };
    let target = versio_parse(rest)?;
    let ordering = versio_compare(version, &target);
    let satisfied = match operator {
        ">=" => ordering >= 0,
        "<=" => ordering <= 0,
        ">" => ordering > 0,
        "<" => ordering < 0,
        "=" => ordering == 0,
        "^" => {
            if target.major > 0 {
                version.major == target.major && ordering >= 0
            } else if target.minor > 0 {
                version.major == 0 && version.minor == target.minor && ordering >= 0
            } else {
                ordering == 0
            }
        }
        "~" => version.major == target.major && version.minor == target.minor && ordering >= 0,
        _ => false,
    };
    std::result::Result::Ok(satisfied)
}

const DIGEST_SHA256_K: [u32; 64] = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
];

fn digest_pad(data: &[u8], big_endian_length: bool) -> (Vec<u8>, usize) {
    let bit_len = (data.len() as u64).wrapping_mul(8);
    let mut padded = data.to_vec();
    padded.push(0x80);
    while padded.len() % 64 != 56 {
        padded.push(0);
    }
    if big_endian_length {
        padded.extend_from_slice(&bit_len.to_be_bytes());
    } else {
        padded.extend_from_slice(&bit_len.to_le_bytes());
    }
    (padded, data.len())
}

pub fn digest_sha256(data: Vec<u8>) -> Vec<u8> {
    let (padded, _) = digest_pad(&data, true);
    let mut h: [u32; 8] = [
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
    ];
    let mut w = [0u32; 64];
    for chunk in padded.chunks_exact(64) {
        for (i, word) in chunk.chunks_exact(4).enumerate() {
            w[i] = u32::from_be_bytes([word[0], word[1], word[2], word[3]]);
        }
        for i in 16..64 {
            let s0 = w[i - 15].rotate_right(7) ^ w[i - 15].rotate_right(18) ^ (w[i - 15] >> 3);
            let s1 = w[i - 2].rotate_right(17) ^ w[i - 2].rotate_right(19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16]
                .wrapping_add(s0)
                .wrapping_add(w[i - 7])
                .wrapping_add(s1);
        }
        let (mut a, mut b, mut c, mut d, mut e, mut f, mut g, mut hh) =
            (h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7]);
        for i in 0..64 {
            let s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let ch = (e & f) ^ ((!e) & g);
            let temp1 = hh
                .wrapping_add(s1)
                .wrapping_add(ch)
                .wrapping_add(DIGEST_SHA256_K[i])
                .wrapping_add(w[i]);
            let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let maj = (a & b) ^ (a & c) ^ (b & c);
            let temp2 = s0.wrapping_add(maj);
            hh = g;
            g = f;
            f = e;
            e = d.wrapping_add(temp1);
            d = c;
            c = b;
            b = a;
            a = temp1.wrapping_add(temp2);
        }
        h[0] = h[0].wrapping_add(a);
        h[1] = h[1].wrapping_add(b);
        h[2] = h[2].wrapping_add(c);
        h[3] = h[3].wrapping_add(d);
        h[4] = h[4].wrapping_add(e);
        h[5] = h[5].wrapping_add(f);
        h[6] = h[6].wrapping_add(g);
        h[7] = h[7].wrapping_add(hh);
    }
    let mut out = Vec::with_capacity(32);
    for word in h {
        out.extend_from_slice(&word.to_be_bytes());
    }
    out
}

pub fn digest_sha1(data: Vec<u8>) -> Vec<u8> {
    let (padded, _) = digest_pad(&data, true);
    let mut h: [u32; 5] = [0x67452301, 0xefcdab89, 0x98badcfe, 0x10325476, 0xc3d2e1f0];
    let mut w = [0u32; 80];
    for chunk in padded.chunks_exact(64) {
        for (i, word) in chunk.chunks_exact(4).enumerate() {
            w[i] = u32::from_be_bytes([word[0], word[1], word[2], word[3]]);
        }
        for i in 16..80 {
            w[i] = (w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16]).rotate_left(1);
        }
        let (mut a, mut b, mut c, mut d, mut e) = (h[0], h[1], h[2], h[3], h[4]);
        for (i, word) in w.iter().enumerate() {
            let (f, k) = match i {
                0..=19 => ((b & c) | ((!b) & d), 0x5a827999),
                20..=39 => (b ^ c ^ d, 0x6ed9eba1),
                40..=59 => ((b & c) | (b & d) | (c & d), 0x8f1bbcdc),
                _ => (b ^ c ^ d, 0xca62c1d6),
            };
            let temp = a
                .rotate_left(5)
                .wrapping_add(f)
                .wrapping_add(e)
                .wrapping_add(k)
                .wrapping_add(*word);
            e = d;
            d = c;
            c = b.rotate_left(30);
            b = a;
            a = temp;
        }
        h[0] = h[0].wrapping_add(a);
        h[1] = h[1].wrapping_add(b);
        h[2] = h[2].wrapping_add(c);
        h[3] = h[3].wrapping_add(d);
        h[4] = h[4].wrapping_add(e);
    }
    let mut out = Vec::with_capacity(20);
    for word in h {
        out.extend_from_slice(&word.to_be_bytes());
    }
    out
}

pub fn digest_crc32(data: Vec<u8>) -> u32 {
    let mut crc = 0xffff_ffffu32;
    for byte in data {
        crc ^= u32::from(byte);
        for _ in 0..8 {
            let mask = (crc & 1).wrapping_neg();
            crc = (crc >> 1) ^ (0xedb8_8320 & mask);
        }
    }
    !crc
}

pub fn digest_fnv1a(data: Vec<u8>) -> u64 {
    let mut hash = 0xcbf2_9ce4_8422_2325u64;
    for byte in data {
        hash ^= u64::from(byte);
        hash = hash.wrapping_mul(0x0000_0100_0000_01b3);
    }
    hash
}


const DIGEST_SHA512_K: [u64; 80] = [
    0x428a2f98d728ae22, 0x7137449123ef65cd, 0xb5c0fbcfec4d3b2f, 0xe9b5dba58189dbbc,
    0x3956c25bf348b538, 0x59f111f1b605d019, 0x923f82a4af194f9b, 0xab1c5ed5da6d8118,
    0xd807aa98a3030242, 0x12835b0145706fbe, 0x243185be4ee4b28c, 0x550c7dc3d5ffb4e2,
    0x72be5d74f27b896f, 0x80deb1fe3b1696b1, 0x9bdc06a725c71235, 0xc19bf174cf692694,
    0xe49b69c19ef14ad2, 0xefbe4786384f25e3, 0x0fc19dc68b8cd5b5, 0x240ca1cc77ac9c65,
    0x2de92c6f592b0275, 0x4a7484aa6ea6e483, 0x5cb0a9dcbd41fbd4, 0x76f988da831153b5,
    0x983e5152ee66dfab, 0xa831c66d2db43210, 0xb00327c898fb213f, 0xbf597fc7beef0ee4,
    0xc6e00bf33da88fc2, 0xd5a79147930aa725, 0x06ca6351e003826f, 0x142929670a0e6e70,
    0x27b70a8546d22ffc, 0x2e1b21385c26c926, 0x4d2c6dfc5ac42aed, 0x53380d139d95b3df,
    0x650a73548baf63de, 0x766a0abb3c77b2a8, 0x81c2c92e47edaee6, 0x92722c851482353b,
    0xa2bfe8a14cf10364, 0xa81a664bbc423001, 0xc24b8b70d0f89791, 0xc76c51a30654be30,
    0xd192e819d6ef5218, 0xd69906245565a910, 0xf40e35855771202a, 0x106aa07032bbd1b8,
    0x19a4c116b8d2d0c8, 0x1e376c085141ab53, 0x2748774cdf8eeb99, 0x34b0bcb5e19b48a8,
    0x391c0cb3c5c95a63, 0x4ed8aa4ae3418acb, 0x5b9cca4f7763e373, 0x682e6ff3d6b2b8a3,
    0x748f82ee5defb2fc, 0x78a5636f43172f60, 0x84c87814a1f0ab72, 0x8cc702081a6439ec,
    0x90befffa23631e28, 0xa4506cebde82bde9, 0xbef9a3f7b2c67915, 0xc67178f2e372532b,
    0xca273eceea26619c, 0xd186b8c721c0c207, 0xeada7dd6cde0eb1e, 0xf57d4f7fee6ed178,
    0x06f067aa72176fba, 0x0a637dc5a2c898a6, 0x113f9804bef90dae, 0x1b710b35131c471b,
    0x28db77f523047d84, 0x32caab7b40c72493, 0x3c9ebe0a15c9bebc, 0x431d67c49c100d4c,
    0x4cc5d4becb3e42b6, 0x597f299cfc657e2a, 0x5fcb6fab3ad6faec, 0x6c44198c4a475817,
];

/// Relleno de SHA-512: bloques de 128 bytes y longitud de 128 bits.
fn digest_pad_512(data: &[u8]) -> Vec<u8> {
    let bit_len = (data.len() as u128).wrapping_mul(8);
    let mut padded = data.to_vec();
    padded.push(0x80);
    while padded.len() % 128 != 112 {
        padded.push(0);
    }
    padded.extend_from_slice(&bit_len.to_be_bytes());
    padded
}

pub fn digest_sha512(data: Vec<u8>) -> Vec<u8> {
    let padded = digest_pad_512(&data);
    let mut h: [u64; 8] = [
        0x6a09e667f3bcc908, 0xbb67ae8584caa73b, 0x3c6ef372fe94f82b, 0xa54ff53a5f1d36f1,
        0x510e527fade682d1, 0x9b05688c2b3e6c1f, 0x1f83d9abfb41bd6b, 0x5be0cd19137e2179,
    ];
    let mut w = [0u64; 80];
    for chunk in padded.chunks_exact(128) {
        for (i, word) in chunk.chunks_exact(8).enumerate() {
            w[i] = u64::from_be_bytes([word[0], word[1], word[2], word[3], word[4], word[5], word[6], word[7]]);
        }
        for i in 16..80 {
            let s0 = w[i - 15].rotate_right(1) ^ w[i - 15].rotate_right(8) ^ (w[i - 15] >> 7);
            let s1 = w[i - 2].rotate_right(19) ^ w[i - 2].rotate_right(61) ^ (w[i - 2] >> 6);
            w[i] = w[i - 16]
                .wrapping_add(s0)
                .wrapping_add(w[i - 7])
                .wrapping_add(s1);
        }
        let (mut a, mut b, mut c, mut d, mut e, mut f, mut g, mut hh) =
            (h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7]);
        for i in 0..80 {
            let s1 = e.rotate_right(14) ^ e.rotate_right(18) ^ e.rotate_right(41);
            let ch = (e & f) ^ ((!e) & g);
            let temp1 = hh
                .wrapping_add(s1)
                .wrapping_add(ch)
                .wrapping_add(DIGEST_SHA512_K[i])
                .wrapping_add(w[i]);
            let s0 = a.rotate_right(28) ^ a.rotate_right(34) ^ a.rotate_right(39);
            let maj = (a & b) ^ (a & c) ^ (b & c);
            let temp2 = s0.wrapping_add(maj);
            hh = g;
            g = f;
            f = e;
            e = d.wrapping_add(temp1);
            d = c;
            c = b;
            b = a;
            a = temp1.wrapping_add(temp2);
        }
        h[0] = h[0].wrapping_add(a);
        h[1] = h[1].wrapping_add(b);
        h[2] = h[2].wrapping_add(c);
        h[3] = h[3].wrapping_add(d);
        h[4] = h[4].wrapping_add(e);
        h[5] = h[5].wrapping_add(f);
        h[6] = h[6].wrapping_add(g);
        h[7] = h[7].wrapping_add(hh);
    }
    let mut out = Vec::with_capacity(64);
    for word in h {
        out.extend_from_slice(&word.to_be_bytes());
    }
    out
}

pub fn digest_sha512_hex(data: Vec<u8>) -> String {
    digest_hex(digest_sha512(data))
}

/// HMAC-SHA-256 (RFC 2104).
pub fn digest_hmac_sha256(key: Vec<u8>, data: Vec<u8>) -> Vec<u8> {
    let mut block = [0u8; 64];
    if key.len() > 64 {
        let hashed = digest_sha256(key);
        block[..hashed.len()].copy_from_slice(&hashed);
    } else {
        block[..key.len()].copy_from_slice(&key);
    }
    let mut inner = Vec::with_capacity(64 + data.len());
    inner.extend(block.iter().map(|byte| byte ^ 0x36));
    inner.extend_from_slice(&data);
    let inner_hash = digest_sha256(inner);
    let mut outer = Vec::with_capacity(64 + inner_hash.len());
    outer.extend(block.iter().map(|byte| byte ^ 0x5c));
    outer.extend_from_slice(&inner_hash);
    digest_sha256(outer)
}

pub fn digest_constant_time_eq(left: Vec<u8>, right: Vec<u8>) -> bool {
    if left.len() != right.len() {
        return false;
    }
    let mut diff = 0u8;
    for (a, b) in left.iter().zip(right.iter()) {
        diff |= a ^ b;
    }
    diff == 0
}

pub fn digest_hex(data: Vec<u8>) -> String {
    let mut out = String::with_capacity(data.len() * 2);
    for byte in data {
        out.push_str(&format!("{byte:02x}"));
    }
    out
}

pub fn digest_unhex(text: &str) -> Option<Vec<u8>> {
    let text = text.trim();
    if text.len() % 2 != 0 {
        return None;
    }
    let mut out = Vec::with_capacity(text.len() / 2);
    let bytes = text.as_bytes();
    let mut i = 0;
    while i < bytes.len() {
        let hi = (bytes[i] as char).to_digit(16)?;
        let lo = (bytes[i + 1] as char).to_digit(16)?;
        #[allow(clippy::cast_possible_truncation)]
        out.push((hi * 16 + lo) as u8);
        i += 2;
    }
    Some(out)
}

pub fn digest_sha256_hex(data: Vec<u8>) -> String {
    digest_hex(digest_sha256(data))
}

pub fn digest_sha1_hex(data: Vec<u8>) -> String {
    digest_hex(digest_sha1(data))
}

// ---------------------------------------------------------------------------
// iason: JSON. El árbol vive en `crate::std::iason::Json`.
// ---------------------------------------------------------------------------

fn iason_node(kind: &str) -> crate::std::iason::Json {
    crate::std::iason::Json {
        kind: kind.to_owned(),
        flag: false,
        integer: 0,
        number: 0.0,
        text: String::new(),
        items: Vec::new(),
        keys: Vec::new(),
    }
}

fn iason_error(message: &str, offset: usize) -> crate::std::iason::IasonError {
    crate::std::iason::IasonError {
        message: message.to_owned(),
        offset,
    }
}

struct IasonParser<'a> {
    bytes: &'a [u8],
    pos: usize,
}

impl IasonParser<'_> {
    fn peek(&self) -> Option<u8> {
        self.bytes.get(self.pos).copied()
    }

    fn skip_ws(&mut self) {
        while let Some(byte) = self.peek() {
            if byte == b' ' || byte == b'\t' || byte == b'\n' || byte == b'\r' {
                self.pos += 1;
            } else {
                break;
            }
        }
    }

    fn expect(&mut self, byte: u8) -> Result<(), crate::std::iason::IasonError> {
        if self.peek() == Some(byte) {
            self.pos += 1;
            Ok(())
        } else {
            Err(iason_error(
                &format!("se esperaba `{}`", byte as char),
                self.pos,
            ))
        }
    }

    fn value(&mut self, depth: usize) -> Result<crate::std::iason::Json, crate::std::iason::IasonError> {
        if depth > 128 {
            return Err(iason_error("anidamiento excesivo", self.pos));
        }
        self.skip_ws();
        match self.peek() {
            None => Err(iason_error("fin de entrada inesperado", self.pos)),
            Some(b'{') => self.object(depth),
            Some(b'[') => self.array(depth),
            Some(b'"') => {
                let mut node = iason_node("string");
                node.text = self.string()?;
                Ok(node)
            }
            Some(b't') => {
                self.literal("true")?;
                let mut node = iason_node("bool");
                node.flag = true;
                Ok(node)
            }
            Some(b'f') => {
                self.literal("false")?;
                Ok(iason_node("bool"))
            }
            Some(b'n') => {
                self.literal("null")?;
                Ok(iason_node("null"))
            }
            Some(byte) if byte == b'-' || byte.is_ascii_digit() => self.number(),
            Some(byte) => Err(iason_error(
                &format!("carácter inesperado `{}`", byte as char),
                self.pos,
            )),
        }
    }

    fn literal(&mut self, word: &str) -> Result<(), crate::std::iason::IasonError> {
        if self.bytes[self.pos..].starts_with(word.as_bytes()) {
            self.pos += word.len();
            Ok(())
        } else {
            Err(iason_error(&format!("se esperaba `{word}`"), self.pos))
        }
    }

    fn number(&mut self) -> Result<crate::std::iason::Json, crate::std::iason::IasonError> {
        let start = self.pos;
        if self.peek() == Some(b'-') {
            self.pos += 1;
        }
        while matches!(self.peek(), Some(byte) if byte.is_ascii_digit()) {
            self.pos += 1;
        }
        let mut is_float = false;
        if self.peek() == Some(b'.') {
            is_float = true;
            self.pos += 1;
            while matches!(self.peek(), Some(byte) if byte.is_ascii_digit()) {
                self.pos += 1;
            }
        }
        if matches!(self.peek(), Some(b'e' | b'E')) {
            is_float = true;
            self.pos += 1;
            if matches!(self.peek(), Some(b'+' | b'-')) {
                self.pos += 1;
            }
            while matches!(self.peek(), Some(byte) if byte.is_ascii_digit()) {
                self.pos += 1;
            }
        }
        let raw = std::str::from_utf8(&self.bytes[start..self.pos])
            .map_err(|_| iason_error("número inválido", start))?;
        if is_float {
            let value: f64 = raw.parse().map_err(|_| iason_error("número inválido", start))?;
            let mut node = iason_node("float");
            node.number = value;
            Ok(node)
        } else {
            let value: i64 = raw.parse().map_err(|_| iason_error("entero fuera de rango", start))?;
            #[allow(clippy::cast_possible_truncation)]
            let value = value as i32;
            let mut node = iason_node("int");
            node.integer = value;
            Ok(node)
        }
    }

    fn string(&mut self) -> Result<String, crate::std::iason::IasonError> {
        self.expect(b'"')?;
        let mut out = String::new();
        loop {
            match self.peek() {
                None => return Err(iason_error("cadena sin cerrar", self.pos)),
                Some(b'"') => {
                    self.pos += 1;
                    return Ok(out);
                }
                Some(b'\\') => {
                    self.pos += 1;
                    let escape = self.peek().ok_or_else(|| iason_error("escape incompleto", self.pos))?;
                    self.pos += 1;
                    match escape {
                        b'"' => out.push('"'),
                        b'\\' => out.push('\\'),
                        b'/' => out.push('/'),
                        b'b' => out.push('\u{0008}'),
                        b'f' => out.push('\u{000c}'),
                        b'n' => out.push('\n'),
                        b'r' => out.push('\r'),
                        b't' => out.push('\t'),
                        b'u' => {
                            let code = self.hex4()?;
                            if (0xd800..0xdc00).contains(&code) {
                                if self.peek() == Some(b'\\') {
                                    self.pos += 1;
                                    if self.peek() == Some(b'u') {
                                        self.pos += 1;
                                        let low = self.hex4()?;
                                        let combined =
                                            0x1_0000 + ((code - 0xd800) << 10) + (low.wrapping_sub(0xdc00));
                                        if let Some(ch) = char::from_u32(combined) {
                                            out.push(ch);
                                        }
                                    }
                                }
                            } else if let Some(ch) = char::from_u32(code) {
                                out.push(ch);
                            }
                        }
                        other => {
                            return Err(iason_error(
                                &format!("escape inválido `\\{}`", other as char),
                                self.pos,
                            ));
                        }
                    }
                }
                Some(byte) => {
                    let start = self.pos;
                    while matches!(self.peek(), Some(b) if b != b'"' && b != b'\\') {
                        self.pos += 1;
                    }
                    out.push_str(
                        std::str::from_utf8(&self.bytes[start..self.pos])
                            .map_err(|_| iason_error("UTF-8 inválido", start))?,
                    );
                }
            }
        }
    }

    fn hex4(&mut self) -> Result<u32, crate::std::iason::IasonError> {
        if self.pos + 4 > self.bytes.len() {
            return Err(iason_error("escape \\u incompleto", self.pos));
        }
        let text = std::str::from_utf8(&self.bytes[self.pos..self.pos + 4])
            .map_err(|_| iason_error("escape \\u inválido", self.pos))?;
        let value = u32::from_str_radix(text, 16).map_err(|_| iason_error("escape \\u inválido", self.pos))?;
        self.pos += 4;
        Ok(value)
    }

    fn array(&mut self, depth: usize) -> Result<crate::std::iason::Json, crate::std::iason::IasonError> {
        self.expect(b'[')?;
        let mut node = iason_node("array");
        self.skip_ws();
        if self.peek() == Some(b']') {
            self.pos += 1;
            return Ok(node);
        }
        loop {
            node.items.push(self.value(depth + 1)?);
            self.skip_ws();
            match self.peek() {
                Some(b',') => {
                    self.pos += 1;
                }
                Some(b']') => {
                    self.pos += 1;
                    return Ok(node);
                }
                _ => return Err(iason_error("se esperaba `,` o `]`", self.pos)),
            }
        }
    }

    fn object(&mut self, depth: usize) -> Result<crate::std::iason::Json, crate::std::iason::IasonError> {
        self.expect(b'{')?;
        let mut node = iason_node("object");
        self.skip_ws();
        if self.peek() == Some(b'}') {
            self.pos += 1;
            return Ok(node);
        }
        loop {
            self.skip_ws();
            let key = self.string()?;
            self.skip_ws();
            self.expect(b':')?;
            let value = self.value(depth + 1)?;
            node.keys.push(key);
            node.items.push(value);
            self.skip_ws();
            match self.peek() {
                Some(b',') => {
                    self.pos += 1;
                }
                Some(b'}') => {
                    self.pos += 1;
                    return Ok(node);
                }
                _ => return Err(iason_error("se esperaba `,` o `}`", self.pos)),
            }
        }
    }
}

pub fn iason_parse(
    text: &str,
) -> std::result::Result<crate::std::iason::Json, crate::std::iason::IasonError> {
    let mut parser = IasonParser {
        bytes: text.as_bytes(),
        pos: 0,
    };
    let value = parser.value(0)?;
    parser.skip_ws();
    if parser.pos != parser.bytes.len() {
        return std::result::Result::Err(iason_error("contenido sobrante", parser.pos));
    }
    std::result::Result::Ok(value)
}

fn iason_escape(text: &str) -> String {
    let mut out = String::with_capacity(text.len() + 2);
    out.push('"');
    for ch in text.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{0008}' => out.push_str("\\b"),
            '\u{000c}' => out.push_str("\\f"),
            other if (other as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", other as u32)),
            other => out.push(other),
        }
    }
    out.push('"');
    out
}

fn iason_write(value: &crate::std::iason::Json, out: &mut String, indent: Option<usize>, depth: usize) {
    match value.kind.as_str() {
        "bool" => out.push_str(if value.flag { "true" } else { "false" }),
        "int" => out.push_str(&value.integer.to_string()),
        "float" => {
            let text = format!("{}", value.number);
            out.push_str(&text);
        }
        "string" => out.push_str(&iason_escape(&value.text)),
        "array" => {
            if value.items.is_empty() {
                out.push_str("[]");
                return;
            }
            out.push('[');
            for (index, item) in value.items.iter().enumerate() {
                if index > 0 {
                    out.push(',');
                }
                if let Some(step) = indent {
                    out.push('\n');
                    out.push_str(&" ".repeat(step * (depth + 1)));
                }
                iason_write(item, out, indent, depth + 1);
            }
            if let Some(step) = indent {
                out.push('\n');
                out.push_str(&" ".repeat(step * depth));
            }
            out.push(']');
        }
        "object" => {
            if value.keys.is_empty() {
                out.push_str("{}");
                return;
            }
            out.push('{');
            for (index, key) in value.keys.iter().enumerate() {
                if index > 0 {
                    out.push(',');
                }
                if let Some(step) = indent {
                    out.push('\n');
                    out.push_str(&" ".repeat(step * (depth + 1)));
                }
                out.push_str(&iason_escape(key));
                out.push(':');
                if indent.is_some() {
                    out.push(' ');
                }
                if let Some(item) = value.items.get(index) {
                    iason_write(item, out, indent, depth + 1);
                }
            }
            if let Some(step) = indent {
                out.push('\n');
                out.push_str(&" ".repeat(step * depth));
            }
            out.push('}');
        }
        _ => out.push_str("null"),
    }
}


/// Igualdad estructural de dos nodos JSON. Los objetos se comparan por clave
/// (el orden de las claves no importa); `int` y `float` son tipos distintos.
pub fn iason_equals(left: &crate::std::iason::Json, right: &crate::std::iason::Json) -> bool {
    if left.kind.as_str() != right.kind.as_str() {
        return false;
    }
    match left.kind.as_str() {
        "null" => true,
        "bool" => left.flag == right.flag,
        "int" => left.integer == right.integer,
        "float" => left.number == right.number,
        "string" => left.text == right.text,
        "array" => {
            left.items.len() == right.items.len()
                && left
                    .items
                    .iter()
                    .zip(right.items.iter())
                    .all(|(a, b)| iason_equals(a, b))
        }
        "object" => {
            if left.keys.len() != right.keys.len() {
                return false;
            }
            left.keys
                .iter()
                .zip(left.items.iter())
                .all(|(key, value)| match right.keys.iter().position(|other| other == key) {
                    Some(index) => iason_equals(value, &right.items[index]),
                    None => false,
                })
        }
        _ => false,
    }
}

pub fn iason_push(value: &mut crate::std::iason::Json, item: &crate::std::iason::Json) {
    if value.kind.as_str() == "array" {
        value.items.push(item.clone());
    }
}

pub fn iason_insert(
    value: &mut crate::std::iason::Json,
    key: String,
    item: &crate::std::iason::Json,
) {
    if value.kind.as_str() != "object" {
        return;
    }
    value.keys.push(key);
    value.items.push(item.clone());
}

pub fn iason_set(
    value: &mut crate::std::iason::Json,
    key: String,
    item: &crate::std::iason::Json,
) {
    if value.kind.as_str() != "object" {
        return;
    }
    match value.keys.iter().position(|other| *other == key) {
        Some(index) => value.items[index] = item.clone(),
        None => {
            value.keys.push(key);
            value.items.push(item.clone());
        }
    }
}

pub fn iason_remove(value: &mut crate::std::iason::Json, key: &str) -> bool {
    if value.kind.as_str() != "object" {
        return false;
    }
    match value.keys.iter().position(|other| other == key) {
        Some(index) => {
            value.keys.remove(index);
            value.items.remove(index);
            true
        }
        None => false,
    }
}

pub fn iason_stringify(value: &crate::std::iason::Json) -> String {
    let mut out = String::new();
    iason_write(value, &mut out, None, 0);
    out
}

pub fn iason_pretty(value: &crate::std::iason::Json, indent: i32) -> String {
    #[allow(clippy::cast_sign_loss)]
    let step = if indent <= 0 { 2 } else { indent as usize };
    let mut out = String::new();
    iason_write(value, &mut out, Some(step), 0);
    out
}

// ---------------------------------------------------------------------------
// terminus: detectar terminal y ancho.
// ---------------------------------------------------------------------------

pub fn terminus_is_terminal() -> bool {
    std::io::IsTerminal::is_terminal(&std::io::stdout())
}

pub fn terminus_width() -> usize {
    std::env::var("COLUMNS")
        .ok()
        .and_then(|value| value.trim().parse().ok())
        .filter(|width: &usize| *width > 0)
        .unwrap_or(80)
}

pub fn terminus_supports_color() -> bool {
    if std::env::var_os("NO_COLOR").is_some() {
        return false;
    }
    match std::env::var("TERM") {
        Ok(term) => term != "dumb" && terminus_is_terminal(),
        Err(_) => false,
    }
}

pub fn terminus_rgb(text: &str, r: u8, g: u8, b: u8) -> String {
    format!("\u{1b}[38;2;{r};{g};{b}m{text}\u{1b}[0m")
}

pub fn terminus_clear_screen() {
    print!("\u{1b}[2J\u{1b}[H");
}

pub fn terminus_move_cursor(row: usize, column: usize) {
    print!("\u{1b}[{row};{column}H");
}

pub fn terminus_hide_cursor() {
    print!("\u{1b}[?25l");
}

pub fn terminus_show_cursor() {
    print!("\u{1b}[?25h");
}

pub fn terminus_cursor_up(lines: usize) {
    print!("\u{1b}[{lines}A");
}

pub fn terminus_cursor_down(lines: usize) {
    print!("\u{1b}[{lines}B");
}

pub fn terminus_cursor_left(columns: usize) {
    print!("\u{1b}[{columns}D");
}

pub fn terminus_cursor_right(columns: usize) {
    print!("\u{1b}[{columns}C");
}

/// Barra de progreso de `width` celdas: `[####----]  42%`.
pub fn terminus_progress_bar(done: usize, total: usize, width: usize) -> String {
    let width = width.max(3);
    let total = total.max(1);
    let ratio = (done.min(total) as f64) / (total as f64);
    #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
    let filled = ((ratio * (width as f64)) as usize).min(width);
    let percent = (ratio * 100.0).round();
    let mut out = String::from("[");
    out.push_str(&"#".repeat(filled));
    out.push_str(&"-".repeat(width - filled));
    out.push(']');
    out.push_str(&format!(" {percent:>3.0}%"));
    out
}

/// Lee una tecla de la entrada estándar. Sin modo crudo el terminal entrega la
/// línea completa, así que devuelve el primer carácter de lo que se escriba.
pub fn terminus_read_key() -> Option<char> {
    use std::io::Read;
    let mut byte = [0u8; 1];
    match std::io::stdin().read(&mut byte) {
        Ok(1) => Some(byte[0] as char),
        _ => None,
    }
}

/// Glob con profundidad y opciones de recorrido.
pub fn globus_find_with(
    pattern: &str,
    root: &str,
    max_depth: i32,
    include_hidden: bool,
    follow_links: bool,
) -> Vec<String> {
    let limit = if max_depth < 0 {
        usize::MAX
    } else {
        #[allow(clippy::cast_sign_loss, clippy::cast_possible_truncation)]
        let value = max_depth as usize;
        value
    };
    let mut out = Vec::new();
    let mut stack = vec![(std::path::PathBuf::from(root), 0usize)];
    while let Some((directory, depth)) = stack.pop() {
        if depth > limit {
            continue;
        }
        let Ok(entries) = std::fs::read_dir(&directory) else {
            continue;
        };
        let mut names: Vec<_> = entries.flatten().map(|entry| entry.path()).collect();
        names.sort();
        for path in names {
            let relative = path.strip_prefix(root).unwrap_or(&path);
            let text = relative.to_string_lossy().replace('\\', "/");
            if !include_hidden && text.split('/').any(|part| part.starts_with('.')) {
                continue;
            }
            if globus_matches(pattern, &text) {
                out.push(text);
            }
            let is_directory = path.is_dir() || (follow_links && path.is_symlink());
            if is_directory && depth < limit {
                stack.push((path, depth + 1));
            }
        }
    }
    out.sort();
    out
}

// ---------------------------------------------------------------------------
// globus: patrones glob.
// ---------------------------------------------------------------------------

fn globus_match_here(pattern: &[u8], text: &[u8]) -> bool {
    let mut p = 0;
    let mut t = 0;
    let mut star: Option<(usize, usize)> = None;
    while t < text.len() {
        if p < pattern.len() {
            match pattern[p] {
                b'?' => {
                    if text[t] != b'/' {
                        p += 1;
                        t += 1;
                        continue;
                    }
                }
                b'*' => {
                    let mut next = p + 1;
                    let mut crosses = false;
                    if next < pattern.len() && pattern[next] == b'*' {
                        crosses = true;
                        next += 1;
                        if next < pattern.len() && pattern[next] == b'/' {
                            next += 1;
                        }
                    }
                    if crosses {
                        // `**` prueba todas las posiciones restantes.
                        for skip in t..=text.len() {
                            if globus_match_here(&pattern[next..], &text[skip..]) {
                                return true;
                            }
                        }
                        return false;
                    }
                    star = Some((next, t));
                    p = next;
                    continue;
                }
                b'[' => {
                    if let Some((matched, after)) = globus_match_class(&pattern[p..], text[t]) {
                        if matched {
                            p += after;
                            t += 1;
                            continue;
                        }
                    }
                }
                b'{' => {
                    if let Some((matched, after)) = globus_match_alt(&pattern[p..], &text[t..]) {
                        if matched {
                            return true;
                        }
                        let _ = after;
                    }
                }
                literal => {
                    if literal == text[t] {
                        p += 1;
                        t += 1;
                        continue;
                    }
                }
            }
        }
        if let Some((star_p, star_t)) = star {
            // Un `*` simple no cruza el separador de directorios.
            if text[star_t] == b'/' {
                return false;
            }
            p = star_p;
            t = star_t + 1;
            star = Some((star_p, star_t + 1));
        } else {
            return false;
        }
    }
    while p < pattern.len() && pattern[p] == b'*' {
        p += 1;
    }
    p == pattern.len()
}

fn globus_match_class(pattern: &[u8], byte: u8) -> Option<(bool, usize)> {
    let close = pattern.iter().position(|b| *b == b']')?;
    let mut index = 1;
    let mut matched = false;
    let negated = pattern.get(1) == Some(&b'!') || pattern.get(1) == Some(&b'^');
    if negated {
        index = 2;
    }
    while index < close {
        let low = pattern[index];
        if index + 2 < close && pattern[index + 1] == b'-' {
            let high = pattern[index + 2];
            if low <= byte && byte <= high {
                matched = true;
            }
            index += 3;
        } else {
            if low == byte {
                matched = true;
            }
            index += 1;
        }
    }
    Some((matched != negated, close + 1))
}

fn globus_match_alt(pattern: &[u8], text: &[u8]) -> Option<(bool, usize)> {
    let close = pattern.iter().position(|b| *b == b'}')?;
    let inner = &pattern[1..close];
    let mut start = 0;
    for (index, byte) in inner.iter().enumerate() {
        if *byte == b',' || index + 1 == inner.len() {
            let end = if *byte == b',' { index } else { index + 1 };
            let alternative = &inner[start..end];
            let mut combined = alternative.to_vec();
            combined.extend_from_slice(&pattern[close + 1..]);
            if globus_match_here(&combined, text) {
                return Some((true, close + 1));
            }
            start = index + 1;
        }
    }
    Some((false, close + 1))
}

pub fn globus_matches(pattern: &str, path: &str) -> bool {
    globus_match_here(pattern.as_bytes(), path.as_bytes())
}

pub fn globus_find(pattern: &str, root: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut stack = vec![std::path::PathBuf::from(root)];
    while let Some(directory) = stack.pop() {
        let Ok(entries) = std::fs::read_dir(&directory) else {
            continue;
        };
        let mut names: Vec<_> = entries.flatten().map(|entry| entry.path()).collect();
        names.sort();
        for path in names {
            let relative = path.strip_prefix(root).unwrap_or(&path);
            let text = relative.to_string_lossy().replace('\\', "/");
            if globus_matches(pattern, &text) {
                out.push(text);
            }
            if path.is_dir() {
                stack.push(path);
            }
        }
    }
    out.sort();
    out
}

// ---------------------------------------------------------------------------
// cellula: celdas globales inicializadas una vez.
// ---------------------------------------------------------------------------

static CELLULA: std::sync::LazyLock<std::sync::Mutex<std::collections::BTreeMap<String, String>>> =
    std::sync::LazyLock::new(|| std::sync::Mutex::new(std::collections::BTreeMap::new()));

fn cellula_map() -> std::sync::MutexGuard<'static, std::collections::BTreeMap<String, String>> {
    CELLULA.lock().unwrap_or_else(std::sync::PoisonError::into_inner)
}

pub fn cellula_get(key: &str) -> Option<String> {
    cellula_map().get(key).cloned()
}

pub fn cellula_set_once(key: &str, value: &str) -> bool {
    let mut map = cellula_map();
    if map.contains_key(key) {
        false
    } else {
        map.insert(key.to_owned(), value.to_owned());
        true
    }
}

pub fn cellula_set(key: &str, value: &str) {
    cellula_map().insert(key.to_owned(), value.to_owned());
}

pub fn cellula_remove(key: &str) -> bool {
    cellula_map().remove(key).is_some()
}

pub fn cellula_clear() {
    cellula_map().clear();
}

pub fn cellula_keys() -> Vec<String> {
    cellula_map().keys().cloned().collect()
}

// ---------------------------------------------------------------------------
// rete: TCP bloqueante con registro de sockets.
// ---------------------------------------------------------------------------

static RETE_LISTENERS: std::sync::LazyLock<std::sync::Mutex<Vec<Option<std::net::TcpListener>>>> =
    std::sync::LazyLock::new(|| std::sync::Mutex::new(Vec::new()));

static RETE_STREAMS: std::sync::LazyLock<std::sync::Mutex<Vec<Option<std::net::TcpStream>>>> =
    std::sync::LazyLock::new(|| std::sync::Mutex::new(Vec::new()));

fn rete_peer(addr: std::net::SocketAddr) -> crate::std::rete::PeerAddr {
    crate::std::rete::PeerAddr {
        host: addr.ip().to_string(),
        port: i32::from(addr.port() as u16),
    }
}

fn rete_error(message: impl std::fmt::Display) -> crate::std::rete::ReteError {
    crate::std::rete::ReteError {
        message: message.to_string(),
    }
}

pub fn rete_bind(
    host: &str,
    port: i32,
) -> std::result::Result<crate::std::rete::TcpListener, crate::std::rete::ReteError> {
    #[allow(clippy::cast_sign_loss, clippy::cast_possible_truncation)]
    let port = u16::try_from(port).map_err(|_| rete_error("puerto fuera de rango"))?;
    let listener = std::net::TcpListener::bind((host, port)).map_err(rete_error)?;
    let mut registry = RETE_LISTENERS.lock().unwrap_or_else(std::sync::PoisonError::into_inner);
    registry.push(Some(listener));
    #[allow(clippy::cast_possible_truncation)]
    let handle = (registry.len() - 1) as u64;
    std::result::Result::Ok(crate::std::rete::TcpListener { handle })
}

fn rete_with_listener<R>(
    handle: u64,
    action: impl FnOnce(&std::net::TcpListener) -> std::io::Result<R>,
) -> std::result::Result<R, crate::std::rete::ReteError> {
    let registry = RETE_LISTENERS.lock().unwrap_or_else(std::sync::PoisonError::into_inner);
    #[allow(clippy::cast_possible_truncation)]
    let index = handle as usize;
    let listener = registry
        .get(index)
        .and_then(Option::as_ref)
        .ok_or_else(|| rete_error("listener cerrado"))?;
    action(listener).map_err(rete_error)
}

pub fn rete_listener_addr(
    listener: &crate::std::rete::TcpListener,
) -> std::result::Result<crate::std::rete::PeerAddr, crate::std::rete::ReteError> {
    rete_with_listener(listener.handle, std::net::TcpListener::local_addr).map(rete_peer)
}

pub fn rete_accept(
    listener: crate::std::rete::TcpListener,
) -> std::result::Result<(crate::std::rete::TcpStream, crate::std::rete::PeerAddr), crate::std::rete::ReteError>
{
    let (stream, peer) = rete_with_listener(listener.handle, std::net::TcpListener::accept)?;
    let mut registry = RETE_STREAMS.lock().unwrap_or_else(std::sync::PoisonError::into_inner);
    registry.push(Some(stream));
    #[allow(clippy::cast_possible_truncation)]
    let handle = (registry.len() - 1) as u64;
    std::result::Result::Ok((crate::std::rete::TcpStream { handle }, rete_peer(peer)))
}

pub fn rete_listener_close(listener: crate::std::rete::TcpListener) {
    let mut registry = RETE_LISTENERS.lock().unwrap_or_else(std::sync::PoisonError::into_inner);
    #[allow(clippy::cast_possible_truncation)]
    let index = listener.handle as usize;
    if let Some(slot) = registry.get_mut(index) {
        *slot = None;
    }
}

pub fn rete_connect(
    host: &str,
    port: i32,
) -> std::result::Result<crate::std::rete::TcpStream, crate::std::rete::ReteError> {
    #[allow(clippy::cast_sign_loss, clippy::cast_possible_truncation)]
    let port = u16::try_from(port).map_err(|_| rete_error("puerto fuera de rango"))?;
    let stream = std::net::TcpStream::connect((host, port)).map_err(rete_error)?;
    let mut registry = RETE_STREAMS.lock().unwrap_or_else(std::sync::PoisonError::into_inner);
    registry.push(Some(stream));
    #[allow(clippy::cast_possible_truncation)]
    let handle = (registry.len() - 1) as u64;
    std::result::Result::Ok(crate::std::rete::TcpStream { handle })
}

fn rete_with_stream<R>(
    handle: u64,
    action: impl FnOnce(&mut std::net::TcpStream) -> std::io::Result<R>,
) -> std::result::Result<R, crate::std::rete::ReteError> {
    let mut registry = RETE_STREAMS.lock().unwrap_or_else(std::sync::PoisonError::into_inner);
    #[allow(clippy::cast_possible_truncation)]
    let index = handle as usize;
    let stream = registry
        .get_mut(index)
        .and_then(Option::as_mut)
        .ok_or_else(|| rete_error("socket cerrado"))?;
    action(stream).map_err(rete_error)
}

pub fn rete_peer_addr(
    stream: &crate::std::rete::TcpStream,
) -> std::result::Result<crate::std::rete::PeerAddr, crate::std::rete::ReteError> {
    rete_with_stream(stream.handle, |socket| socket.peer_addr()).map(rete_peer)
}

pub fn rete_read(
    stream: &mut crate::std::rete::TcpStream,
    count: usize,
) -> std::result::Result<Vec<u8>, crate::std::rete::ReteError> {
    use std::io::Read;
    let mut buffer = vec![0u8; count];
    let read = rete_with_stream(stream.handle, |socket| socket.read(&mut buffer))?;
    buffer.truncate(read);
    std::result::Result::Ok(buffer)
}

pub fn rete_read_to_string(
    stream: &mut crate::std::rete::TcpStream,
) -> std::result::Result<String, crate::std::rete::ReteError> {
    use std::io::Read;
    let mut text = String::new();
    rete_with_stream(stream.handle, |socket| socket.read_to_string(&mut text))?;
    std::result::Result::Ok(text)
}

pub fn rete_write(
    stream: &mut crate::std::rete::TcpStream,
    data: Vec<u8>,
) -> std::result::Result<usize, crate::std::rete::ReteError> {
    use std::io::Write;
    rete_with_stream(stream.handle, |socket| socket.write(&data))
}

pub fn rete_write_str(
    stream: &mut crate::std::rete::TcpStream,
    text: &str,
) -> std::result::Result<usize, crate::std::rete::ReteError> {
    use std::io::Write;
    rete_with_stream(stream.handle, |socket| socket.write(text.as_bytes()))
}

pub fn rete_flush(
    stream: &mut crate::std::rete::TcpStream,
) -> std::result::Result<(), crate::std::rete::ReteError> {
    use std::io::Write;
    rete_with_stream(stream.handle, std::io::Write::flush)
}

pub fn rete_set_read_timeout(
    stream: &mut crate::std::rete::TcpStream,
    millis: i32,
) -> std::result::Result<(), crate::std::rete::ReteError> {
    #[allow(clippy::cast_sign_loss, clippy::cast_possible_truncation)]
    let millis = u64::try_from(millis).map_err(|_| rete_error("timeout negativo"))?;
    let duration = std::time::Duration::from_millis(millis);
    rete_with_stream(stream.handle, |socket| socket.set_read_timeout(Some(duration)).map(|()| ()))
}

pub fn rete_shutdown(stream: crate::std::rete::TcpStream) {
    let mut registry = RETE_STREAMS.lock().unwrap_or_else(std::sync::PoisonError::into_inner);
    #[allow(clippy::cast_possible_truncation)]
    let index = stream.handle as usize;
    if let Some(slot) = registry.get_mut(index) {
        if let Some(socket) = slot.take() {
            let _ = socket.shutdown(std::net::Shutdown::Both);
        }
    }
}

// ---------------------------------------------------------------------------
// archivum: tar (ustar) sin compresión.
// ---------------------------------------------------------------------------

fn archivum_error(message: impl std::fmt::Display) -> crate::std::archivum::ArchivumError {
    crate::std::archivum::ArchivumError {
        message: message.to_string(),
    }
}

fn archivum_octal(value: u64, width: usize) -> String {
    let digits = format!("{value:o}");
    let padded = format!("{:0>width$}", digits, width = width.saturating_sub(1));
    format!("{padded}\0")
}

fn archivum_checksum(header: &[u8; 512]) -> u32 {
    header
        .iter()
        .enumerate()
        .map(|(index, byte)| {
            if (148..156).contains(&index) {
                u32::from(b' ')
            } else {
                u32::from(*byte)
            }
        })
        .sum()
}

fn archivum_header(name: &str, size: u64, directory: bool, mode: u32) -> [u8; 512] {
    let mut header = [0u8; 512];
    let raw = name.as_bytes();
    let limit = raw.len().min(100);
    header[..limit].copy_from_slice(&raw[..limit]);
    header[100..108].copy_from_slice(archivum_octal(u64::from(mode), 8).as_bytes());
    header[108..116].copy_from_slice(archivum_octal(0, 8).as_bytes());
    header[116..124].copy_from_slice(archivum_octal(0, 8).as_bytes());
    header[124..136].copy_from_slice(archivum_octal(size, 12).as_bytes());
    header[136..148].copy_from_slice(archivum_octal(0, 12).as_bytes());
    header[148..156].copy_from_slice(b"        ");
    header[156] = if directory { b'5' } else { b'0' };
    header[257..263].copy_from_slice(b"ustar\0");
    header[263..265].copy_from_slice(b"00");
    let checksum = archivum_checksum(&header);
    header[148..156].copy_from_slice(format!("{checksum:06o}\0 ").as_bytes());
    header
}

fn archivum_pad(out: &mut Vec<u8>, size: usize) {
    let remainder = size % 512;
    if remainder != 0 {
        out.extend(std::iter::repeat_n(0u8, 512 - remainder));
    }
}

// ---------------------------------------------------------------------------
// Compresión: inflate (RFC 1951), gzip (RFC 1952) y zip (APPNOTE 6.3).
// El codificador emite bloques *stored*: el archivo es válido y cualquier
// herramienta lo lee, pero no reduce tamaño. El decodificador sí es completo
// (stored, Huffman fijo y Huffman dinámico), para poder leer archivos reales.
// ---------------------------------------------------------------------------

struct InflateBits<'a> {
    data: &'a [u8],
    pos: usize,
    bit: u32,
    count: u32,
}

impl<'a> InflateBits<'a> {
    fn new(data: &'a [u8]) -> Self {
        Self { data, pos: 0, bit: 0, count: 0 }
    }

    fn bits(&mut self, want: u32) -> std::result::Result<u32, String> {
        let mut value = 0u32;
        for shift in 0..want {
            if self.count == 0 {
                let byte = *self.data.get(self.pos).ok_or("datos comprimidos truncados")?;
                self.pos += 1;
                self.bit = u32::from(byte);
                self.count = 8;
            }
            value |= (self.bit & 1) << shift;
            self.bit >>= 1;
            self.count -= 1;
        }
        std::result::Result::Ok(value)
    }

    fn align(&mut self) {
        self.bit = 0;
        self.count = 0;
    }
}

struct InflateHuffman {
    counts: [u16; 16],
    symbols: Vec<u16>,
}

impl InflateHuffman {
    fn from_lengths(lengths: &[u8]) -> Self {
        let mut counts = [0u16; 16];
        for length in lengths {
            counts[usize::from(*length)] += 1;
        }
        counts[0] = 0;
        let mut offsets = [0u16; 16];
        for length in 1..16 {
            offsets[length] = offsets[length - 1] + counts[length - 1];
        }
        let mut symbols = vec![0u16; lengths.len()];
        for (symbol, length) in lengths.iter().enumerate() {
            if *length != 0 {
                symbols[usize::from(offsets[usize::from(*length)])] = symbol as u16;
                offsets[usize::from(*length)] += 1;
            }
        }
        Self { counts, symbols }
    }

    fn decode(&self, bits: &mut InflateBits<'_>) -> std::result::Result<u16, String> {
        let mut code: i32 = 0;
        let mut first: i32 = 0;
        let mut index: i32 = 0;
        for length in 1..16 {
            code |= bits.bits(1)? as i32;
            let count = i32::from(self.counts[length]);
            if code - count < first {
                return std::result::Result::Ok(self.symbols[(index + (code - first)) as usize]);
            }
            index += count;
            first = (first + count) << 1;
            code <<= 1;
        }
        std::result::Result::Err("código Huffman inválido".to_owned())
    }
}

const INFLATE_LENGTH_BASE: [u16; 29] = [
    3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 17, 19, 23, 27, 31, 35, 43, 51, 59, 67, 83, 99, 115,
    131, 163, 195, 227, 258,
];
const INFLATE_LENGTH_EXTRA: [u8; 29] = [
    0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 0,
];
const INFLATE_DIST_BASE: [u16; 30] = [
    1, 2, 3, 4, 5, 7, 9, 13, 17, 25, 33, 49, 65, 97, 129, 193, 257, 385, 513, 769, 1025, 1537,
    2049, 3073, 4097, 6145, 8193, 12289, 16385, 24577,
];
const INFLATE_DIST_EXTRA: [u8; 30] = [
    0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12,
    13, 13,
];

fn inflate_fixed_tables() -> (InflateHuffman, InflateHuffman) {
    let mut literal = [0u8; 288];
    for (symbol, length) in literal.iter_mut().enumerate() {
        *length = match symbol {
            0..=143 => 8,
            144..=255 => 9,
            256..=279 => 7,
            _ => 8,
        };
    }
    (InflateHuffman::from_lengths(&literal), InflateHuffman::from_lengths(&[5u8; 30]))
}

fn inflate_dynamic_tables(
    bits: &mut InflateBits<'_>,
) -> std::result::Result<(InflateHuffman, InflateHuffman), String> {
    let hlit = bits.bits(5)? as usize + 257;
    let hdist = bits.bits(5)? as usize + 1;
    let hclen = bits.bits(4)? as usize + 4;
    let order = [16usize, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15];
    let mut code_lengths = [0u8; 19];
    for index in 0..hclen {
        code_lengths[order[index]] = bits.bits(3)? as u8;
    }
    let code_huffman = InflateHuffman::from_lengths(&code_lengths);
    let mut lengths = vec![0u8; hlit + hdist];
    let mut index = 0;
    while index < lengths.len() {
        let symbol = code_huffman.decode(bits)?;
        match symbol {
            0..=15 => {
                lengths[index] = symbol as u8;
                index += 1;
            }
            16 => {
                if index == 0 {
                    return std::result::Result::Err("repetición sin longitud previa".to_owned());
                }
                let repeat = bits.bits(2)? as usize + 3;
                let previous = lengths[index - 1];
                for _ in 0..repeat {
                    if index >= lengths.len() {
                        break;
                    }
                    lengths[index] = previous;
                    index += 1;
                }
            }
            17 => {
                let repeat = bits.bits(3)? as usize + 3;
                index = (index + repeat).min(lengths.len());
            }
            18 => {
                let repeat = bits.bits(7)? as usize + 11;
                index = (index + repeat).min(lengths.len());
            }
            _ => return std::result::Result::Err("símbolo de longitud inválido".to_owned()),
        }
    }
    let literal = InflateHuffman::from_lengths(&lengths[..hlit]);
    let distance = InflateHuffman::from_lengths(&lengths[hlit..]);
    std::result::Result::Ok((literal, distance))
}

/// Descomprime un flujo deflate crudo (sin cabecera gzip ni zlib).
fn inflate_raw(data: &[u8]) -> std::result::Result<Vec<u8>, String> {
    let mut bits = InflateBits::new(data);
    let mut out: Vec<u8> = Vec::new();
    loop {
        let last = bits.bits(1)? == 1;
        let kind = bits.bits(2)?;
        match kind {
            0 => {
                bits.align();
                let length = bits.bits(16)? as usize;
                let complement = bits.bits(16)? as usize;
                if length != (!complement & 0xffff) {
                    return std::result::Result::Err("bloque stored corrupto".to_owned());
                }
                for _ in 0..length {
                    out.push(bits.bits(8)? as u8);
                }
            }
            1 => {
                let (literal, distance) = inflate_fixed_tables();
                inflate_block(&mut bits, &literal, &distance, &mut out)?;
            }
            2 => {
                let (literal, distance) = inflate_dynamic_tables(&mut bits)?;
                inflate_block(&mut bits, &literal, &distance, &mut out)?;
            }
            _ => return std::result::Result::Err("tipo de bloque deflate inválido".to_owned()),
        }
        if last {
            break;
        }
    }
    std::result::Result::Ok(out)
}

fn inflate_block(
    bits: &mut InflateBits<'_>,
    literal: &InflateHuffman,
    distance: &InflateHuffman,
    out: &mut Vec<u8>,
) -> std::result::Result<(), String> {
    loop {
        let symbol = literal.decode(bits)?;
        match symbol {
            0..=255 => out.push(symbol as u8),
            256 => return std::result::Result::Ok(()),
            257..=285 => {
                let index = usize::from(symbol - 257);
                let length = u32::from(INFLATE_LENGTH_BASE[index])
                    + bits.bits(u32::from(INFLATE_LENGTH_EXTRA[index]))?;
                let dist_symbol = distance.decode(bits)?;
                if dist_symbol >= 30 {
                    return std::result::Result::Err("distancia inválida".to_owned());
                }
                let dist_index = usize::from(dist_symbol);
                let dist = u32::from(INFLATE_DIST_BASE[dist_index])
                    + bits.bits(u32::from(INFLATE_DIST_EXTRA[dist_index]))?;
                if u32::try_from(out.len()).unwrap_or(u32::MAX) < dist {
                    return std::result::Result::Err("distancia fuera de rango".to_owned());
                }
                let start = out.len() - dist as usize;
                for offset in 0..length as usize {
                    let byte = out[start + offset];
                    out.push(byte);
                }
            }
            _ => return std::result::Result::Err("símbolo de longitud inválido".to_owned()),
        }
    }
}

fn deflate_stored(data: &[u8]) -> Vec<u8> {
    let mut out = Vec::with_capacity(data.len() + data.len() / 65_535 * 5 + 8);
    let mut offset = 0;
    loop {
        let remaining = data.len() - offset;
        let take = remaining.min(65_535);
        let last = offset + take >= data.len();
        out.push(u8::from(last));
        let length = take as u16;
        out.extend_from_slice(&length.to_le_bytes());
        out.extend_from_slice(&(!length).to_le_bytes());
        out.extend_from_slice(&data[offset..offset + take]);
        offset += take;
        if last {
            break;
        }
    }
    out
}

pub fn gz_compress(data: Vec<u8>) -> Vec<u8> {
    let mut out = vec![0x1f, 0x8b, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x03];
    out.extend(deflate_stored(&data));
    let crc = digest_crc32(data.clone());
    out.extend_from_slice(&crc.to_le_bytes());
    out.extend_from_slice(&(data.len() as u32).to_le_bytes());
    out
}

pub fn gz_decompress(data: Vec<u8>) -> std::result::Result<Vec<u8>, crate::std::archivum::ArchivumError> {
    if data.len() < 18 || data[0] != 0x1f || data[1] != 0x8b {
        return std::result::Result::Err(archivum_error("cabecera gzip inválida"));
    }
    let flags = data[3];
    let mut offset = 10;
    if flags & 0x04 != 0 {
        if offset + 2 > data.len() {
            return std::result::Result::Err(archivum_error("gzip truncado"));
        }
        let extra = usize::from(u16::from_le_bytes([data[offset], data[offset + 1]]));
        offset += 2 + extra;
    }
    for flag in [0x08, 0x10] {
        if flags & flag != 0 {
            while offset < data.len() && data[offset] != 0 {
                offset += 1;
            }
            offset += 1;
        }
    }
    if flags & 0x02 != 0 {
        offset += 2;
    }
    if offset >= data.len() {
        return std::result::Result::Err(archivum_error("gzip truncado"));
    }
    let end = data.len().saturating_sub(8);
    let output = inflate_raw(&data[offset..end]).map_err(archivum_error)?;
    let crc = u32::from_le_bytes([data[end], data[end + 1], data[end + 2], data[end + 3]]);
    if crc != digest_crc32(output.clone()) {
        return std::result::Result::Err(archivum_error("CRC gzip inválido"));
    }
    let size = u32::from_le_bytes([data[end + 4], data[end + 5], data[end + 6], data[end + 7]]);
    if usize::try_from(size).ok() != Some(output.len()) {
        return std::result::Result::Err(archivum_error("longitud gzip inválida"));
    }
    std::result::Result::Ok(output)
}

fn zip_crc(data: &[u8]) -> u32 {
    digest_crc32(data.to_vec())
}

pub fn zip_create(
    archive: &str,
    base: &str,
    paths: Vec<String>,
) -> std::result::Result<(), crate::std::archivum::ArchivumError> {
    let base = std::path::Path::new(base);
    let mut out = Vec::new();
    let mut central = Vec::new();
    let mut count: u16 = 0;
    for relative in paths {
        let full = base.join(&relative);
        let metadata = std::fs::symlink_metadata(&full).map_err(archivum_error)?;
        if !metadata.is_file() {
            continue;
        }
        let name = relative.trim_start_matches('/').replace('\\', "/");
        let contents = std::fs::read(&full).map_err(archivum_error)?;
        let crc = zip_crc(&contents);
        let size = u32::try_from(contents.len())
            .map_err(|_| archivum_error("fichero demasiado grande para zip"))?;
        let name_bytes = name.as_bytes();
        let name_len = u16::try_from(name_bytes.len())
            .map_err(|_| archivum_error("nombre demasiado largo"))?;
        let offset = u32::try_from(out.len()).map_err(|_| archivum_error("zip demasiado grande"))?;
        out.extend_from_slice(&0x0403_4b50u32.to_le_bytes());
        out.extend_from_slice(&20u16.to_le_bytes());
        out.extend_from_slice(&0u16.to_le_bytes());
        out.extend_from_slice(&0u16.to_le_bytes());
        out.extend_from_slice(&0u16.to_le_bytes());
        // Fecha DOS: 1980-01-01 (0 = mes/día inválidos para muchos lectores).
        out.extend_from_slice(&0x0021u16.to_le_bytes());
        out.extend_from_slice(&crc.to_le_bytes());
        out.extend_from_slice(&size.to_le_bytes());
        out.extend_from_slice(&size.to_le_bytes());
        out.extend_from_slice(&name_len.to_le_bytes());
        out.extend_from_slice(&0u16.to_le_bytes());
        out.extend_from_slice(name_bytes);
        out.extend_from_slice(&contents);
        central.extend_from_slice(&0x0201_4b50u32.to_le_bytes());
        central.extend_from_slice(&20u16.to_le_bytes());
        central.extend_from_slice(&20u16.to_le_bytes());
        central.extend_from_slice(&0u16.to_le_bytes());
        central.extend_from_slice(&0u16.to_le_bytes());
        central.extend_from_slice(&0u16.to_le_bytes());
        central.extend_from_slice(&0x0021u16.to_le_bytes());
        central.extend_from_slice(&crc.to_le_bytes());
        central.extend_from_slice(&size.to_le_bytes());
        central.extend_from_slice(&size.to_le_bytes());
        central.extend_from_slice(&name_len.to_le_bytes());
        central.extend_from_slice(&0u16.to_le_bytes());
        central.extend_from_slice(&0u16.to_le_bytes());
        central.extend_from_slice(&0u16.to_le_bytes());
        central.extend_from_slice(&0u16.to_le_bytes());
        central.extend_from_slice(&0u32.to_le_bytes());
        central.extend_from_slice(&offset.to_le_bytes());
        central.extend_from_slice(name_bytes);
        count += 1;
    }
    let central_offset =
        u32::try_from(out.len()).map_err(|_| archivum_error("zip demasiado grande"))?;
    out.extend_from_slice(&central);
    let central_size =
        u32::try_from(central.len()).map_err(|_| archivum_error("zip demasiado grande"))?;
    out.extend_from_slice(&0x0605_4b50u32.to_le_bytes());
    out.extend_from_slice(&0u16.to_le_bytes());
    out.extend_from_slice(&0u16.to_le_bytes());
    out.extend_from_slice(&count.to_le_bytes());
    out.extend_from_slice(&count.to_le_bytes());
    out.extend_from_slice(&central_size.to_le_bytes());
    out.extend_from_slice(&central_offset.to_le_bytes());
    out.extend_from_slice(&0u16.to_le_bytes());
    std::fs::write(archive, out).map_err(archivum_error)?;
    std::result::Result::Ok(())
}

struct ZipEntry {
    name: String,
    method: u16,
    compressed: Vec<u8>,
}

fn zip_read_entries(
    bytes: &[u8],
) -> std::result::Result<Vec<ZipEntry>, crate::std::archivum::ArchivumError> {
    let mut eocd = None;
    let mut index = bytes.len().saturating_sub(22);
    loop {
        if bytes.len() >= 4 && bytes[index..index + 4] == [0x50, 0x4b, 0x05, 0x06] {
            eocd = Some(index);
            break;
        }
        if index == 0 {
            break;
        }
        index -= 1;
    }
    let eocd = eocd.ok_or_else(|| archivum_error("no es un zip (sin EOCD)"))?;
    let count = usize::from(u16::from_le_bytes([bytes[eocd + 10], bytes[eocd + 11]]));
    #[allow(clippy::cast_possible_truncation)]
    let mut offset = u32::from_le_bytes([
        bytes[eocd + 16],
        bytes[eocd + 17],
        bytes[eocd + 18],
        bytes[eocd + 19],
    ]) as usize;
    let mut entries = Vec::with_capacity(count);
    for _ in 0..count {
        if offset + 46 > bytes.len() || bytes[offset..offset + 4] != [0x50, 0x4b, 0x01, 0x02] {
            return std::result::Result::Err(archivum_error("directorio central corrupto"));
        }
        let method = u16::from_le_bytes([bytes[offset + 10], bytes[offset + 11]]);
        let compressed_size = u32::from_le_bytes([
            bytes[offset + 20],
            bytes[offset + 21],
            bytes[offset + 22],
            bytes[offset + 23],
        ]) as usize;
        let name_len = usize::from(u16::from_le_bytes([bytes[offset + 28], bytes[offset + 29]]));
        let extra_len = usize::from(u16::from_le_bytes([bytes[offset + 30], bytes[offset + 31]]));
        let comment_len = usize::from(u16::from_le_bytes([bytes[offset + 32], bytes[offset + 33]]));
        let local_offset = u32::from_le_bytes([
            bytes[offset + 42],
            bytes[offset + 43],
            bytes[offset + 44],
            bytes[offset + 45],
        ]) as usize;
        let name = String::from_utf8_lossy(&bytes[offset + 46..offset + 46 + name_len]).into_owned();
        offset += 46 + name_len + extra_len + comment_len;
        if local_offset + 30 > bytes.len() {
            return std::result::Result::Err(archivum_error("entrada zip corrupta"));
        }
        let local_name = usize::from(u16::from_le_bytes([
            bytes[local_offset + 26],
            bytes[local_offset + 27],
        ]));
        let local_extra = usize::from(u16::from_le_bytes([
            bytes[local_offset + 28],
            bytes[local_offset + 29],
        ]));
        let start = local_offset + 30 + local_name + local_extra;
        let end = (start + compressed_size).min(bytes.len());
        entries.push(ZipEntry { name, method, compressed: bytes[start..end].to_vec() });
    }
    std::result::Result::Ok(entries)
}

pub fn zip_entries(
    archive: &str,
) -> std::result::Result<Vec<String>, crate::std::archivum::ArchivumError> {
    let bytes = std::fs::read(archive).map_err(archivum_error)?;
    let entries = zip_read_entries(&bytes)?;
    std::result::Result::Ok(entries.into_iter().map(|entry| entry.name).collect())
}

pub fn zip_extract(
    archive: &str,
    dest: &str,
) -> std::result::Result<Vec<String>, crate::std::archivum::ArchivumError> {
    let bytes = std::fs::read(archive).map_err(archivum_error)?;
    let entries = zip_read_entries(&bytes)?;
    let mut extracted = Vec::new();
    for entry in entries {
        if entry.name.contains("..") {
            return std::result::Result::Err(archivum_error("ruta insegura en el archivo"));
        }
        let data = match entry.method {
            0 => entry.compressed,
            8 => inflate_raw(&entry.compressed).map_err(archivum_error)?,
            other => return std::result::Result::Err(archivum_error(format!("método zip {other} no soportado"))),
        };
        let target = std::path::Path::new(dest).join(&entry.name);
        if let Some(parent) = target.parent() {
            std::fs::create_dir_all(parent).map_err(archivum_error)?;
        }
        std::fs::write(&target, data).map_err(archivum_error)?;
        extracted.push(entry.name);
    }
    std::result::Result::Ok(extracted)
}

pub fn archivum_targz_create(
    archive: &str,
    base: &str,
    paths: Vec<String>,
) -> std::result::Result<(), crate::std::archivum::ArchivumError> {
    let temporary = format!("{archive}.tar");
    archivum_create(&temporary, base, paths)?;
    let bytes = std::fs::read(&temporary).map_err(archivum_error)?;
    let compressed = gz_compress(bytes);
    std::fs::write(archive, compressed).map_err(archivum_error)?;
    std::fs::remove_file(&temporary).map_err(archivum_error)?;
    std::result::Result::Ok(())
}

pub fn archivum_targz_entries(
    archive: &str,
) -> std::result::Result<Vec<String>, crate::std::archivum::ArchivumError> {
    let bytes = std::fs::read(archive).map_err(archivum_error)?;
    let tar = gz_decompress(bytes)?;
    let mut names = Vec::new();
    let mut offset = 0;
    while let Some((name, _size, _directory, _start)) = archivum_read_entry(&tar, &mut offset)? {
        names.push(name);
    }
    std::result::Result::Ok(names)
}

pub fn archivum_targz_extract(
    archive: &str,
    dest: &str,
) -> std::result::Result<Vec<String>, crate::std::archivum::ArchivumError> {
    let temporary = format!("{archive}.tar");
    let bytes = std::fs::read(archive).map_err(archivum_error)?;
    let tar = gz_decompress(bytes)?;
    std::fs::write(&temporary, tar).map_err(archivum_error)?;
    let extracted = archivum_extract(&temporary, dest)?;
    std::fs::remove_file(&temporary).map_err(archivum_error)?;
    std::result::Result::Ok(extracted)
}

pub fn archivum_create(
    archive: &str,
    base: &str,
    paths: Vec<String>,
) -> std::result::Result<(), crate::std::archivum::ArchivumError> {
    let mut out = Vec::new();
    let base = std::path::Path::new(base);
    for relative in paths {
        let full = base.join(&relative);
        let metadata = std::fs::symlink_metadata(&full).map_err(archivum_error)?;
        let name = relative.trim_start_matches('/').replace('\\', "/");
        if metadata.is_dir() {
            let name = if name.ends_with('/') { name } else { format!("{name}/") };
            out.extend_from_slice(&archivum_header(&name, 0, true, 0o755));
        } else if metadata.is_file() {
            let contents = std::fs::read(&full).map_err(archivum_error)?;
            #[allow(clippy::cast_possible_truncation)]
            let size = contents.len() as u64;
            out.extend_from_slice(&archivum_header(&name, size, false, 0o644));
            out.extend_from_slice(&contents);
            archivum_pad(&mut out, contents.len());
        }
    }
    out.extend(std::iter::repeat_n(0u8, 1024));
    std::fs::write(archive, out).map_err(archivum_error)?;
    std::result::Result::Ok(())
}

fn archivum_read_entry(
    bytes: &[u8],
    offset: &mut usize,
) -> std::result::Result<Option<(String, u64, bool, usize)>, crate::std::archivum::ArchivumError> {
    if *offset + 512 > bytes.len() {
        return std::result::Result::Ok(None);
    }
    let header: &[u8; 512] = bytes[*offset..*offset + 512]
        .try_into()
        .map_err(|_| archivum_error("cabecera tar inválida"))?;
    if header[..100].iter().all(|byte| *byte == 0) {
        return std::result::Result::Ok(None);
    }
    let name = String::from_utf8_lossy(&header[..100]);
    let name = name.trim_end_matches('\0').to_owned();
    let size_text = String::from_utf8_lossy(&header[124..136]);
    let size = u64::from_str_radix(size_text.trim_matches(|c: char| c == '\0' || c == ' '), 8)
        .map_err(|_| archivum_error("tamaño tar inválido"))?;
    let directory = header[156] == b'5';
    *offset += 512;
    #[allow(clippy::cast_possible_truncation)]
    let size_usize = size as usize;
    let data_start = *offset;
    let padded = size_usize.div_ceil(512) * 512;
    *offset = (*offset + padded).min(bytes.len());
    std::result::Result::Ok(Some((name, size, directory, data_start)))
}

pub fn archivum_extract(
    archive: &str,
    dest: &str,
) -> std::result::Result<Vec<String>, crate::std::archivum::ArchivumError> {
    let bytes = std::fs::read(archive).map_err(archivum_error)?;
    let mut extracted = Vec::new();
    let mut offset = 0;
    while let Some((name, size, directory, data_start)) = archivum_read_entry(&bytes, &mut offset)? {
        if name.contains("..") {
            return std::result::Result::Err(archivum_error("ruta insegura en el archivo"));
        }
        let target = std::path::Path::new(dest).join(&name);
        if directory {
            std::fs::create_dir_all(&target).map_err(archivum_error)?;
        } else {
            if let Some(parent) = target.parent() {
                std::fs::create_dir_all(parent).map_err(archivum_error)?;
            }
            #[allow(clippy::cast_possible_truncation)]
            let end = (data_start + size as usize).min(bytes.len());
            std::fs::write(&target, &bytes[data_start..end]).map_err(archivum_error)?;
        }
        extracted.push(name);
    }
    std::result::Result::Ok(extracted)
}

pub fn archivum_entries(
    archive: &str,
) -> std::result::Result<Vec<String>, crate::std::archivum::ArchivumError> {
    let bytes = std::fs::read(archive).map_err(archivum_error)?;
    let mut names = Vec::new();
    let mut offset = 0;
    while let Some((name, _size, _directory, _data_start)) = archivum_read_entry(&bytes, &mut offset)? {
        names.push(name);
    }
    std::result::Result::Ok(names)
}

pub fn archivum_pack(
    archive: &str,
    base: &str,
) -> std::result::Result<(), crate::std::archivum::ArchivumError> {
    let mut paths = Vec::new();
    let mut stack = vec![std::path::PathBuf::from(base)];
    while let Some(directory) = stack.pop() {
        let Ok(entries) = std::fs::read_dir(&directory) else {
            continue;
        };
        let mut children: Vec<_> = entries.flatten().map(|entry| entry.path()).collect();
        children.sort();
        for path in children {
            let relative = path
                .strip_prefix(base)
                .unwrap_or(&path)
                .to_string_lossy()
                .replace('\\', "/");
            paths.push(relative);
            if path.is_dir() {
                stack.push(path);
            }
        }
    }
    paths.sort();
    archivum_create(archive, base, paths)
}

// ---------------------------------------------------------------------------
// libra: TOML aplanado (clave punteada -> texto + tipo).
// ---------------------------------------------------------------------------

fn libra_error(line: usize, message: impl std::fmt::Display) -> crate::std::libra::LibraError {
    #[allow(clippy::cast_possible_truncation, clippy::cast_possible_wrap)]
    let line = line as i32;
    crate::std::libra::LibraError {
        message: message.to_string(),
        line,
    }
}

fn libra_is_date(raw: &str) -> bool {
    let bytes = raw.as_bytes();
    bytes.len() == 10
        && bytes[4] == b'-'
        && bytes[7] == b'-'
        && raw
            .split('-')
            .all(|part| part.chars().all(|ch| ch.is_ascii_digit()))
}

fn libra_is_time(raw: &str) -> bool {
    let mut parts = raw.split(':');
    let (Some(hour), Some(minute), Some(second)) = (parts.next(), parts.next(), parts.next()) else {
        return false;
    };
    parts.next().is_none()
        && hour.len() == 2
        && minute.len() == 2
        && second.len() >= 2
        && [hour, minute, &second[..2]]
            .iter()
            .all(|part| part.chars().all(|ch| ch.is_ascii_digit()))
}

fn libra_is_datetime(raw: &str) -> bool {
    match raw.split_once(['T', 't', ' ']) {
        Some((date, rest)) => libra_is_date(date) && !rest.is_empty(),
        None => false,
    }
}

struct LibraParser<'a> {
    chars: Vec<char>,
    pos: usize,
    line: usize,
    table: crate::std::libra::Table,
    prefix: String,
    arrays: Vec<(String, usize)>,
    _source: std::marker::PhantomData<&'a ()>,
}

impl<'a> LibraParser<'a> {
    fn new(text: &'a str) -> Self {
        Self {
            chars: text.chars().collect(),
            pos: 0,
            line: 1,
            table: crate::std::libra::Table {
                keys: Vec::new(),
                values: Vec::new(),
                kinds: Vec::new(),
            },
            prefix: String::new(),
            arrays: Vec::new(),
            _source: std::marker::PhantomData,
        }
    }

    fn peek(&self) -> Option<char> {
        self.chars.get(self.pos).copied()
    }

    fn bump(&mut self) -> Option<char> {
        let ch = self.peek()?;
        self.pos += 1;
        if ch == '\n' {
            self.line += 1;
        }
        Some(ch)
    }

    fn skip_spaces(&mut self) {
        while matches!(self.peek(), Some(' ' | '\t')) {
            self.bump();
        }
    }

    fn skip_comment(&mut self) {
        while let Some(ch) = self.peek() {
            if ch == '\n' {
                break;
            }
            self.bump();
        }
    }

    fn skip_blank(&mut self) {
        loop {
            match self.peek() {
                Some(' ' | '\t' | '\r' | '\n') => {
                    self.bump();
                }
                Some('#') => self.skip_comment(),
                _ => break,
            }
        }
    }

    fn dotted(&self, key: &str) -> String {
        if self.prefix.is_empty() {
            key.to_owned()
        } else {
            format!("{}.{key}", self.prefix)
        }
    }

    fn insert(&mut self, key: &str, value: String, kind: &str) {
        let full = self.dotted(key);
        self.table.keys.push(full);
        self.table.values.push(value);
        self.table.kinds.push(kind.to_owned());
    }

    fn parse_bare(&mut self) -> std::result::Result<String, crate::std::libra::LibraError> {
        let mut out = String::new();
        while let Some(ch) = self.peek() {
            if ch.is_alphanumeric() || ch == '_' || ch == '-' || ch == '.' {
                out.push(ch);
                self.bump();
            } else {
                break;
            }
        }
        if out.is_empty() {
            return std::result::Result::Err(libra_error(self.line, "se esperaba una clave"));
        }
        std::result::Result::Ok(out)
    }

    fn parse_string(&mut self) -> std::result::Result<String, crate::std::libra::LibraError> {
        let quote = self.bump().unwrap_or('"');
        let triple = self.peek() == Some(quote) && self.chars.get(self.pos + 1) == Some(&quote);
        if triple {
            self.bump();
            self.bump();
        }
        let mut out = String::new();
        loop {
            let Some(ch) = self.bump() else {
                return std::result::Result::Err(libra_error(self.line, "cadena sin cerrar"));
            };
            if ch == quote {
                if triple {
                    if self.peek() == Some(quote) && self.chars.get(self.pos + 1) == Some(&quote) {
                        self.bump();
                        self.bump();
                        break;
                    }
                    out.push(ch);
                } else {
                    break;
                }
            } else if ch == '\\' && quote == '"' {
                match self.bump() {
                    Some('n') => out.push('\n'),
                    Some('t') => out.push('\t'),
                    Some('r') => out.push('\r'),
                    Some('"') => out.push('"'),
                    Some('\\') => out.push('\\'),
                    Some('u') => {
                        if self.peek() == Some('{') {
                            self.bump();
                            let mut digits = String::new();
                            while let Some(next) = self.peek() {
                                if next == '}' {
                                    self.bump();
                                    break;
                                }
                                digits.push(next);
                                self.bump();
                            }
                            if let Ok(value) = u32::from_str_radix(&digits, 16) {
                                if let Some(decoded) = char::from_u32(value) {
                                    out.push(decoded);
                                }
                            }
                        }
                    }
                    Some(other) => out.push(other),
                    None => return std::result::Result::Err(libra_error(self.line, "escape incompleto")),
                }
            } else {
                out.push(ch);
            }
        }
        std::result::Result::Ok(out)
    }

    fn parse_value(&mut self) -> std::result::Result<(String, String), crate::std::libra::LibraError> {
        self.skip_spaces();
        match self.peek() {
            Some('"' | '\'') => {
                let text = self.parse_string()?;
                std::result::Result::Ok((text, "string".to_owned()))
            }
            Some('[') => {
                self.bump();
                let mut items = Vec::new();
                loop {
                    self.skip_blank();
                    match self.peek() {
                        Some(']') => {
                            self.bump();
                            break;
                        }
                        Some(',') => {
                            self.bump();
                        }
                        Some(_) => {
                            let (value, _kind) = self.parse_value()?;
                            items.push(value);
                        }
                        None => return std::result::Result::Err(libra_error(self.line, "array sin cerrar")),
                    }
                }
                std::result::Result::Ok((items.join("\u{1f}"), "array".to_owned()))
            }
            _ => {
                let mut raw = String::new();
                while let Some(ch) = self.peek() {
                    if ch == '\n' || ch == '#' || ch == ',' || ch == ']' {
                        break;
                    }
                    raw.push(ch);
                    self.bump();
                }
                let raw = raw.trim().to_owned();
                let kind = if raw == "true" || raw == "false" {
                    "bool"
                } else if raw.parse::<i64>().is_ok() {
                    "integer"
                } else if raw.parse::<f64>().is_ok() {
                    "float"
                } else if libra_is_datetime(&raw) {
                    "datetime"
                } else if libra_is_date(&raw) {
                    "date"
                } else if libra_is_time(&raw) {
                    "time"
                } else {
                    "string"
                };
                std::result::Result::Ok((raw, kind.to_owned()))
            }
        }
    }

    /// Tabla en línea: `{ a = 1, b = "x", c = { d = 2 } }`. Se aplana bajo la
    /// clave que la contiene (`tabla.a`, `tabla.c.d`).
    fn parse_inline_table(
        &mut self,
        key: &str,
    ) -> std::result::Result<(), crate::std::libra::LibraError> {
        self.bump();
        let saved = self.prefix.clone();
        self.prefix = self.dotted(key);
        loop {
            self.skip_blank();
            match self.peek() {
                Some('}') => {
                    self.bump();
                    break;
                }
                Some(',') => {
                    self.bump();
                }
                None => {
                    self.prefix = saved;
                    return std::result::Result::Err(libra_error(self.line, "tabla sin cerrar"));
                }
                Some(_) => {
                    let inner = self.parse_bare()?;
                    self.skip_spaces();
                    if self.peek() != Some('=') {
                        self.prefix = saved;
                        return std::result::Result::Err(libra_error(self.line, "se esperaba `=`"));
                    }
                    self.bump();
                    self.skip_spaces();
                    if self.peek() == Some('{') {
                        self.parse_inline_table(&inner)?;
                    } else {
                        let (value, kind) = self.parse_value()?;
                        self.insert(&inner, value, &kind);
                    }
                }
            }
        }
        self.prefix = saved;
        std::result::Result::Ok(())
    }

    fn parse_document(&mut self) -> std::result::Result<(), crate::std::libra::LibraError> {
        loop {
            self.skip_blank();
            match self.peek() {
                None => break,
                Some('[') => {
                    self.bump();
                    let array = self.peek() == Some('[');
                    if array {
                        self.bump();
                    }
                    self.skip_spaces();
                    let name = self.parse_bare()?;
                    self.skip_spaces();
                    while let Some(ch) = self.bump() {
                        if ch == ']' {
                            break;
                        }
                    }
                    if array {
                        if self.peek() == Some(']') {
                            self.bump();
                        }
                        // `[[nombre]]` se aplana con un índice por instancia:
                        // `nombre.0.campo`, `nombre.1.campo`, ...
                        let slot = match self.arrays.iter().position(|(key, _)| *key == name) {
                            Some(index) => index,
                            None => {
                                self.arrays.push((name.clone(), 0));
                                self.arrays.len() - 1
                            }
                        };
                        let instance = self.arrays[slot].1;
                        self.arrays[slot].1 += 1;
                        self.prefix = format!("{name}.{instance}");
                    } else {
                        self.prefix = name;
                    }
                }
                Some(_) => {
                    let key = self.parse_bare()?;
                    self.skip_spaces();
                    if self.peek() != Some('=') {
                        return std::result::Result::Err(libra_error(self.line, "se esperaba `=`"));
                    }
                    self.bump();
                    self.skip_spaces();
                    if self.peek() == Some('{') {
                        self.parse_inline_table(&key)?;
                    } else {
                        let (value, kind) = self.parse_value()?;
                        self.insert(&key, value, &kind);
                    }
                }
            }
        }
        std::result::Result::Ok(())
    }
}

pub fn libra_parse(text: &str) -> std::result::Result<crate::std::libra::Table, crate::std::libra::LibraError> {
    let mut parser = LibraParser::new(text);
    parser.parse_document()?;
    std::result::Result::Ok(parser.table)
}

pub fn libra_parse_file(
    path: &str,
) -> std::result::Result<crate::std::libra::Table, crate::std::libra::LibraError> {
    let text = std::fs::read_to_string(path).map_err(|error| libra_error(0, error))?;
    libra_parse(&text)
}

pub fn libra_get(table: &crate::std::libra::Table, key: &str) -> Option<String> {
    table
        .keys
        .iter()
        .position(|candidate| candidate == key)
        .and_then(|index| table.values.get(index))
        .map(|value| value.replace('\u{1f}', ", "))
}

pub fn libra_get_array(table: &crate::std::libra::Table, key: &str) -> Option<Vec<String>> {
    let index = table.keys.iter().position(|candidate| candidate == key)?;
    if table.kinds.get(index).map(std::string::String::as_str) != Some("array") {
        return None;
    }
    Some(
        table.values[index]
            .split('\u{1f}')
            .map(std::string::ToString::to_string)
            .collect(),
    )
}

pub fn libra_has(table: &crate::std::libra::Table, key: &str) -> bool {
    table.keys.iter().any(|candidate| candidate == key)
}

pub fn libra_kind_of(table: &crate::std::libra::Table, key: &str) -> Option<String> {
    table
        .keys
        .iter()
        .position(|candidate| candidate == key)
        .and_then(|index| table.kinds.get(index).cloned())
}

pub fn libra_keys_of(table: &crate::std::libra::Table, prefix: &str) -> Vec<String> {
    let dotted = format!("{prefix}.");
    table
        .keys
        .iter()
        .filter(|key| key.starts_with(&dotted))
        .cloned()
        .collect()
}

pub fn libra_get_int(table: &crate::std::libra::Table, key: &str) -> Option<i32> {
    libra_get(table, key)?.trim().parse().ok()
}

pub fn libra_get_float(table: &crate::std::libra::Table, key: &str) -> Option<f64> {
    libra_get(table, key)?.trim().parse().ok()
}

pub fn libra_get_bool(table: &crate::std::libra::Table, key: &str) -> Option<bool> {
    match libra_get(table, key)?.trim() {
        "true" => Some(true),
        "false" => Some(false),
        _ => None,
    }
}

// ---------------------------------------------------------------------------
// via: rutas (Path/PathBuf), tipos de archivo, permisos y recorrido configurable.
// ---------------------------------------------------------------------------

fn via_ms(value: std::io::Result<std::time::SystemTime>) -> std::result::Result<Option<i64>, crate::std::via::IoError> {
    match value {
        std::result::Result::Ok(time) => {
            let millis = time
                .duration_since(std::time::UNIX_EPOCH)
                .map_err(via_error)?
                .as_millis();
            std::result::Result::Ok(i64::try_from(millis).ok())
        }
        std::result::Result::Err(_) => std::result::Result::Ok(None),
    }
}

pub fn via_modified_ms(path: &str) -> std::result::Result<Option<i64>, crate::std::via::IoError> {
    let metadata = std::fs::metadata(path).map_err(via_error)?;
    via_ms(metadata.modified())
}

pub fn via_created_ms(path: &str) -> std::result::Result<Option<i64>, crate::std::via::IoError> {
    let metadata = std::fs::metadata(path).map_err(via_error)?;
    via_ms(metadata.created())
}

pub fn via_accessed_ms(path: &str) -> std::result::Result<Option<i64>, crate::std::via::IoError> {
    let metadata = std::fs::metadata(path).map_err(via_error)?;
    via_ms(metadata.accessed())
}

pub fn via_file_modified_ms(handle: u64) -> std::result::Result<Option<i64>, crate::std::via::IoError> {
    let metadata = via_with_file(handle, |file| file.metadata())?;
    via_ms(metadata.modified())
}

pub fn via_file_sync_all(handle: u64) -> std::result::Result<(), crate::std::via::IoError> {
    via_with_file(handle, |file| file.sync_all())
}

pub fn via_file_sync_data(handle: u64) -> std::result::Result<(), crate::std::via::IoError> {
    via_with_file(handle, |file| file.sync_data())
}

pub fn via_file_try_clone(handle: u64) -> std::result::Result<crate::std::via::File, crate::std::via::IoError> {
    let clone = via_with_file(handle, |file| file.try_clone())?;
    let mut files = VIA_FILES.lock().unwrap_or_else(std::sync::PoisonError::into_inner);
    files.push(Some(clone));
    #[allow(clippy::cast_possible_truncation)]
    let handle = (files.len() - 1) as u64;
    std::result::Result::Ok(crate::std::via::File { handle })
}

pub fn via_path_join(base: &str, child: &str) -> String {
    std::path::Path::new(base)
        .join(child)
        .to_string_lossy()
        .into_owned()
}

pub fn via_path_parent(path: &str) -> Option<String> {
    std::path::Path::new(path)
        .parent()
        .map(|parent| parent.to_string_lossy().into_owned())
}

pub fn via_path_file_name(path: &str) -> Option<String> {
    std::path::Path::new(path)
        .file_name()
        .map(|name| name.to_string_lossy().into_owned())
}

pub fn via_path_extension(path: &str) -> Option<String> {
    std::path::Path::new(path)
        .extension()
        .map(|extension| extension.to_string_lossy().into_owned())
}

pub fn via_path_file_stem(path: &str) -> Option<String> {
    std::path::Path::new(path)
        .file_stem()
        .map(|stem| stem.to_string_lossy().into_owned())
}

pub fn via_path_is_absolute(path: &str) -> bool {
    std::path::Path::new(path).is_absolute()
}

pub fn via_path_starts_with(path: &str, base: &str) -> bool {
    std::path::Path::new(path).starts_with(base)
}

pub fn via_path_ends_with(path: &str, suffix: &str) -> bool {
    std::path::Path::new(path).ends_with(suffix)
}

pub fn via_path_strip_prefix(path: &str, base: &str) -> Option<String> {
    std::path::Path::new(path)
        .strip_prefix(base)
        .ok()
        .map(|stripped| stripped.to_string_lossy().into_owned())
}

pub fn via_path_components(path: &str) -> Vec<String> {
    std::path::Path::new(path)
        .components()
        .map(|component| component.as_os_str().to_string_lossy().into_owned())
        .collect()
}

pub fn via_path_to_string_lossy(path: &str) -> String {
    std::path::Path::new(path).to_string_lossy().into_owned()
}

pub fn via_path_pop(path: &str) -> (String, bool) {
    let mut buffer = std::path::PathBuf::from(path);
    let removed = buffer.pop();
    (buffer.to_string_lossy().into_owned(), removed)
}

pub fn via_path_with_extension(path: &str, extension: &str) -> String {
    let mut buffer = std::path::PathBuf::from(path);
    buffer.set_extension(extension);
    buffer.to_string_lossy().into_owned()
}

pub fn via_path_set_extension(path: &str, extension: &str) -> (String, bool) {
    let mut buffer = std::path::PathBuf::from(path);
    let changed = buffer.set_extension(extension);
    (buffer.to_string_lossy().into_owned(), changed)
}

pub fn via_permissions(path: &str) -> std::result::Result<crate::std::via::Permissions, crate::std::via::IoError> {
    let metadata = std::fs::metadata(path).map_err(via_error)?;
    std::result::Result::Ok(crate::std::via::Permissions {
        readonly: metadata.permissions().readonly(),
    })
}

pub fn via_set_permissions(
    path: &str,
    permissions: crate::std::via::Permissions,
) -> std::result::Result<(), crate::std::via::IoError> {
    let metadata = std::fs::metadata(path).map_err(via_error)?;
    let mut permissions_rust = metadata.permissions();
    permissions_rust.set_readonly(permissions.readonly);
    std::fs::set_permissions(path, permissions_rust).map_err(via_error)
}

pub fn via_file_type(path: &str) -> std::result::Result<crate::std::via::FileType, crate::std::via::IoError> {
    let file_type = std::fs::symlink_metadata(path).map_err(via_error)?.file_type();
    std::result::Result::Ok(crate::std::via::FileType {
        is_file: file_type.is_file(),
        is_dir: file_type.is_dir(),
        is_symlink: file_type.is_symlink(),
    })
}

struct ViaWalkSettings {
    follow_links: bool,
    include_hidden: bool,
    max_depth: usize,
    mode: u8,
}

fn via_walk_entry(
    path: &std::path::Path,
    settings: &ViaWalkSettings,
) -> std::result::Result<Option<crate::std::via::DirEntry>, crate::std::via::IoError> {
    let metadata = std::fs::symlink_metadata(path).map_err(via_error)?;
    let mut is_dir = metadata.is_dir();
    let mut is_file = metadata.is_file();
    let mut is_symlink = metadata.file_type().is_symlink();
    if is_symlink && settings.follow_links {
        if let std::result::Result::Ok(resolved) = std::fs::metadata(path) {
            is_dir = resolved.is_dir();
            is_file = resolved.is_file();
            is_symlink = false;
        }
    }
    let keep = match settings.mode {
        1 => is_file,
        2 => is_dir,
        _ => true,
    };
    if !keep {
        return std::result::Result::Ok(None);
    }
    std::result::Result::Ok(Some(crate::std::via::DirEntry {
        path: path.to_string_lossy().into_owned(),
        file_name: path
            .file_name()
            .map(|name| name.to_string_lossy().into_owned())
            .unwrap_or_default(),
        is_dir,
        is_file,
        is_symlink,
        len: metadata.len(),
    }))
}

pub fn via_walk_with(
    root: &str,
    follow_links: bool,
    include_hidden: bool,
    max_depth: i32,
    mode: i32,
) -> std::result::Result<Vec<crate::std::via::DirEntry>, crate::std::via::IoError> {
    #[allow(clippy::cast_sign_loss)]
    let settings = ViaWalkSettings {
        follow_links,
        include_hidden,
        max_depth: usize::try_from(max_depth).unwrap_or(0),
        #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
        mode: (mode.clamp(0, 2)) as u8,
    };
    let root_path = std::path::PathBuf::from(root);
    let mut entries = Vec::new();
    if let Some(entry) = via_walk_entry(&root_path, &settings)? {
        entries.push(entry);
    }
    let mut stack = vec![(root_path, 0usize)];
    let mut visited = std::collections::BTreeSet::new();
    if let std::result::Result::Ok(canonical) = std::fs::canonicalize(root) {
        visited.insert(canonical);
    }
    while let Some((directory, depth)) = stack.pop() {
        if settings.max_depth != 0 && depth >= settings.max_depth {
            continue;
        }
        let Ok(reader) = std::fs::read_dir(&directory) else {
            continue;
        };
        let mut children: Vec<_> = reader.flatten().map(|entry| entry.path()).collect();
        children.sort();
        for child in children {
            let name = child.file_name().map(|name| name.to_string_lossy().into_owned());
            if !settings.include_hidden && name.as_deref().is_some_and(|name| name.starts_with('.')) {
                continue;
            }
            let metadata = std::fs::symlink_metadata(&child).map_err(via_error)?;
            let is_dir = if metadata.file_type().is_symlink() && settings.follow_links {
                std::fs::metadata(&child).is_ok_and(|resolved| resolved.is_dir())
            } else {
                metadata.is_dir()
            };
            if let Some(entry) = via_walk_entry(&child, &settings)? {
                entries.push(entry);
            }
            if is_dir {
                if settings.follow_links {
                    if let std::result::Result::Ok(canonical) = std::fs::canonicalize(&child) {
                        if !visited.insert(canonical) {
                            continue;
                        }
                    }
                }
                stack.push((child, depth + 1));
            }
        }
    }
    entries.sort_by(|left, right| left.path.cmp(&right.path));
    std::result::Result::Ok(entries)
}

// ---------------------------------------------------------------------------
// via: apertura configurable y E/S por cantidad.
// ---------------------------------------------------------------------------

pub fn via_file_open_with(
    path: &str,
    read: bool,
    write: bool,
    append: bool,
    create: bool,
    truncate: bool,
) -> std::result::Result<crate::std::via::File, crate::std::via::IoError> {
    let mut options = std::fs::OpenOptions::new();
    options
        .read(read)
        .write(write)
        .append(append)
        .create(create)
        .truncate(truncate);
    let file = options.open(path).map_err(via_error)?;
    let mut files = VIA_FILES.lock().unwrap_or_else(std::sync::PoisonError::into_inner);
    files.push(Some(file));
    #[allow(clippy::cast_possible_truncation)]
    let handle = (files.len() - 1) as u64;
    std::result::Result::Ok(crate::std::via::File { handle })
}

pub fn via_file_read_bytes(
    handle: u64,
    count: u64,
) -> std::result::Result<Vec<u8>, crate::std::via::IoError> {
    use std::io::Read;
    #[allow(clippy::cast_possible_truncation)]
    let mut buffer = vec![0u8; usize::try_from(count).unwrap_or(0)];
    let read = via_with_file(handle, |file| file.read(&mut buffer))?;
    buffer.truncate(read);
    std::result::Result::Ok(buffer)
}

pub fn via_file_write_bytes(
    handle: u64,
    bytes: Vec<u8>,
) -> std::result::Result<usize, crate::std::via::IoError> {
    use std::io::Write;
    via_with_file(handle, |file| file.write(&bytes))
}
