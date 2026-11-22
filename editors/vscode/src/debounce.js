// Retrasa una acción hasta que pasen `delay` ms sin volver a pedirla.
// Sirve para no preguntar al servidor en cada movimiento del cursor.

function make_debounced(delay, run) {
  let timer;
  const schedule = () => {
    if (timer !== undefined) clearTimeout(timer);
    timer = setTimeout(() => {
      timer = undefined;
      run();
    }, delay);
  };
  const cancel = () => {
    if (timer !== undefined) clearTimeout(timer);
    timer = undefined;
  };
  return { schedule, cancel };
}

module.exports = { make_debounced };
