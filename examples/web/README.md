# Web application example

`hello_app.pengu` builds a small page with `std.web.dom` and fetches text with
`std.web.http`.

```sh
psc build examples/web/hello_app.pengu --target wasm --profile=release --out=build/hello_app
```

Open `build/hello_app.html` in a browser. The example uses a `data:` URL so it
works offline. To call a real API, replace it with an `https://` URL and serve
the page over HTTP(S); `fetch` follows the same CORS rules as JavaScript.

The example intentionally lives outside the native test suite: `std.web.dom`
has a native `NotSupported` stub, but constructing a DOM program in a native
build is not meaningful.
