export type Result<T, E> =
  | { readonly ok: true; readonly value: T }
  | { readonly ok: false; readonly error: E };

export function ok<T>(value: T): Result<T, never> {
  return { ok: true, value };
}

export function err<E>(error: E): Result<never, E> {
  return { ok: false, error };
}

export function is_ok<T, E>(result: Result<T, E>): result is { ok: true; value: T } {
  return result.ok;
}

export function is_err<T, E>(result: Result<T, E>): result is { ok: false; error: E } {
  return !result.ok;
}

export function map_result<T, U, E>(
  result: Result<T, E>,
  map: (value: T) => U,
): Result<U, E> {
  return result.ok ? ok(map(result.value)) : result;
}

export function unwrap_or<T, E>(result: Result<T, E>, fallback: T): T {
  return result.ok ? result.value : fallback;
}

export function collect_results<T, E>(
  results: readonly Result<T, E>[],
): Result<readonly T[], readonly E[]> {
  const values: T[] = [];
  const errors: E[] = [];
  for (const result of results) {
    if (result.ok) values.push(result.value);
    else errors.push(result.error);
  }
  return errors.length > 0 ? err(errors) : ok(values);
}
