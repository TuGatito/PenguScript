// Sugerencias de nombres parecidos para los diagnósticos.
//
// Se usa una distancia de Levenshtein pequeña y una comparación sin
// distinguir mayúsculas: la mayoría de los errores reales son una
// letra cambiada o una palabra clave escrita con mayúscula inicial.

const MAX_CANDIDATES = 200;

export function levenshtein(a: string, b: string): number {
  if (a === b) return 0;
  const rows = a.length + 1;
  const columns = b.length + 1;
  let previous = Array.from({ length: columns }, (_, index) => index);
  let current = new Array<number>(columns).fill(0);

  for (let row = 1; row < rows; row += 1) {
    current[0] = row;
    for (let column = 1; column < columns; column += 1) {
      const cost = a.charAt(row - 1) === b.charAt(column - 1) ? 0 : 1;
      current[column] = Math.min(
        (current[column - 1] ?? 0) + 1,
        (previous[column] ?? 0) + 1,
        (previous[column - 1] ?? 0) + cost,
      );
    }
    const swap = previous;
    previous = current;
    current = swap;
  }
  return previous[columns - 1] ?? 0;
}

// Devuelve el candidato más parecido, o `undefined` si ninguno está lo
// bastante cerca como para sugerirlo sin ruido.
export function suggest_name(
  input: string,
  candidates: Iterable<string>,
): string | undefined {
  const lower_input = input.toLowerCase();
  let best: string | undefined;
  let best_distance = Number.POSITIVE_INFINITY;
  let seen = 0;

  for (const candidate of candidates) {
    if (candidate === input) return candidate;
    seen += 1;
    if (seen > MAX_CANDIDATES) break;

    if (candidate.toLowerCase() === lower_input) {
      return candidate;
    }
    const distance = levenshtein(lower_input, candidate.toLowerCase());
    const limit = lower_input.length <= 4 ? 1 : 2;
    if (distance <= limit && distance < best_distance) {
      best = candidate;
      best_distance = distance;
    }
  }
  return best;
}
