// Parches declarativos sobre lo que sale de los `.d.ts`.
//
// La tabla de tipos de §6.3 no puede con tres cosas de las librerías reales:
//
// 1. Los métodos **genéricos** con acceso indexado (`createElement<K extends
//    keyof HTMLElementTagNameMap>(tagName: K): HTMLElementTagNameMap[K]`), que
//    en PenguScript no tienen traducción directa.
// 2. Las **sobrecargas** cuya primera firma no es la útil (`getContext`).
// 3. Los tipos que el navegador devuelve como unión y que se usan siempre con
//    un literal (`addEventListener("click", …)`).
//
// Un parche dice, por tipo y miembro, qué firma se emite en su lugar. Es
// declarativo a propósito: no hay código, solo la tabla, y el informe de
// `ts-bindgen` cuenta los parches aplicados (`overrides`).

export interface MemberOverride {
  // Firma del método (`(params) -> tipo`) o tipo de la propiedad.
  readonly text: string;
  // Se emite como `mut` (propiedad escribible del host).
  readonly mutable?: boolean;
  // Se emite como `?` (propiedad opcional).
  readonly optional?: boolean;
  // Sigilos del método (`<T>`), si hace falta conservarlos.
  readonly sigils?: readonly string[];
  // Motivo, para el informe.
  readonly why?: string;
}

export interface TypeOverride {
  // Miembros nuevos que no están en el `.d.ts` (rara vez).
  readonly add?: Readonly<Record<string, MemberOverride>>;
  // Miembros del `.d.ts` cuya firma se sustituye.
  readonly members?: Readonly<Record<string, MemberOverride>>;
}

