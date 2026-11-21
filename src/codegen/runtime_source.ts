// Cabecera del runtime que acompaña al C++ generado.
//
// Se escribe en el directorio de compilación junto a los módulos.
// Es deliberadamente pequeña: solo cubre lo que el código generado
// necesita (formato, longitud, búsqueda, acceso seguro, pánico).

export const RUNTIME_HEADER = `// Runtime generado por pengu 0.1.0. No editar a mano.
#pragma once

#include <algorithm>
#include <array>
#include <atomic>
#include <bitset>
#include <complex>
#include <condition_variable>
#include <deque>
#include <forward_list>
#include <initializer_list>
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
#include <chrono>
#include <cmath>
#include <limits>
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
#include <functional>
#include <numbers>
#include <random>
#include <thread>
#include <type_traits>
#include <utility>
#include <variant>
#include <vector>

namespace pengu {

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
  };

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

// Declaraciones adelantadas: las sobrecargas de contenedores pueden
// necesitar imprimir un Value (por ejemplo vector de Value).
class Value;
std::string to_string(const Value& item);

// Resultado de comparar dos valores con <=>.
enum class Ordering { Less, Equal, Greater };

inline std::string to_string(Ordering value) {
  switch (value) {
    case Ordering::Less:
      return "less";
    case Ordering::Equal:
      return "equal";
    case Ordering::Greater:
      return "greater";
  }
  return "equal";
}

template <class A, class B>
Ordering compare(const A& left, const B& right) {
  if (left < right) return Ordering::Less;
  if (right < left) return Ordering::Greater;
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

inline bool contains(const std::string& text, const std::string& needle) {
  return text.find(needle) != std::string::npos;
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
  return container.at(index);
}

template <class C>
const auto& vec_at(const C& container, std::size_t index) {
  return container.at(index);
}

template <class M>
auto& map_at(M& map, const typename M::key_type& key) {
  auto it = map.find(key);
  if (it == map.end()) throw std::runtime_error("clave inexistente");
  return it->second;
}

template <class M>
const auto& map_at(const M& map, const typename M::key_type& key) {
  auto it = map.find(key);
  if (it == map.end()) throw std::runtime_error("clave inexistente");
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

inline long long random_int(long long min, long long max) {
  if (max < min) std::swap(min, max);
  std::uniform_int_distribution<long long> distribution(min, max);
  return distribution(random_engine());
}

inline double random_float() {
  std::uniform_real_distribution<double> distribution(0.0, 1.0);
  return distribution(random_engine());
}

inline bool random_bool() {
  std::uniform_int_distribution<int> distribution(0, 1);
  return distribution(random_engine()) == 1;
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
    const auto lowest = static_cast<long long>(std::numeric_limits<T>::lowest());
    const auto highest = static_cast<long long>(std::numeric_limits<T>::max());
    if (value < lowest || value > highest) return std::nullopt;
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
  std::cerr << "[" << level << "] " << format_values(values) << '\\n';
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
