# std.web.canvas

> Source: `std/web/canvas.pengu`

std.web.canvas — Canvas 2D drawing.

WebAssembly-only. `context2d` looks up a canvas element and returns a drawing
context. All methods return `result`; a missing element, a null context, or a
browser exception becomes `JsError` with the real name/message/stack.

```pengu
var c as result of canvas.Canvas to js.JsError is calling canvas.context2d with "#board"
if c.is_ok:
    calling canvas.set_fill_style with c.value, "#101820"
    calling canvas.fill_rect with c.value, 0.0, 0.0, 320.0, 200.0
    calling canvas.free with (sigil of c.value)
```

Coordinates and sizes are `f64`. Colour strings are CSS colours. The canvas
element is kept alive by the `Canvas` value.

---

### `CANVAS_VERSION`

> **CANVAS_VERSION** : string

_Undocumented._

### `Canvas`

> rune Canvas

```pengu
    _ctx as JsValue
    _element as Element
```

 A 2D drawing context and its canvas element.

### `TextMetrics`

> rune TextMetrics

```pengu
    width as f64
    actual_left as f64
    actual_right as f64
    actual_ascent as f64
    actual_descent as f64
    font_left as f64
    font_right as f64
    font_ascent as f64
    font_descent as f64
```

 Text measurements returned by `measure_text`.

### `context2d`

> **context2d**(selector: string) -> result of Canvas to JsError

_Undocumented._

### `from_element`

> **from_element**(el: Element) -> result of Canvas to JsError

_Undocumented._

### `free`

> **free**(c: ref to Canvas) -> void

_Undocumented._

### `element`

> **element**(c: Canvas) -> Element

_Undocumented._

### `width`

> **width**(c: Canvas) -> result of int to JsError

_Undocumented._

### `height`

> **height**(c: Canvas) -> result of int to JsError

_Undocumented._

### `set_text_prop`

> **set_text_prop**(c: Canvas, name: string, value: string) -> result of bool to JsError

_Undocumented._

### `text_prop`

> **text_prop**(c: Canvas, name: string) -> result of string to JsError

_Undocumented._

### `set_number_prop`

> **set_number_prop**(c: Canvas, name: string, value: f64) -> result of bool to JsError

_Undocumented._

### `number_prop`

> **number_prop**(c: Canvas, name: string) -> result of f64 to JsError

_Undocumented._

### `set_fill_style`

> **set_fill_style**(c: Canvas, value: string) -> result of bool to JsError

_Undocumented._

### `fill_style`

> **fill_style**(c: Canvas) -> result of string to JsError

_Undocumented._

### `set_stroke_style`

> **set_stroke_style**(c: Canvas, value: string) -> result of bool to JsError

_Undocumented._

### `stroke_style`

> **stroke_style**(c: Canvas) -> result of string to JsError

_Undocumented._

### `set_line_width`

> **set_line_width**(c: Canvas, value: f64) -> result of bool to JsError

_Undocumented._

### `line_width`

> **line_width**(c: Canvas) -> result of f64 to JsError

_Undocumented._

### `set_line_cap`

> **set_line_cap**(c: Canvas, value: string) -> result of bool to JsError

_Undocumented._

### `set_line_join`

> **set_line_join**(c: Canvas, value: string) -> result of bool to JsError

_Undocumented._

### `set_miter_limit`

> **set_miter_limit**(c: Canvas, value: f64) -> result of bool to JsError

_Undocumented._

### `set_font`

> **set_font**(c: Canvas, value: string) -> result of bool to JsError

_Undocumented._

### `font`

> **font**(c: Canvas) -> result of string to JsError

_Undocumented._

### `set_text_align`

> **set_text_align**(c: Canvas, value: string) -> result of bool to JsError

_Undocumented._

### `text_align`

> **text_align**(c: Canvas) -> result of string to JsError

_Undocumented._

### `set_text_baseline`

> **set_text_baseline**(c: Canvas, value: string) -> result of bool to JsError

_Undocumented._

### `text_baseline`

> **text_baseline**(c: Canvas) -> result of string to JsError

_Undocumented._

### `set_global_alpha`

> **set_global_alpha**(c: Canvas, value: f64) -> result of bool to JsError

_Undocumented._

### `global_alpha`

> **global_alpha**(c: Canvas) -> result of f64 to JsError

_Undocumented._

### `set_composite`

> **set_composite**(c: Canvas, value: string) -> result of bool to JsError

_Undocumented._

### `composite`

> **composite**(c: Canvas) -> result of string to JsError

_Undocumented._

### `set_shadow_color`

> **set_shadow_color**(c: Canvas, value: string) -> result of bool to JsError

_Undocumented._

### `set_shadow_blur`

> **set_shadow_blur**(c: Canvas, value: f64) -> result of bool to JsError

_Undocumented._

### `set_shadow_offset_x`

> **set_shadow_offset_x**(c: Canvas, value: f64) -> result of bool to JsError

_Undocumented._

### `set_shadow_offset_y`

> **set_shadow_offset_y**(c: Canvas, value: f64) -> result of bool to JsError

_Undocumented._

### `set_image_smoothing`

> **set_image_smoothing**(c: Canvas, value: bool) -> result of bool to JsError

_Undocumented._

### `call0`

> **call0**(c: Canvas, method: string) -> result of JsValue to JsError

_Undocumented._

### `call1`

> **call1**(c: Canvas, method: string, a: f64) -> result of JsValue to JsError

_Undocumented._

### `call2`

> **call2**(c: Canvas, method: string, a: f64, b: f64) -> result of JsValue to JsError

_Undocumented._

