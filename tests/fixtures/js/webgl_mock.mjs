// Mock de WebGL para los tests E2E (plan §8). Reutiliza el del DOM y añade un
// contexto `webgl` que registra las llamadas, para poder comprobar que el
// programa habla con la API como lo haría en un navegador real.

import "./dom_mock.mjs";

globalThis.__GL = [];

function registro(nombre, ...args) {
  const texto = args.map((valor) => (typeof valor === "number" ? String(valor) : JSON.stringify(valor) ?? "null"));
  globalThis.__GL.push(`${nombre}(${texto.join(",")})`);
}

class ShaderMock {
  constructor(tipo) {
    this.tipo = tipo;
    this.fuente = "";
    globalThis.__GL.push(`createShader:${tipo}`);
  }
}

class ProgramaMock {
  constructor() {
    this.shaders = [];
    globalThis.__GL.push("createProgram");
  }
}

class BufferMock {
  constructor() {
    this.datos = null;
    globalThis.__GL.push("createBuffer");
  }
}

const gl = {
  VERTEX_SHADER: 35633,
  FRAGMENT_SHADER: 35632,
  COMPILE_STATUS: 35713,
  LINK_STATUS: 35714,
  ARRAY_BUFFER: 34962,
  STATIC_DRAW: 35044,
  FLOAT: 5126,
  TRIANGLES: 4,
  COLOR_BUFFER_BIT: 16384,

  createShader(tipo) {
    return new ShaderMock(tipo);
  },
  shaderSource(shader, fuente) {
    shader.fuente = fuente;
    registro("shaderSource", fuente);
  },
  compileShader(shader) {
    registro("compileShader", shader.fuente.length);
  },
  getShaderParameter(_shader, parametro) {
    registro("getShaderParameter", parametro);
    return true;
  },
  getShaderInfoLog() {
    return "";
  },
  createProgram() {
    return new ProgramaMock();
  },
  attachShader(programa, shader) {
    programa.shaders.push(shader);
    registro("attachShader", programa.shaders.length);
  },
  linkProgram(programa) {
    registro("linkProgram", programa.shaders.length);
  },
  getProgramParameter(_programa, parametro) {
    registro("getProgramParameter", parametro);
    return true;
  },
  useProgram() {
    registro("useProgram");
  },
  createBuffer() {
    return new BufferMock();
  },
  bindBuffer() {
    registro("bindBuffer");
  },
  bufferData(_objetivo, datos) {
    registro("bufferData", datos.length);
  },
  getAttribLocation(_programa, nombre) {
    registro("getAttribLocation", nombre);
    return 0;
  },
  enableVertexAttribArray() {
    registro("enableVertexAttribArray");
  },
  vertexAttribPointer(_indice, tamano, _tipo, _normalizado, _paso, _desplazamiento) {
    registro("vertexAttribPointer", tamano);
  },
  viewport(_x, _y, ancho, alto) {
    registro("viewport", ancho, alto);
  },
  clearColor(r, g, b, a) {
    registro("clearColor", r, g, b, a);
  },
  clear() {
    registro("clear");
  },
  drawArrays(_modo, primero, cuenta) {
    registro("drawArrays", primero, cuenta);
  },
};

// Cualquier lienzo que pida `webgl` recibe este contexto.
const crear = globalThis.document.createElement.bind(globalThis.document);
globalThis.document.createElement = (etiqueta) => {
  const elemento = crear(etiqueta);
  if (etiqueta !== "canvas") return elemento;
  const original = elemento.getContext.bind(elemento);
  elemento.getContext = (tipo) => (tipo === "webgl" || tipo === "webgl2" ? gl : original(tipo));
  return elemento;
};
