// Cabecera del runtime que acompaña al C++ generado.
//
// Se escribe en el directorio de compilación junto a los módulos.
// Es deliberadamente pequeña: solo cubre lo que el código generado
// necesita (formato, longitud, búsqueda, acceso seguro, pánico).

export const RUNTIME_HEADER = `// Runtime generado por pengu 0.1.0. No editar a mano.
#pragma once

#include <algorithm>
#include <array>
#include <cstdio>
#include <charconv>
#include <ctime>
#include <exception>
#include <atomic>
#include <bitset>
#include <complex>
#include <condition_variable>
#include <deque>
#include <forward_list>
#include <initializer_list>
#include <iomanip>
#include <iterator>
#include <list>
#include <mutex>
#include <queue>
#include <shared_mutex>
#include <stack>
#include <span>
#include <string_view>
#include <unordered_map>
#include <unordered_set>
#include <any>
#include <charconv>
#include <compare>
#include <chrono>
#include <cctype>
#include <cmath>
#include <limits>
#include <numeric>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <iostream>
#include <map>
#include <memory>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <filesystem>
#include <fstream>
#include <unistd.h>
#include <functional>
#include <numbers>
#include <random>
#include <thread>
#include <type_traits>
#include <utility>
#include <variant>
#include <vector>

namespace pengu {

// ---- hash combinado -------------------------------------------------------
//
// Las runes no declaran un hash: el compilador sintetiza std::hash<Rune>
// combinando los campos. Estas sobrecargas cubren los tipos compuestos que
// std::hash no trae de serie.

inline std::string join_parts(std::initializer_list<std::string> parts) {
  std::string text;
  for (const auto& part : parts) text += part;
  return text;
}

inline void hash_combine(std::size_t& seed, std::size_t value) {
  seed ^= value + 0x9e3779b97f4a7c15ULL + (seed << 6) + (seed >> 2);
}

template <class T>
inline void hash_combine(std::size_t& seed, const T& value) {
  hash_combine(seed, std::hash<T>{}(value));
}

template <class A, class B>
inline void hash_combine(std::size_t& seed, const std::pair<A, B>& value) {
  hash_combine(seed, value.first);
  hash_combine(seed, value.second);
}

template <class... Ts>
inline void hash_combine(std::size_t& seed, const std::tuple<Ts...>& value) {
  std::apply([&seed](const auto&... item) { (hash_combine(seed, item), ...); }, value);
}

template <class T>
inline void hash_combine(std::size_t& seed, const std::optional<T>& value) {
  hash_combine(seed, value.has_value());
  if (value.has_value()) hash_combine(seed, *value);
}

struct Range {
  long long first;
  long long last;
  bool inclusive;

  struct iterator {
    long long value;
    long long last;
    long long step;
    bool inclusive;

    long long operator*() const { return value; }
    iterator& operator++() { value += step; return *this; }
    bool operator!=(const iterator&) const {
      return inclusive ? (step > 0 ? value <= last : value >= last)
                       : (step > 0 ? value < last : value > last);
    }

    using iterator_category = std::input_iterator_tag;
    using value_type = long long;
    using difference_type = long long;
    using pointer = const long long*;
    using reference = long long;
  };

  // Largo del rango: «#(1..10)» es 10 y «#(1..<10)» es 9.
  std::size_t size() const {
    if (last < first) return 0;
    const long long total = last - first;
    return static_cast<std::size_t>(inclusive ? total + 1 : total);
  }

  iterator begin() const {
    return iterator{first, last, first <= last ? 1 : -1, inclusive};
  }

  iterator end() const {
    return iterator{last, last, first <= last ? 1 : -1, inclusive};
  }
};

inline std::string to_string(const std::string& value) { return value; }
inline std::string to_string(const char* value) { return std::string(value); }
inline std::string to_string(char value) { return std::string(1, value); }
inline char char_upper(char value) {
  return static_cast<char>(std::toupper(static_cast<unsigned char>(value)));
}
inline char char_lower(char value) {
  return static_cast<char>(std::tolower(static_cast<unsigned char>(value)));
}
// «int8_t»/«uint8_t» son «signed char»/«unsigned char»: sin estas sobrecargas
// el operador de flujo los imprimiría como caracteres.
inline std::string to_string(std::int8_t value) { return std::to_string(static_cast<int>(value)); }
inline std::string to_string(std::uint8_t value) {
  return std::to_string(static_cast<unsigned int>(value));
}
inline std::string to_string(bool value) { return value ? "true" : "false"; }

// Cadenas anchas: se reducen a UTF-8 aproximado (byte a byte) para
// poder imprimirlas. La conversión completa es trabajo de std/.
inline std::string to_string(const std::wstring& value) { return std::string(value.begin(), value.end()); }
inline std::string to_string(const std::u8string& value) {
  return std::string(reinterpret_cast<const char*>(value.data()), value.size());
}
inline std::string to_string(const std::u16string& value) {
  std::string out;
  for (char16_t unit : value) out.push_back(static_cast<char>(unit));
  return out;
}
inline std::string to_string(const std::u32string& value) {
  std::string out;
  for (char32_t unit : value) out.push_back(static_cast<char>(unit));
  return out;
}
inline std::string to_string(std::string_view value) { return std::string(value); }

template <class T>
  requires std::is_arithmetic_v<T>
std::string to_string(T value) {
  std::ostringstream out;
  out << value;
  return out.str();
}

// Un rune con «to_string» implementa Display: su propio método manda.
template <class T>
  requires requires(const T& value) { value.to_string(); }
std::string to_string(const T& value) {
  return value.to_string();
}

// Declaraciones adelantadas: las sobrecargas de contenedores pueden
// necesitar imprimir un Value (por ejemplo vector de Value).
class Value;
std::string to_string(const Value& item);

// Resultado de comparar dos valores con <=>. Envuelve los tres tipos
// de orden de C++20 en un valor con la API del lenguaje.
class Ordering {
 public:
  constexpr Ordering() = default;
  // Implícito a propósito: «a <=> b» produce std::*_ordering y el
  // retorno declarado de un operador del usuario es Ordering.
  constexpr Ordering(std::partial_ordering value) : value_(value) {}

  static const Ordering Less;
  static const Ordering Equal;
  static const Ordering Greater;

  bool is_lt() const { return value_ < 0; }
  bool is_eq() const { return value_ == 0; }
  bool is_gt() const { return value_ > 0; }

  Ordering reverse() const {
    if (is_lt()) return Greater;
    if (is_gt()) return Less;
    return Equal;
  }

  std::partial_ordering raw() const { return value_; }

 private:
  std::partial_ordering value_ = std::partial_ordering::equivalent;
};

inline constexpr Ordering Ordering::Less = Ordering(std::partial_ordering::less);
inline constexpr Ordering Ordering::Equal = Ordering(std::partial_ordering::equivalent);
inline constexpr Ordering Ordering::Greater = Ordering(std::partial_ordering::greater);

inline bool operator==(Ordering left, Ordering right) {
  return left.raw() == right.raw();
}

inline bool operator!=(Ordering left, Ordering right) {
  return !(left == right);
}

inline std::string to_string(Ordering value) {
  if (value.is_lt()) return "less";
  if (value.is_gt()) return "greater";
  return "equal";
}

template <class A, class B>
Ordering compare(const A& left, const B& right) {
  auto result = left <=> right;
  if (result < 0) return Ordering::Less;
  if (result > 0) return Ordering::Greater;
  return Ordering::Equal;
}

template <class T>
  requires std::is_enum_v<T>
std::string to_string(T value) {
  return std::to_string(static_cast<long long>(value));
}

template <class T>
std::string to_string(const std::optional<T>& value) {
  return value ? to_string(*value) : "none";
}

template <class T>
std::string to_string(const std::vector<T>& value) {
  std::string out = "[";
  bool first = true;
  for (const auto& item : value) {
    if (!first) out += ", ";
    first = false;
    out += to_string(item);
  }
  out += "]";
  return out;
}

template <class T>
std::string to_string(const std::set<T>& value) {
  std::string out = "{";
  bool first = true;
  for (const auto& item : value) {
    if (!first) out += ", ";
    first = false;
    out += to_string(item);
  }
  out += "}";
  return out;
}

template <class K, class V>
std::string to_string(const std::map<K, V>& value) {
  std::string out = "{";
  bool first = true;
  for (const auto& [key, item] : value) {
    if (!first) out += ", ";
    first = false;
    out += to_string(key) + ": " + to_string(item);
  }
  out += "}";
  return out;
}

template <class... Ts>
std::string to_string(const std::tuple<Ts...>& value) {
  std::string out = "(";
  bool first = true;
  std::apply(
      [&](const auto&... item) {
        ((out += (first ? "" : ", "), out += to_string(item), first = false), ...);
      },
      value);
  out += ")";
  return out;
}

template <class A, class B>
std::string to_string(const std::pair<A, B>& value) {
  return "(" + to_string(value.first) + ", " + to_string(value.second) + ")";
}

// Renderiza un valor para Display: usa su método to_string() si lo
// tiene y, si no, la sobrecarga libre de to_string.
template <class T>
std::string to_string_value(const T& value) {
  if constexpr (requires { value.to_string(); }) {
    return value.to_string();
  } else {
    return to_string(value);
  }
}

// Caja heterogénea para las variádicas any.
class Value {
 public:
  Value() = default;

  template <class T>
  explicit Value(T value) : render_([value]() { return to_string_value(value); }) {}

  std::string render() const { return render_ ? render_() : std::string(); }

 private:
  std::function<std::string()> render_;
};

template <class T>
Value value(T item) {
  return Value(item);
}

inline std::string to_string(const Value& item) { return item.render(); }

template <class... Ts>
void println(const Ts&... values) {
  std::string out;
  ((out += to_string(values)), ...);
  std::cout << out << '\\n';
}

template <class T>
void print(const T& value) {
  std::cout << to_string(value);
}

template <class... Ts>
std::string format_all(const Ts&... values) {
  std::string out;
  ((out += to_string(values)), ...);
  return out;
}

template <class... Ts>
void eprintln(const Ts&... values) {
  std::string out;
  ((out += to_string(values)), ...);
  std::cerr << out << '\\n';
}

template <class T>
void eprint(const T& value) {
  std::cerr << to_string(value);
}

inline std::string read_line() {
  std::string line;
  std::getline(std::cin, line);
  return line;
}

template <class... Ts>
void log_line(const char* level, const Ts&... values) {
  std::string out;
  ((out += to_string(values)), ...);
  std::cerr << '[' << level << "] " << out << '\\n';
}

template <class... Ts>
void log_debug(const Ts&... values) { log_line("debug", values...); }
template <class... Ts>
void log_info(const Ts&... values) { log_line("info", values...); }
template <class... Ts>
void log_warn(const Ts&... values) { log_line("warn", values...); }
template <class... Ts>
void log_error(const Ts&... values) { log_line("error", values...); }

// --- Argumentos del programa ----------------------------------------------

inline std::vector<std::string>& arg_list() {
  static std::vector<std::string> list;
  return list;
}

inline void set_args(int argc, char** argv) {
  auto& list = arg_list();
  list.clear();
  for (int index = 0; index < argc; index++) list.emplace_back(argv[index]);
}

inline std::vector<std::string> os_args() {
  return arg_list();
}

template <class C>
std::size_t len(const C& container) {
  if constexpr (requires { container.size(); }) {
    return static_cast<std::size_t>(container.size());
  } else {
    return static_cast<std::size_t>(std::distance(container.begin(), container.end()));
  }
}

// «x in 1..10»: el rango no tiene find, así que se compara el elemento.
template <class T>
bool contains(const Range& range, const T& value) {
  const auto target = static_cast<long long>(value);
  if (target < range.first) return false;
  if (range.inclusive ? target > range.last : target >= range.last) return false;
  return true;
}

inline bool contains(const std::string& text, const std::string& needle) {
  return text.find(needle) != std::string::npos;
}

// Intrínsecos de std/string: devuelven el largo cuando no encuentran, para
// que PenguScript pueda convertirlo en «none».
inline std::size_t find_raw(const std::string& text, const std::string& needle) {
  const auto position = text.find(needle);
  return position == std::string::npos ? text.size() : position;
}

inline std::string trim_raw(const std::string& text) {
  std::size_t first = 0;
  std::size_t last = text.size();
  while (first < last && std::isspace(static_cast<unsigned char>(text[first])) != 0) ++first;
  while (last > first && std::isspace(static_cast<unsigned char>(text[last - 1])) != 0) --last;
  return text.substr(first, last - first);
}

inline std::string to_upper_raw(const std::string& text) {
  std::string out = text;
  for (char& letter : out) letter = static_cast<char>(std::toupper(static_cast<unsigned char>(letter)));
  return out;
}

inline std::string to_lower_raw(const std::string& text) {
  std::string out = text;
  for (char& letter : out) letter = static_cast<char>(std::tolower(static_cast<unsigned char>(letter)));
  return out;
}

inline std::size_t rfind_raw(const std::string& text, const std::string& needle) {
  const auto position = text.rfind(needle);
  return position == std::string::npos ? text.size() : position;
}

inline std::size_t find_from_raw(const std::string& text, const std::string& needle, std::size_t from) {
  if (from >= text.size()) return text.size();
  const auto position = text.find(needle, from);
  return position == std::string::npos ? text.size() : position;
}

inline std::string replace_first_raw(const std::string& text, const std::string& from, const std::string& to) {
  if (from.empty()) return text;
  const auto position = text.find(from);
  if (position == std::string::npos) return text;
  return text.substr(0, position) + to + text.substr(position + from.size());
}

inline std::vector<std::string> split_whitespace_raw(const std::string& text) {
  std::vector<std::string> parts;
  std::size_t index = 0;
  while (index < text.size()) {
    while (index < text.size() && std::isspace(static_cast<unsigned char>(text[index])) != 0) ++index;
    const std::size_t start = index;
    while (index < text.size() && std::isspace(static_cast<unsigned char>(text[index])) == 0) ++index;
    if (index > start) parts.push_back(text.substr(start, index - start));
  }
  return parts;
}

// Cuenta puntos de codigo UTF-8: los bytes de continuacion empiezan por 10xxxxxx.
inline std::size_t char_count_raw(const std::string& text) {
  std::size_t total = 0;
  for (const char letter : text) {
    if ((static_cast<unsigned char>(letter) & 0xC0) != 0x80) ++total;
  }
  return total;
}

// Invierte por puntos de codigo, para no romper secuencias UTF-8.
inline std::string reverse_raw(const std::string& text) {
  std::vector<std::string> letters;
  std::size_t index = 0;
  while (index < text.size()) {
    std::size_t length = 1;
    const unsigned char lead = static_cast<unsigned char>(text[index]);
    if ((lead & 0xF8) == 0xF0) length = 4;
    else if ((lead & 0xF0) == 0xE0) length = 3;
    else if ((lead & 0xE0) == 0xC0) length = 2;
    if (index + length > text.size()) length = 1;
    letters.push_back(text.substr(index, length));
    index += length;
  }
  std::string out;
  for (auto it = letters.rbegin(); it != letters.rend(); ++it) out += *it;
  return out;
}

inline std::optional<std::int64_t> parse_int_raw(const std::string& text) {
  if (text.empty()) return std::nullopt;
  std::int64_t value = 0;
  const auto result = std::from_chars(text.data(), text.data() + text.size(), value);
  if (result.ec != std::errc{} || result.ptr != text.data() + text.size()) return std::nullopt;
  return value;
}

inline std::optional<double> parse_double_raw(const std::string& text) {
  if (text.empty()) return std::nullopt;
  double value = 0.0;
  const auto result = std::from_chars(text.data(), text.data() + text.size(), value);
  if (result.ec != std::errc{} || result.ptr != text.data() + text.size()) return std::nullopt;
  return value;
}

inline std::vector<std::uint8_t> bytes_raw(const std::string& text) {
  std::vector<std::uint8_t> out;
  out.reserve(text.size());
  for (const char letter : text) out.push_back(static_cast<std::uint8_t>(letter));
  return out;
}

// format::template: sustituye cada «{}» por el siguiente valor.
inline std::string template_values(const std::string& text, const std::vector<Value>& values) {
  std::string out;
  std::size_t index = 0;
  std::size_t next = 0;
  while (index < text.size()) {
    if (index + 1 < text.size() && text[index] == '{' && text[index + 1] == '}') {
      if (next < values.size()) out += values[next++].render();
      index += 2;
      continue;
    }
    out += text[index];
    ++index;
  }
  return out;
}

inline int log_severity(const std::string& name) {
  if (name == "debug") return 0;
  if (name == "info") return 1;
  if (name == "warn") return 2;
  if (name == "error") return 3;
  return 1;
}

inline int& log_threshold() {
  static int level = 1;
  return level;
}

inline bool& log_timestamped() {
  static bool enabled = false;
  return enabled;
}

inline void set_log_level_raw(const std::string& name) { log_threshold() = log_severity(name); }

inline std::string log_level_raw() {
  static const char* names[] = {"debug", "info", "warn", "error"};
  const int level = log_threshold();
  return names[level < 0 ? 0 : (level > 3 ? 3 : level)];
}

inline bool log_enabled_raw(const std::string& name) { return log_severity(name) >= log_threshold(); }

inline void log_timestamped_raw(bool enabled) { log_timestamped() = enabled; }

inline std::string log_stamp() {
  const std::time_t now = std::time(nullptr);
  std::tm local{};
  localtime_r(&now, &local);
  char buffer[16] = {0};
  std::strftime(buffer, sizeof(buffer), "%H:%M:%S", &local);
  return buffer;
}

inline std::vector<std::string> split_raw(const std::string& text, const std::string& separator) {
  std::vector<std::string> parts;
  if (separator.empty()) {
    for (const char letter : text) parts.emplace_back(1, letter);
    return parts;
  }
  std::size_t start = 0;
  while (true) {
    const auto position = text.find(separator, start);
    if (position == std::string::npos) {
      parts.push_back(text.substr(start));
      return parts;
    }
    parts.push_back(text.substr(start, position - start));
    start = position + separator.size();
  }
}

template <class C, class V>
bool contains(const C& container, const V& value) {
  if constexpr (requires { container.find(value) != container.end(); }) {
    return container.find(value) != container.end();
  } else {
    return std::find(container.begin(), container.end(), value) != container.end();
  }
}

template <class C>
auto& vec_at(C& container, std::size_t index) {
  if (index >= container.size()) {
    throw std::runtime_error("índice " + std::to_string(index) + " fuera de rango (tamaño " +
                             std::to_string(container.size()) + ")");
  }
  return container[index];
}

template <class C>
const auto& vec_at(const C& container, std::size_t index) {
  if (index >= container.size()) {
    throw std::runtime_error("índice " + std::to_string(index) + " fuera de rango (tamaño " +
                             std::to_string(container.size()) + ")");
  }
  return container[index];
}

template <class M>
auto& map_at(M& map, const typename M::key_type& key) {
  auto it = map.find(key);
  if (it == map.end()) throw std::runtime_error("no existe la clave en el mapa");
  return it->second;
}

template <class M>
const auto& map_at(const M& map, const typename M::key_type& key) {
  auto it = map.find(key);
  if (it == map.end()) throw std::runtime_error("no existe la clave en el mapa");
  return it->second;
}

// --- Acceso seguro a contenedores -----------------------------------------

template <class C>
auto get_at(const C& container, std::size_t index) -> std::optional<typename C::value_type> {
  if (index >= container.size()) return std::nullopt;
  return container[index];
}

template <class M>
auto map_get(const M& map, const typename M::key_type& key) -> std::optional<typename M::mapped_type> {
  auto it = map.find(key);
  if (it == map.end()) return std::nullopt;
  return it->second;
}

template <class M>
auto map_get_or(const M& map, const typename M::key_type& key, typename M::mapped_type fallback)
    -> typename M::mapped_type {
  auto it = map.find(key);
  return it == map.end() ? fallback : it->second;
}

template <class M>
auto map_extract(M& map, const typename M::key_type& key) -> std::optional<typename M::mapped_type> {
  auto it = map.find(key);
  if (it == map.end()) return std::nullopt;
  auto value = it->second;
  map.erase(it);
  return value;
}

template <class M>
bool map_insert(M& map, const typename M::key_type& key, const typename M::mapped_type& value) {
  return map.insert({key, value}).second;
}

template <class S>
bool set_insert(S& set, const typename S::value_type& value) {
  return set.insert(value).second;
}

template <class C>
auto pop_opt(C& container) -> std::optional<typename C::value_type> {
  if (container.empty()) return std::nullopt;
  auto value = container.back();
  container.pop_back();
  return value;
}

// pop() promete devolver el elemento y panica si el contenedor está vacío.
template <class C>
auto pop_back_checked(C& container) -> typename C::value_type {
  if (container.empty()) throw std::runtime_error("pop() sobre un contenedor vacío");
  auto value = container.back();
  container.pop_back();
  return value;
}

// remove_at(i) devuelve el elemento borrado; el índice se comprueba.
template <class C>
auto erase_at(C& container, std::size_t index) -> typename C::value_type {
  if (index >= container.size()) {
    throw std::runtime_error("índice " + std::to_string(index) + " fuera de rango (tamaño " +
                             std::to_string(container.size()) + ")");
  }
  auto value = container[index];
  container.erase(std::next(container.begin(), static_cast<std::ptrdiff_t>(index)));
  return value;
}

template <class C, class V>
void insert_at(C& container, std::size_t index, const V& value) {
  if (index > container.size()) {
    throw std::runtime_error("no se puede insertar en la posición " + std::to_string(index) +
                             " (tamaño " + std::to_string(container.size()) + ")");
  }
  container.insert(std::next(container.begin(), static_cast<std::ptrdiff_t>(index)), value);
}

// pop_front() para deque/list: devuelve el elemento y comprueba que haya.
template <class C>
auto pop_front_checked(C& container) -> typename C::value_type {
  if (container.empty()) throw std::runtime_error("pop_front() sobre un contenedor vacío");
  auto value = container.front();
  container.pop_front();
  return value;
}

// pop() de stack/queue/priority_queue: C++ lo devuelve void, así que se lee
// el elemento antes de quitarlo.
template <class A>
auto adapter_pop(A& container) -> typename A::value_type {
  if (container.empty()) throw std::runtime_error("pop() sobre un contenedor vacío");
  auto value = [&container]() -> typename A::value_type {
    if constexpr (requires { container.top(); }) {
      return container.top();
    } else {
      return container.front();
    }
  }();
  container.pop();
  return value;
}

template <class A>
void adapter_clear(A& container) {
  while (!container.empty()) container.pop();
}

// sum() y product() de una secuencia: el elemento decide la aritmética.
template <class C>
auto sum_of(const C& container) -> typename C::value_type {
  typename C::value_type total{};
  for (const auto& value : container) total += value;
  return total;
}

template <class C>
auto product_of(const C& container) -> typename C::value_type {
  typename C::value_type total{1};
  for (const auto& value : container) total *= value;
  return total;
}

template <class C, class V>
bool remove_value(C& container, const V& value) {
  auto found = std::find(container.begin(), container.end(), value);
  if (found == container.end()) return false;
  container.erase(found);
  return true;
}

template <class S, class V>
bool remove_from_set(S& set, const V& value) {
  return set.erase(value) > 0;
}

template <class M>
bool map_assign(M& map, const typename M::key_type& key, const typename M::mapped_type& value) {
  return map.insert_or_assign(key, value).second;
}

template <class M>
std::vector<typename M::key_type> map_keys(const M& map) {
  std::vector<typename M::key_type> keys;
  keys.reserve(map.size());
  for (const auto& entry : map) keys.push_back(entry.first);
  return keys;
}

template <class M>
std::vector<typename M::mapped_type> map_values(const M& map) {
  std::vector<typename M::mapped_type> values;
  values.reserve(map.size());
  for (const auto& entry : map) values.push_back(entry.second);
  return values;
}

// find de string devuelve optional<size_t>: npos es un detalle de C++.
inline std::optional<std::size_t> find_opt(const std::string& text, const std::string& needle,
                                           std::size_t from = 0) {
  if (from > text.size()) return std::nullopt;
  const auto found = text.find(needle, from);
  if (found == std::string::npos) return std::nullopt;
  return found;
}

// --- Formato numérico ------------------------------------------------------

inline std::string to_fixed(double value, int decimals) {
  std::ostringstream out;
  out << std::fixed << std::setprecision(decimals < 0 ? 0 : decimals) << value;
  return out.str();
}

inline std::string to_scientific(double value, int decimals) {
  std::ostringstream out;
  out << std::scientific << std::setprecision(decimals < 0 ? 0 : decimals) << value;
  return out.str();
}

// Las sobrecargas de «long double» reutilizan la implementación de «double».
inline std::string to_fixed(long double value, int decimals) { return to_fixed(static_cast<double>(value), decimals); }
inline std::string to_scientific(long double value, int decimals) { return to_scientific(static_cast<double>(value), decimals); }

inline std::string to_radix(std::int64_t value, int base) {
  if (base < 2 || base > 36) throw std::runtime_error("base fuera de rango (2..36)");
  if (value == 0) return "0";
  static const char* digits = "0123456789abcdefghijklmnopqrstuvwxyz";
  const bool negative = value < 0;
  const std::uint64_t magnitude = negative
      ? static_cast<std::uint64_t>(-(value + 1)) + 1u
      : static_cast<std::uint64_t>(value);
  std::string out;
  for (std::uint64_t rest = magnitude; rest > 0; rest /= static_cast<std::uint64_t>(base)) {
    out.push_back(digits[rest % static_cast<std::uint64_t>(base)]);
  }
  if (negative) out.push_back('-');
  std::reverse(out.begin(), out.end());
  return out;
}

// --- Punteros débiles ------------------------------------------------------

template <class T>
std::optional<std::shared_ptr<T>> lock_weak(const std::weak_ptr<T>& pointer) {
  auto locked = pointer.lock();
  if (!locked) return std::nullopt;
  return locked;
}

[[noreturn]] inline void panic(const std::string& message);

// --- Sistema de archivos ---------------------------------------------------

inline std::optional<std::string> read_file(const std::string& path) {
  std::ifstream input(path, std::ios::binary);
  if (!input) return std::nullopt;
  std::ostringstream buffer;
  buffer << input.rdbuf();
  return buffer.str();
}

inline bool write_file(const std::string& path, const std::string& contents) {
  std::ofstream output(path, std::ios::binary);
  if (!output) return false;
  output << contents;
  return static_cast<bool>(output);
}

inline bool path_exists(const std::string& path) {
  std::error_code error;
  return std::filesystem::exists(path, error);
}

inline bool path_is_dir(const std::string& path) {
  std::error_code error;
  return std::filesystem::is_directory(path, error);
}

inline bool path_remove(const std::string& path) {
  std::error_code error;
  return std::filesystem::remove_all(path, error) > 0;
}

inline bool create_dir(const std::string& path) {
  std::error_code error;
  std::filesystem::create_directories(path, error);
  return !error;
}

inline bool append_file(const std::string& path, const std::string& contents) {
  std::ofstream output(path, std::ios::binary | std::ios::app);
  if (!output) return false;
  output << contents;
  return static_cast<bool>(output);
}

inline std::optional<std::vector<std::uint8_t>> read_bytes(const std::string& path) {
  std::ifstream input(path, std::ios::binary);
  if (!input) return std::nullopt;
  std::vector<std::uint8_t> out;
  char byte = 0;
  while (input.get(byte)) out.push_back(static_cast<std::uint8_t>(byte));
  return out;
}

inline bool write_bytes(const std::string& path, const std::vector<std::uint8_t>& bytes) {
  std::ofstream output(path, std::ios::binary);
  if (!output) return false;
  for (const std::uint8_t byte : bytes) output.put(static_cast<char>(byte));
  return static_cast<bool>(output);
}

inline bool path_is_file(const std::string& path) {
  std::error_code error;
  return std::filesystem::is_regular_file(path, error);
}

inline std::vector<std::string> list_dir(const std::string& path) {
  std::vector<std::string> out;
  std::error_code error;
  for (const auto& entry : std::filesystem::directory_iterator(path, error)) {
    out.push_back(entry.path().filename().string());
  }
  std::sort(out.begin(), out.end());
  return out;
}

inline std::optional<std::int64_t> file_size(const std::string& path) {
  std::error_code error;
  const auto size = std::filesystem::file_size(path, error);
  if (error) return std::nullopt;
  return static_cast<std::int64_t>(size);
}

inline bool rename_path(const std::string& from, const std::string& to) {
  std::error_code error;
  std::filesystem::rename(from, to, error);
  return !error;
}

inline bool copy_path(const std::string& from, const std::string& to) {
  std::error_code error;
  std::filesystem::copy(
      from,
      to,
      std::filesystem::copy_options::recursive | std::filesystem::copy_options::overwrite_existing,
      error);
  return !error;
}

inline std::optional<std::string> canonical_path(const std::string& path) {
  std::error_code error;
  const auto result = std::filesystem::weakly_canonical(path, error);
  if (error) return std::nullopt;
  return result.string();
}

// --- Tiempo, entorno y azar ------------------------------------------------

inline long long now_millis() {
  using namespace std::chrono;
  return duration_cast<milliseconds>(system_clock::now().time_since_epoch()).count();
}

inline long long now_seconds() {
  return now_millis() / 1000;
}

inline void sleep_millis(long long millis) {
  std::this_thread::sleep_for(std::chrono::milliseconds(millis));
}

inline std::optional<std::string> get_env(const std::string& name) {
  const char* value = std::getenv(name.c_str());
  if (value == nullptr) return std::nullopt;
  return std::string(value);
}

inline std::mt19937& random_engine() {
  static std::mt19937 engine(std::random_device{}());
  return engine;
}

// Baraja y elige sobre cualquier contenedor secuencial: la plantilla deduce
// el tipo del elemento, así que vale para «vector<T>» con cualquier «T».
template <typename C>
inline void shuffle_values(C& values) {
  std::shuffle(values.begin(), values.end(), random_engine());
}

template <typename C>
inline std::optional<typename C::value_type> choose_value(const C& values) {
  if (values.empty()) return std::nullopt;
  std::uniform_int_distribution<std::size_t> distribution(0, values.size() - 1);
  return values[distribution(random_engine())];
}

inline long long random_int(long long min, long long max) {
  if (max < min) std::swap(min, max);
  std::uniform_int_distribution<long long> distribution(min, max);
  return distribution(random_engine());
}

// «math::infinite()» y «math::not_a_number()» no pueden ser constantes
// const-evaluables, así que se exponen como funciones del runtime.
inline double infinite_double() { return std::numeric_limits<double>::infinity(); }
inline double nan_double() { return std::numeric_limits<double>::quiet_NaN(); }

inline double random_float() {
  std::uniform_real_distribution<double> distribution(0.0, 1.0);
  return distribution(random_engine());
}

inline bool random_bool() {
  std::uniform_int_distribution<int> distribution(0, 1);
  return distribution(random_engine()) == 1;
}

inline void seed_random(std::int64_t seed) {
  random_engine().seed(static_cast<std::mt19937::result_type>(seed));
}

inline long long random_range(double min, double max) {
  if (max < min) std::swap(min, max);
  std::uniform_real_distribution<double> distribution(min, max);
  return static_cast<long long>(distribution(random_engine()));
}

inline double random_real(double min, double max) {
  if (max < min) std::swap(min, max);
  std::uniform_real_distribution<double> distribution(min, max);
  return distribution(random_engine());
}

// --- Reloj (F4) ------------------------------------------------------------

inline std::int64_t now_nanos() {
  using namespace std::chrono;
  return duration_cast<nanoseconds>(system_clock::now().time_since_epoch()).count();
}

inline std::int64_t monotonic_millis() {
  using namespace std::chrono;
  return duration_cast<milliseconds>(steady_clock::now().time_since_epoch()).count();
}

inline std::int64_t monotonic_nanos() {
  using namespace std::chrono;
  return duration_cast<nanoseconds>(steady_clock::now().time_since_epoch()).count();
}

// Año, mes, día, hora, minuto y segundo locales de un instante.
inline std::vector<std::int64_t> time_parts(std::int64_t millis) {
  const std::time_t seconds = static_cast<std::time_t>(millis / 1000);
  std::tm local{};
  localtime_r(&seconds, &local);
  return {
      static_cast<std::int64_t>(local.tm_year + 1900),
      static_cast<std::int64_t>(local.tm_mon + 1),
      static_cast<std::int64_t>(local.tm_mday),
      static_cast<std::int64_t>(local.tm_hour),
      static_cast<std::int64_t>(local.tm_min),
      static_cast<std::int64_t>(local.tm_sec),
  };
}

inline std::string format_datetime(std::int64_t millis) {
  const auto parts = time_parts(millis);
  std::ostringstream out;
  out << std::setfill('0') << std::setw(4) << parts[0] << '-' << std::setw(2) << parts[1] << '-'
      << std::setw(2) << parts[2] << ' ' << std::setw(2) << parts[3] << ':' << std::setw(2)
      << parts[4] << ':' << std::setw(2) << parts[5];
  return out.str();
}

// --- Entorno y proceso (F4) ------------------------------------------------

inline bool set_env(const std::string& name, const std::string& value) {
  return ::setenv(name.c_str(), value.c_str(), 1) == 0;
}

inline std::int64_t process_id() { return static_cast<std::int64_t>(::getpid()); }

inline std::optional<std::string> home_dir() {
  const char* value = std::getenv("HOME");
  if (value == nullptr) return std::nullopt;
  return std::string(value);
}

inline std::optional<std::string> temp_dir() {
  std::error_code error;
  const auto result = std::filesystem::temp_directory_path(error);
  if (error) return std::nullopt;
  return result.string();
}

inline std::optional<std::string> current_dir() {
  std::error_code error;
  const auto result = std::filesystem::current_path(error);
  if (error) return std::nullopt;
  return result.string();
}

inline std::string platform_name() {
#if defined(_WIN32)
  return "windows";
#elif defined(__APPLE__)
  return "macos";
#else
  return "linux";
#endif
}

inline std::string arch_name() {
#if defined(__x86_64__) || defined(_M_X64)
  return "x86_64";
#elif defined(__aarch64__) || defined(_M_ARM64)
  return "aarch64";
#else
  return "desconocida";
#endif
}

inline std::int64_t cpu_count() {
  return static_cast<std::int64_t>(std::thread::hardware_concurrency());
}

// --- Entrada y salida (F4) -------------------------------------------------

inline std::string read_all_stdin() {
  std::ostringstream buffer;
  buffer << std::cin.rdbuf();
  return buffer.str();
}

inline void flush_stdout() { std::cout.flush(); }

inline bool stdin_is_terminal() { return ::isatty(0) == 1; }

inline std::optional<char> read_char() {
  char letter = 0;
  if (!std::cin.get(letter)) return std::nullopt;
  return letter;
}

inline void assert_that(bool condition) {
  if (!condition) ::pengu::panic("aserción fallida");
}

// --- Conversión de omens ---------------------------------------------------

template <class E, class I>
std::optional<E> try_from(I value) {
  return static_cast<E>(value);
}

template <class E, class I>
E from(I value) {
  return static_cast<E>(value);
}

[[noreturn]] inline void panic(const std::string& message) {
  throw std::runtime_error(message);
}

// T::try_from(x): comprobación de rango en tiempo de ejecución.
template <class T>
std::optional<T> try_from_int(long long value) {
  if constexpr (std::is_same_v<T, bool>) {
    return value != 0;
  } else if constexpr (std::is_integral_v<T>) {
    // El destino puede ser de 64 bits sin signo: comparar siempre en el
    // dominio de «long long» desbordaría al convertir «T::max()».
    if constexpr (std::is_signed_v<T>) {
      const auto lowest = static_cast<long long>(std::numeric_limits<T>::lowest());
      const auto highest = static_cast<long long>(std::numeric_limits<T>::max());
      if (value < lowest || value > highest) return std::nullopt;
    } else {
      if (value < 0) return std::nullopt;
      const auto highest = static_cast<unsigned long long>(std::numeric_limits<T>::max());
      if (static_cast<unsigned long long>(value) > highest) return std::nullopt;
    }
    return static_cast<T>(value);
  } else {
    return static_cast<T>(value);
  }
}

template <class T>
std::optional<T> try_from_double(double value) {
  if (std::isnan(value) || std::isinf(value)) return std::nullopt;
  if constexpr (std::is_integral_v<T>) {
    if (value < static_cast<double>(std::numeric_limits<T>::lowest())) return std::nullopt;
    if (value > static_cast<double>(std::numeric_limits<T>::max())) return std::nullopt;
    return static_cast<T>(value);
  } else {
    if (value < static_cast<double>(std::numeric_limits<T>::lowest())) return std::nullopt;
    if (value > static_cast<double>(std::numeric_limits<T>::max())) return std::nullopt;
    return static_cast<T>(value);
  }
}

template <class T>
std::optional<T> try_parse(const std::string& text) {
  if (text.empty()) return std::nullopt;
  if constexpr (std::is_integral_v<T>) {
    T value{};
    const char* first = text.data();
    const char* last = first + text.size();
    const auto result = std::from_chars(first, last, value);
    if (result.ec != std::errc{} || result.ptr != last) return std::nullopt;
    return value;
  } else {
    try {
      std::size_t used = 0;
      const double value = std::stod(text, &used);
      if (used != text.size()) return std::nullopt;
      return try_from_double<T>(value);
    } catch (const std::exception&) {
      return std::nullopt;
    }
  }
}

template <class T>
void append(std::vector<T>& target, const std::vector<T>& more) {
  target.insert(target.end(), more.begin(), more.end());
}

inline void write_values(const std::vector<Value>& values, bool newline) {
  for (const Value& item : values) std::cout << item.render();
  if (newline) std::cout << '\\n';
}

inline void eprint_values(const std::vector<Value>& values, bool newline) {
  for (const Value& item : values) std::cerr << item.render();
  if (newline) std::cerr << '\\n';
}

inline std::string format_values(const std::vector<Value>& values) {
  std::string text;
  for (const Value& item : values) text += item.render();
  return text;
}

inline void log_values(const std::string& level, const std::vector<Value>& values) {
  if (!log_enabled_raw(level)) return;
  std::cerr << "[" << level << "] ";
  if (log_timestamped()) std::cerr << "[" << log_stamp() << "] ";
  std::cerr << format_values(values) << '\\n';
}

template <class T>
T or_panic(std::optional<T> value, const std::string& message) {
  if (!value.has_value()) panic(message);
  return *value;
}

template <class F>
constexpr bool has(F flags, F bit) {
  return (static_cast<std::uint64_t>(flags) & static_cast<std::uint64_t>(bit)) != 0;
}

}  // namespace pengu
`;