// Los tipos de `lib.dom.d.ts` que necesitan parche, por orden de importancia
// para el catálogo del navegador.
export const OVERRIDES: Readonly<Record<string, TypeOverride>> = {
  Document: {
    members: {
      createElement: {
        text: "(tagName: string, options: js::Any?) -> js::HTMLElement",
        why: "la firma real es genérica con acceso indexado",
      },
      createElementNS: {
        text: "(namespace: string, name: string, options: js::Any?) -> js::HTMLElement",
        why: "la firma real es genérica con acceso indexado",
      },
      getElementById: {
        text: "(elementId: string) -> js::HTMLElement?",
        why: "devuelve `HTMLElement | null`",
      },
      querySelector: {
        text: "(selector: string) -> js::Element?",
        why: "genérica sobre `ElementTagNameMap`",
      },
      querySelectorAll: {
        text: "(selector: string) -> js::NodeList",
        why: "genérica sobre `ElementTagNameMap`",
      },
    },
  },
  DocumentFragment: {
    members: {
      querySelector: { text: "(selector: string) -> js::Element?", why: "genérica" },
      querySelectorAll: { text: "(selector: string) -> js::NodeList", why: "genérica" },
    },
  },
  Element: {
    members: {
      querySelector: { text: "(selector: string) -> js::Element?", why: "genérica" },
      querySelectorAll: { text: "(selector: string) -> js::NodeList", why: "genérica" },
      // `addEventListener` acepta un mapa de opciones y una unión de listener;
      // en la práctica se pasa `(evento) => …`.
      addEventListener: {
        text: "(type: string, listener: js::Any, options: js::Any?) -> void",
        why: "unión de listener y opciones",
      },
      removeEventListener: { text: "(type: string, listener: js::Any, options: js::Any?) -> void", why: "unión" },
      dispatchEvent: { text: "(event: js::Event) -> bool", why: "unión" },
    },
  },
  Node: {
    members: {
      addEventListener: { text: "(type: string, listener: js::Any, options: js::Any?) -> void", why: "unión" },
      removeEventListener: { text: "(type: string, listener: js::Any, options: js::Any?) -> void", why: "unión" },
      appendChild: { text: "(node: js::Node) -> js::Node", why: "genérica: se pierde el tipo del hijo" },
    },
  },
  HTMLCanvasElement: {
    members: {
      getContext: {
        text: "(contextId: string, options: js::Any?) -> js::CanvasRenderingContext2D?",
        why: "sobrecargas por literal",
      },
      toDataURL: { text: "(type: string?, quality: double?) -> string", why: "sobrecargas" },
      toBlob: {
        text: "(funcion: js::Any, type: string?, quality: double?) -> void",
        why: "sobrecargas con callback",
      },
    },
  },
  CanvasRenderingContext2D: {
    members: {
      // `fillRect` y compañía ya salen bien; aquí solo lo que es unión.
      setLineDash: { text: "(segments: js::Array<double>) -> void", why: "acepta `number[]`" },
      getLineDash: { text: "() -> js::Array<double>", why: "devuelve `number[]`" },
      createPattern: { text: "(image: js::Any, repetition: string?) -> js::CanvasPattern?", why: "unión" },
      createLinearGradient: {
        text: "(x0: double, y0: double, x1: double, y1: double) -> js::CanvasGradient",
        why: "firma posicional",
      },
      // Propiedades de estilo: en el `.d.ts` son uniones con objetos y el
      // mapeador las dejaría en `js::Any`.
      fillStyle: { text: "string", why: "unión" },
      strokeStyle: { text: "string", why: "unión" },
      font: { text: "string", why: "unión" },
      textAlign: { text: "string", why: "unión" },
      textBaseline: { text: "string", why: "unión" },
      lineCap: { text: "string", why: "unión" },
      lineJoin: { text: "string", why: "unión" },
      globalCompositeOperation: { text: "string", why: "unión" },
      direction: { text: "string", why: "unión" },
      filter: { text: "string", why: "unión" },
    },
  },
  Window: {
    members: {
      addEventListener: { text: "(type: string, listener: js::Any, options: js::Any?) -> void", why: "unión" },
      removeEventListener: { text: "(type: string, listener: js::Any, options: js::Any?) -> void", why: "unión" },
      setTimeout: {
        text: "(handler: js::Any, timeout: double?, ...args: js::Any) -> int",
        why: "devuelve `number` y acepta argumentos",
      },
      setInterval: {
        text: "(handler: js::Any, timeout: double?, ...args: js::Any) -> int",
        why: "devuelve `number`",
      },
      clearTimeout: { text: "(id: int?) -> void", why: "acepta el id" },
      clearInterval: { text: "(id: int?) -> void", why: "acepta el id" },
      requestAnimationFrame: {
        text: "(funcion: js::Any) -> int",
        why: "devuelve `number`",
      },
      cancelAnimationFrame: { text: "(handle: int) -> void", why: "acepta el handle" },
      fetch: { text: "(input: string, init: js::RequestInit?) -> js::Promise<js::Response>", why: "unión" },
    },
  },
  Storage: {
    members: {
      getItem: { text: "(key: string) -> string?", why: "devuelve `string | null`" },
    },
  },
  Performance: {
    members: {
      now: { text: "() -> double", why: "`DOMHighResTimeStamp`" },
      mark: { text: "(markName: string, markOptions: js::Any?) -> js::PerformanceMark", why: "unión" },
      measure: { text: "(measureName: string, startOrOptions: js::Any?, endMark: string?) -> js::PerformanceMeasure", why: "unión" },
    },
  },
  Headers: {
    members: {
      get: { text: "(name: string) -> string?", why: "devuelve `string | null`" },
    },
  },
  Response: {
    members: {
      text: { text: "() -> js::Promise<string>", why: "devuelve `Promise<string>`" },
      json: { text: "() -> js::Promise<js::Any>", why: "devuelve `Promise<any>`" },
    },
  },
};

// Parches de `*` que valen para cualquier tipo que declare ese miembro (el
// `addEventListener` genérico aparece mezclado en decenas de interfaces).
const WILDCARD: readonly string[] = ["addEventListener", "removeEventListener", "dispatchEvent", "querySelector", "querySelectorAll"];

export function override_of(type: string, member: string): MemberOverride | undefined {
  const own = OVERRIDES[type]?.members?.[member];
  if (own !== undefined) return own;
  if (!WILDCARD.includes(member)) return undefined;
  for (const patch of Object.values(OVERRIDES)) {
    const found = patch.members?.[member];
    if (found !== undefined) return found;
  }
  return undefined;
}

export function added_of(type: string): readonly [string, MemberOverride][] {
  return Object.entries(OVERRIDES[type]?.add ?? {});
}

/** Nombres de los tipos con parche, para el informe. */
export function patched_types(): readonly string[] {
  return Object.keys(OVERRIDES);
}
