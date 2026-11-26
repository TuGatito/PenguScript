// Filtrado por dominio: `pengu ts-bindgen lib.dom.d.ts --only canvas`.
//
// Un dominio es un conjunto de tipos «semilla»; el resto del módulo entra por
// cierre de dependencias (los tipos que esos tipos usan en miembros, herencia
// o firmas). Sin el cierre, un módulo filtrado declararía miembros cuyo tipo no
// existe y el checker fallaría al usarlos.

import { referenced_names } from "./dts_type.ts";
import type { DtsModule, DtsNamedNode, DtsNode } from "./dts_ast.ts";
import type { DtsMember } from "./dts_type.ts";

export interface Domain {
  readonly name: string;
  // Nombres del `.d.ts` que forman el dominio.
  readonly seeds: readonly string[];
}

// Los diez dominios del catálogo (§6.5), más los dos grandes que se generan
// enteros.
export const DOMAINS: Readonly<Record<string, Domain>> = {
  dom: {
    name: "dom",
    seeds: [
      "Document",
      "DocumentFragment",
      "DocumentType",
      "Node",
      "NodeList",
      "Element",
      "HTMLElement",
      "HTMLDivElement",
      "HTMLInputElement",
      "HTMLImageElement",
      "HTMLAnchorElement",
      "HTMLButtonElement",
      "HTMLBodyElement",
      "HTMLHeadElement",
      "HTMLHtmlElement",
      "HTMLParagraphElement",
      "HTMLSpanElement",
      "HTMLStyleElement",
      "HTMLScriptElement",
      "HTMLTemplateElement",
      "Text",
      "Comment",
      "DOMTokenList",
      "DOMRect",
      "DOMRectReadOnly",
      "DOMPoint",
      "Range",
      "Selection",
      "MutationObserver",
      "NodeFilter",
    ],
  },
  events: {
    name: "events",
    seeds: [
      "Event",
      "EventTarget",
      "EventInit",
      "CustomEvent",
      "MouseEvent",
      "KeyboardEvent",
      "PointerEvent",
      "FocusEvent",
      "InputEvent",
      "WheelEvent",
      "TouchEvent",
      "DragEvent",
      "SubmitEvent",
      "UIEvent",
      "EventListener",
      "EventListenerObject",
      "EventListenerOrEventListenerObject",
      "AddEventListenerOptions",
      "EventListenerOptions",
    ],
  },
  canvas: {
    name: "canvas",
    seeds: [
      "HTMLCanvasElement",
      "CanvasRenderingContext2D",
      "CanvasRenderingContext2DSettings",
      "ImageData",
      "ImageBitmap",
      "CanvasPattern",
      "CanvasGradient",
      "TextMetrics",
      "Path2D",
      "OffscreenCanvas",
      "OffscreenCanvasRenderingContext2D",
      "CanvasImageSource",
      "CanvasFillStrokeStyles",
      "CanvasPathDrawingStyles",
      "CanvasTextDrawingStyles",
      "CanvasDrawImage",
      "CanvasDrawPath",
      "CanvasText",
      "CanvasRect",
      "CanvasCompositing",
      "CanvasImageSmoothing",
      "CanvasShadowStyles",
    ],
  },
  fetch: {
    name: "fetch",
    seeds: [
      "Headers",
      "HeadersInit",
      "Request",
      "RequestInit",
      "RequestInfo",
      "RequestMode",
      "RequestCache",
      "RequestCredentials",
      "RequestRedirect",
      "Response",
      "ResponseInit",
      "ResponseType",
      "Body",
      "BodyInit",
      "AbortController",
      "AbortSignal",
    ],
  },
  storage: {
    name: "storage",
    seeds: ["Storage", "StorageEvent", "StorageEventInit"],
  },
  webgl: {
    name: "webgl",
    seeds: [
      "WebGLRenderingContext",
      "WebGL2RenderingContext",
      "WebGLContextAttributes",
      "WebGLBuffer",
      "WebGLFramebuffer",
      "WebGLProgram",
      "WebGLRenderbuffer",
      "WebGLShader",
      "WebGLTexture",
      "WebGLUniformLocation",
      "WebGLActiveInfo",
      "WebGLShaderPrecisionFormat",
      "WebGLContextEvent",
      "WebGLPowerPreference",
    ],
  },
  webaudio: {
    name: "webaudio",
    seeds: [
      "AudioContext",
      "AudioNode",
      "AudioBuffer",
      "AudioBufferSourceNode",
      "AudioDestinationNode",
      "AudioListener",
      "AudioParam",
      "BiquadFilterNode",
      "GainNode",
      "OscillatorNode",
      "PannerNode",
      "AnalyserNode",
      "BaseAudioContext",
      "OfflineAudioContext",
      "PeriodicWave",
    ],
  },
  webgpu: {
    name: "webgpu",
    seeds: [
      "GPU",
      "GPUDevice",
      "GPUAdapter",
      "GPUCanvasContext",
      "GPUBuffer",
      "GPUTexture",
      "GPUShaderModule",
      "GPURenderPipeline",
      "GPUComputePipeline",
      "GPUCommandEncoder",
      "GPUQueue",
      "GPUBindGroup",
      "GPUBindGroupLayout",
      "GPUPipelineLayout",
      "GPUSampler",
    ],
  },
  performance: {
    name: "performance",
    seeds: [
      "Performance",
      "PerformanceEntry",
      "PerformanceMark",
      "PerformanceMeasure",
      "PerformanceObserver",
      "PerformanceObserverEntryList",
      "PerformanceResourceTiming",
      "PerformanceNavigationTiming",
      "PerformanceTiming",
      "PerformanceNavigation",
    ],
  },
};

