// Fixture controlado para `pengu ts-bindgen`: cubre todas las construcciones
// de `.d.ts` que el plan dice mapear, incluidas las que deben reportarse como
// omitidas. No pretende parecerse a `lib.dom.d.ts`, solo ejercitarlo.

/** Un elemento del árbol. */
interface Node {
  /** Nombre del nodo. */
  readonly nodeName: string;
  readonly parentNode: Node | null;
  appendChild<T extends Node>(node: T): T;
}

interface Element extends Node {
  readonly tagName: string;
  id: string;
  className?: string;
  getAttribute(name: string): string | null;
  setAttribute(name: string, value: string): void;
  querySelector<E extends Element = Element>(selectors: string): E | null;
}

interface HTMLElement extends Element {
  title: string;
  hidden: boolean;
  style: CSSStyleDeclaration;
  textContent: string | null;
}

interface CSSStyleDeclaration {
  [index: number]: string;
  length: number;
  getPropertyValue(property: string): string;
  setProperty(property: string, value: string | null): void;
}

interface HTMLCanvasElement extends HTMLElement {
  width: number;
  height: number;
  getContext(contextId: "2d", options?: CanvasRenderingContext2DSettings): CanvasRenderingContext2D | null;
}

interface CanvasRenderingContext2DSettings {
  alpha?: boolean;
  desynchronized?: boolean;
}

interface CanvasRenderingContext2D {
  fillStyle: string;
  strokeStyle: string;
  readonly canvas: HTMLCanvasElement;
  fillRect(x: number, y: number, w: number, h: number): void;
  fillText(text: string, x: number, y: number, maxWidth?: number): void;
  measureText(text: string): TextMetrics;
}

interface TextMetrics {
  readonly width: number;
}

interface Document extends Node {
  readonly body: HTMLElement;
  readonly head: HTMLElement;
  title: string;
  getElementById(elementId: string): HTMLElement | null;
  createElement(tagName: string, options?: ElementCreationOptions): HTMLElement;
  querySelector<E extends Element = Element>(selectors: string): E | null;
}

declare var document: Document;

declare function setTimeout(handler: TimerHandler, timeout?: number, ...arguments: unknown[]): number;
declare function clearTimeout(id: number): void;
declare function fetch(input: string, init?: RequestInit): Promise<Response>;

type TimerHandler = string | Function;

interface RequestInit {
  method?: string;
  body?: BodyInit | null;
  headers?: string | readonly string[][] | Record<string, string>;
}

type BodyInit = string | Uint8Array | ArrayBuffer;

interface Response {
  readonly ok: boolean;
  readonly status: number;
  json(): Promise<any>;
  text(): Promise<string>;
}

interface Storage {
  readonly length: number;
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
  clear(): void;
}

declare var localStorage: Storage;

declare namespace Math {
  const PI: number;
  function sin(x: number): number;
  function max(...values: number[]): number;
}

declare namespace JSON {
  function parse(text: string, reviver?: (this: any, key: string, value: any) => any): any;
  function stringify(value: any): string;
}

declare const enum Readonly_ {
  None = 0,
  Some = 1
}

interface Unsupported {
  conditional: unknown extends string ? string : number;
  mapped: { [K in "a" | "b"]: number };
  template: `hola-${string}`;
  intersection: string & { marca: true };
  keyed: keyof Document;
  indexed: Document["title"];
  lambda: (this: Window, ev: Event) => any;
}

interface Window {
  document: Document;
  setTimeout: typeof setTimeout;
}

declare global {
  interface Window {
    miGlobal: number;
  }
  var miVarGlobal: string;
}
