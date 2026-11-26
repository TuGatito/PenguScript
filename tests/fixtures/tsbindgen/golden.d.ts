/** Un elemento del documento. */
interface Element {
  /** Identificador del elemento. */
  id: string;
  readonly tagName: string;
  className: string;
  childElementCount: number;
  width: number;
  appendChild(child: Node): Node;
  querySelector(selectors: string): Element | null;
  getAttribute(name: string): string | null;
  setAttribute(name: string, value: string): void;
  remove(): void;
  [index: number]: Element;
}

interface Node {
  nodeType: number;
  textContent: string | null;
  parentNode: Node | null;
}

interface HTMLElement extends Element, Node {
  title: string;
  hidden: boolean;
  click(): void;
}

interface Document {
  title: string;
  body: HTMLElement;
  createElement(tagName: string, options?: ElementCreationOptions): HTMLElement;
  getElementById(id: string): HTMLElement | null;
  querySelectorAll(selectors: string): NodeList;
}

type NodeList = ArrayLike<Node>;

declare var document: Document;
declare function setTimeout(handler: () => void, timeout?: number): number;

declare namespace URL {
  function createObjectURL(blob: Blob): string;
  const canParse: boolean;
}

interface Blob {
  readonly size: number;
  type: string;
}

enum NodeKind {
  Element = 1,
  Text = 3,
}