// Globals que pertenecen a un dominio aunque su tipo no esté en las semillas
// (el global es lo que usa el programa: `localStorage`, `performance`…).
const DOMAIN_GLOBALS: Readonly<Record<string, readonly string[]>> = {
  dom: ["document", "window", "navigator", "history", "location", "screen"],
  storage: ["localStorage", "sessionStorage"],
  performance: ["performance"],
  fetch: ["fetch", "caches"],
  webaudio: ["AudioContext", "OfflineAudioContext"],
};

export function domain_names(name: string): readonly string[] {
  const domain = DOMAINS[name];
  if (domain === undefined) return [];
  return [...domain.seeds, ...(DOMAIN_GLOBALS[name] ?? [])];
}

export function is_domain(name: string): boolean {
  return DOMAINS[name] !== undefined;
}

function member_types(member: DtsMember, into: Set<string>): void {
  switch (member.kind) {
    case "property":
      referenced_names(member.type, into);
      return;
    case "method":
    case "call":
      for (const param of member.params) referenced_names(param.type, into);
      referenced_names(member.result, into);
      return;
    case "construct":
      for (const param of member.params) referenced_names(param.type, into);
      return;
    case "index":
      referenced_names(member.key, into);
      referenced_names(member.value, into);
      return;
  }
}

function node_types(node: DtsNode, into: Set<string>): void {
  switch (node.kind) {
    case "interface":
    case "class":
      for (const heritage of node.heritage) into.add(heritage.name);
      for (const member of node.members) member_types(member, into);
      return;
    case "alias":
      referenced_names(node.type, into);
      return;
    case "var":
      referenced_names(node.type, into);
      return;
    case "function":
      for (const param of node.params) referenced_names(param.type, into);
      referenced_names(node.result, into);
      return;
    case "namespace":
      for (const child of node.nodes) node_types(child, into);
      return;
    case "enum":
    case "global":
      return;
  }
}

/**
 * Recorta el módulo a `seeds` y sus dependencias. Los nodos que no se
 * alcanzan quedan fuera, así que un `--only canvas` produce un archivo pequeño
 * que sigue siendo autoconsistente.
 */
export function filter_module(module: DtsModule, seeds: readonly string[]): DtsModule {
  const by_name = module.by_name;
  const wanted = new Set<string>();
  const queue: string[] = [];
  for (const seed of seeds) {
    if (by_name.has(seed) && !wanted.has(seed)) {
      wanted.add(seed);
      queue.push(seed);
    }
  }

  while (queue.length > 0) {
    const name = queue.pop() as string;
    const node = by_name.get(name);
    if (node === undefined) continue;
    const references = new Set<string>();
    node_types(node, references);
    for (const reference of references) {
      if (!by_name.has(reference) || wanted.has(reference)) continue;
      wanted.add(reference);
      queue.push(reference);
    }
  }

  const nodes: DtsNode[] = [];
  for (const node of module.nodes) {
    switch (node.kind) {
      case "namespace":
      case "global":
        nodes.push(node);
        break;
      case "enum":
        nodes.push(node);
        break;
      default:
        if (wanted.has(node.name)) nodes.push(node);
        break;
    }
  }

  const byName = new Map<string, DtsNamedNode>();
  for (const node of nodes) {
    if (node.kind !== "global") byName.set(node.name, node);
  }

  return { file: module.file, nodes, by_name: byName, stats: module.stats };
}

/** Para el informe: cuántos tipos del dominio entraron frente a los pedidos. */
export function coverage_of(module: DtsModule, filtered: DtsModule): { total: number; kept: number } {
  const total = module.nodes.filter((node) => node.kind === "interface" || node.kind === "class").length;
  const kept = filtered.nodes.filter((node) => node.kind === "interface" || node.kind === "class").length;
  return { total, kept };
}

export type { DtsNode };