### `call3`

> **call3**(c: Canvas, method: string, a: f64, b: f64, d: f64) -> result of JsValue to JsError

_Undocumented._

### `call4`

> **call4**(c: Canvas, method: string, a: f64, b: f64, d: f64, e: f64) -> result of JsValue to JsError

_Undocumented._

### `save`

> **save**(c: Canvas) -> result of bool to JsError

_Undocumented._

### `restore`

> **restore**(c: Canvas) -> result of bool to JsError

_Undocumented._

### `translate`

> **translate**(c: Canvas, x: f64, y: f64) -> result of bool to JsError

_Undocumented._

### `scale`

> **scale**(c: Canvas, x: f64, y: f64) -> result of bool to JsError

_Undocumented._

### `rotate`

> **rotate**(c: Canvas, radians: f64) -> result of bool to JsError

_Undocumented._

### `transform`

> **transform**(c: Canvas, a: f64, b: f64, cc: f64, d: f64, e: f64, f: f64) -> result of bool to JsError

_Undocumented._

### `set_transform`

> **set_transform**(c: Canvas, a: f64, b: f64, cc: f64, d: f64, e: f64, f: f64) -> result of bool to JsError

_Undocumented._

### `reset_transform`

> **reset_transform**(c: Canvas) -> result of bool to JsError

_Undocumented._

### `begin_path`

> **begin_path**(c: Canvas) -> result of bool to JsError

_Undocumented._

### `close_path`

> **close_path**(c: Canvas) -> result of bool to JsError

_Undocumented._

### `move_to`

> **move_to**(c: Canvas, x: f64, y: f64) -> result of bool to JsError

_Undocumented._

### `line_to`

> **line_to**(c: Canvas, x: f64, y: f64) -> result of bool to JsError

_Undocumented._

### `bezier_curve_to`

> **bezier_curve_to**(c: Canvas, cp1x: f64, cp1y: f64, cp2x: f64, cp2y: f64, x: f64, y: f64) -> result of bool to JsError

_Undocumented._

### `quadratic_curve_to`

> **quadratic_curve_to**(c: Canvas, cpx: f64, cpy: f64, x: f64, y: f64) -> result of bool to JsError

_Undocumented._

### `arc`

> **arc**(c: Canvas, x: f64, y: f64, radius: f64, start: f64, end: f64, anticlockwise: bool) -> result of bool to JsError

_Undocumented._

### `arc_to`

> **arc_to**(c: Canvas, x1: f64, y1: f64, x2: f64, y2: f64, radius: f64) -> result of bool to JsError

_Undocumented._

### `ellipse`

> **ellipse**(c: Canvas, x: f64, y: f64, rx: f64, ry: f64, rotation: f64, start: f64, end: f64, anticlockwise: bool) -> result of bool to JsError

_Undocumented._

### `rect`

> **rect**(c: Canvas, x: f64, y: f64, width: f64, height: f64) -> result of bool to JsError

_Undocumented._

### `round_rect`

> **round_rect**(c: Canvas, x: f64, y: f64, width: f64, height: f64, radius: f64) -> result of bool to JsError

_Undocumented._

### `fill`

> **fill**(c: Canvas) -> result of bool to JsError

_Undocumented._

### `stroke`

> **stroke**(c: Canvas) -> result of bool to JsError

_Undocumented._

### `clip`

> **clip**(c: Canvas) -> result of bool to JsError

_Undocumented._

### `fill_rect`

> **fill_rect**(c: Canvas, x: f64, y: f64, width: f64, height: f64) -> result of bool to JsError

_Undocumented._

### `stroke_rect`

> **stroke_rect**(c: Canvas, x: f64, y: f64, width: f64, height: f64) -> result of bool to JsError

_Undocumented._

### `clear_rect`

> **clear_rect**(c: Canvas, x: f64, y: f64, width: f64, height: f64) -> result of bool to JsError

_Undocumented._

### `fill_text`

> **fill_text**(c: Canvas, text: string, x: f64, y: f64) -> result of bool to JsError

_Undocumented._

### `stroke_text`

> **stroke_text**(c: Canvas, text: string, x: f64, y: f64) -> result of bool to JsError

_Undocumented._

### `measure_text`

> **measure_text**(c: Canvas, text: string) -> result of TextMetrics to JsError

_Undocumented._

### `measure_text_width`

> **measure_text_width**(c: Canvas, text: string) -> result of f64 to JsError

_Undocumented._

### `get_image_data`

> **get_image_data**(c: Canvas, x: f64, y: f64, width: f64, height: f64) -> result of JsValue to JsError

_Undocumented._

### `put_image_data`

> **put_image_data**(c: Canvas, data: JsValue, dx: f64, dy: f64) -> result of bool to JsError

_Undocumented._

### `create_image_data`

> **create_image_data**(c: Canvas, width: f64, height: f64) -> result of JsValue to JsError

_Undocumented._

### `set_size`

> **set_size**(c: Canvas, width: int, height: int) -> result of bool to JsError

_Undocumented._

### `fit_display`

> **fit_display**(selector: string, dpr: bool) -> result of Canvas to JsError

_Undocumented._

### `draw_image`

> **draw_image**(c: Canvas, image: Element, dx: f64, dy: f64) -> result of bool to JsError

_Undocumented._

### `draw_image_scaled`

> **draw_image_scaled**(c: Canvas, image: Element, dx: f64, dy: f64, width: f64, height: f64) -> result of bool to JsError

_Undocumented._

### `to_data_url`

> **to_data_url**(c: Canvas, kind: string, quality: f64) -> result of string to JsError

_Undocumented._

