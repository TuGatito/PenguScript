// Mock mínimo del DOM para los tests E2E de `std/js` (plan §8). No pretende
// ser un navegador: solo registra las llamadas para poder compararlas.

globalThis.__LLAMADAS = [];
globalThis.__EVENTOS = [];

class NodoMock {
  constructor(nombre) {
    this.nodeName = nombre.toUpperCase();
    this.childNodes = [];
    this.parentNode = null;
    this.textContent = "";
  }

  appendChild(hijo) {
    hijo.parentNode = this;
    this.childNodes.push(hijo);
    return hijo;
  }

  removeChild(hijo) {
    const indice = this.childNodes.indexOf(hijo);
    if (indice >= 0) this.childNodes.splice(indice, 1);
    hijo.parentNode = null;
    return hijo;
  }

  addEventListener(tipo, manejador) {
    globalThis.__EVENTOS.push(`${this.nodeName}:${tipo}`);
    this.manejador = manejador;
  }

  removeEventListener(tipo) {
    globalThis.__EVENTOS.push(`${this.nodeName}:quitar:${tipo}`);
  }

  get firstChild() {
    return this.childNodes[0] ?? null;
  }
}

class ElementoMock extends NodoMock {
  constructor(etiqueta) {
    super(etiqueta);
    this.tagName = etiqueta.toUpperCase();
    this.attributes = {};
    this.style = {};
    this.dataset = {};
    this.className = "";
    this.id = "";
    this.children = this.childNodes;
  }

  setAttribute(nombre, valor) {
    this.attributes[nombre] = String(valor);
  }

  getAttribute(nombre) {
    return this.attributes[nombre] ?? null;
  }

  removeAttribute(nombre) {
    delete this.attributes[nombre];
  }

  hasAttribute(nombre) {
    return nombre in this.attributes;
  }

  getContext(tipo) {
    globalThis.__LLAMADAS.push(`getContext:${tipo}:${this.tagName}`);
    return new ContextoMock(this);
  }

  getBoundingClientRect() {
    return { x: 0, y: 0, width: this.width ?? 0, height: this.height ?? 0, top: 0, left: 0 };
  }
}

class ContextoMock {
  constructor(lienzo) {
    this.canvas = lienzo;
    this.fillStyle = "#000000";
    this.strokeStyle = "#000000";
    this.lineWidth = 1;
    this.font = "10px sans-serif";
    this.globalAlpha = 1;
  }

  registrar(nombre, ...args) {
    const argumentos = args.map((valor) => JSON.stringify(valor) ?? "null").join(",");
    globalThis.__LLAMADAS.push(`${nombre}(${argumentos})`);
  }

  fillRect(...args) {
    this.registrar("fillRect", ...args);
  }

  strokeRect(...args) {
    this.registrar("strokeRect", ...args);
  }

  clearRect(...args) {
    this.registrar("clearRect", ...args);
  }

  fillText(...args) {
    this.registrar("fillText", ...args);
  }

  strokeText(...args) {
    this.registrar("strokeText", ...args);
  }

  beginPath() {
    this.registrar("beginPath");
  }

  closePath() {
    this.registrar("closePath");
  }

  moveTo(...args) {
    this.registrar("moveTo", ...args);
  }

  lineTo(...args) {
    this.registrar("lineTo", ...args);
  }

  arc(...args) {
    this.registrar("arc", ...args);
  }

  fill() {
    this.registrar("fill");
  }

  stroke() {
    this.registrar("stroke");
  }

  save() {
    this.registrar("save");
  }

  restore() {
    this.registrar("restore");
  }

  translate(...args) {
    this.registrar("translate", ...args);
  }

  rotate(...args) {
    this.registrar("rotate", ...args);
  }

  scale(...args) {
    this.registrar("scale", ...args);
  }

  drawImage(...args) {
    this.registrar("drawImage", ...args);
  }

  createImageData(ancho, alto) {
    return { width: ancho, height: alto, data: new Uint8ClampedArray(ancho * alto * 4) };
  }

  getImageData(_x, _y, ancho, alto) {
    return { width: ancho, height: alto, data: new Uint8ClampedArray(ancho * alto * 4) };
  }

  putImageData() {
    this.registrar("putImageData");
  }
}

class DocumentoMock extends NodoMock {
  constructor() {
    super("document");
    this.title = "";
    this.cookie = "";
    this.body = new ElementoMock("body");
    this.documentElement = new ElementoMock("html");
    this.readyState = "complete";
    this.porId = new Map();
  }

  createElement(etiqueta) {
    globalThis.__LLAMADAS.push(`createElement:${etiqueta}`);
    const elemento = new ElementoMock(etiqueta);
    if (etiqueta === "canvas") {
      elemento.width = 300;
      elemento.height = 150;
    }
    return elemento;
  }

  createTextNode(texto) {
    const nodo = new NodoMock("#text");
    nodo.textContent = String(texto);
    nodo.data = String(texto);
    return nodo;
  }

  getElementById(id) {
    const elemento = this.porId.get(id);
    if (elemento === undefined) {
      globalThis.__LLAMADAS.push(`getElementById:${id}:null`);
      return null;
    }
    globalThis.__LLAMADAS.push(`getElementById:${id}`);
    return elemento;
  }

  querySelector(selector) {
    globalThis.__LLAMADAS.push(`querySelector:${selector}`);
    for (const elemento of this.porId.values()) {
      if (`#${elemento.id}` === selector) return elemento;
    }
    return null;
  }

  querySelectorAll(selector) {
    globalThis.__LLAMADAS.push(`querySelectorAll:${selector}`);
    return [...this.porId.values()].filter((elemento) => `#${elemento.id}` === selector);
  }
}

const documento = new DocumentoMock();

// Un elemento conocido para los tests que usan `getElementById`.
const conocido = documento.createElement("div");
conocido.id = "app";
documento.porId.set("app", conocido);

globalThis.document = documento;
globalThis.window = globalThis;
// `navigator` y `location` son de solo lectura en Node 26: se definen como
// propiedades configurables para que el mock funcione igual en bun y en node.
Object.defineProperty(globalThis, "navigator", {
  value: { userAgent: "pengu-test", language: "es-ES" },
  configurable: true,
  writable: true,
});
Object.defineProperty(globalThis, "location", {
  value: { href: "https://example.test/", hash: "", pathname: "/" },
  configurable: true,
  writable: true,
});
globalThis.devicePixelRatio = 1;
globalThis.localStorage = {
  datos: new Map(),
  getItem(clave) {
    return this.datos.has(clave) ? this.datos.get(clave) : null;
  },
  setItem(clave, valor) {
    this.datos.set(clave, String(valor));
  },
  removeItem(clave) {
    this.datos.delete(clave);
  },
  clear() {
    this.datos.clear();
  },
};
globalThis.sessionStorage = globalThis.localStorage;
globalThis.performance = globalThis.performance ?? { now: () => 0 };
globalThis.requestAnimationFrame = (funcion) => {
  globalThis.__LLAMADAS.push("requestAnimationFrame");
  funcion(0);
  return 1;
};
globalThis.cancelAnimationFrame = () => {};
globalThis.alert = (...args) => {
  globalThis.__LLAMADAS.push(`alert:${args.join(",")}`);
};
globalThis.fetch = async (url) => ({
  ok: true,
  status: 200,
  url: String(url),
  text: async () => "respuesta",
  json: async () => ({ ok: true }),
});
