use std::path::PathBuf;

fn project(name: &str, source: &str) -> PathBuf {
    let stamp = format!(
        "{}_{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    );
    let dir = std::env::temp_dir().join(format!("gate-b-{name}-{stamp}"));
    std::fs::create_dir_all(&dir).unwrap();
    std::fs::write(
        dir.join("Tome.toml"),
        "[tome]\nname = \"demo\"\nversion = \"0.1.0\"\npengu = \"0.6\"\nedition = \"2024\"\n\n[[bin]]\nname = \"demo\"\n",
    )
    .unwrap();
    std::fs::write(dir.join("main.pengu"), source).unwrap();
    dir
}

fn build(name: &str, source: &str) -> Result<(), String> {
    let root = project(name, source);
    let report = pengu_build::build_report(&root).unwrap();
    if report.success() {
        Ok(())
    } else {
        Err(format!(
            "{name}: {:?}\n--- stderr ---\n{}",
            report.diagnostics,
            report
                .output
                .as_ref()
                .map(|o| format!(
                    "{}\n{}",
                    String::from_utf8_lossy(&o.stdout),
                    String::from_utf8_lossy(&o.stderr)
                ))
                .unwrap_or_default()
        ))
    }
}

#[test]
fn gate_b_valid_programs_compile() {
    let mut failures = Vec::new();
    let cases = [
        ("hello", "grimoire\n    print(\"hola\")\n"),
        (
            "records",
            "rune Point\n    x: Float\n    y: Float\n\n\
             unveil length = (p: Point) -> Float\n    p.x\n\n\
             grimoire\n    bind p = Point(x: 1.0, y: 2.0)\n    bind l = length(p)\n    print(l)\n",
        ),
        (
            "sums",
            "enchanting Shape\n    Circle(Float)\n    Point\n\n\
             area = (s: Shape) -> Float\n    match s\n        when Circle(r) then r * r\n        when Point then 0.0\n\n\
             grimoire\n    bind a = area(Circle(2.0))\n    print(a)\n",
        ),
        (
            "generic",
            "identity = [T](value: T) -> T\n    value\n\n\
             grimoire\n    bind n = identity[Int](42)\n    print(n)\n",
        ),
        (
            "option",
            "parse = (s: Str) -> Result[Int, Str]\n    if s == \"\" then\n        err(\"vacío\")\n    else\n        ok(1)\n\n\
             grimoire: Result[Unit, Str]\n    bind n = parse(\"x\")?\n    print(n)\n    ok(())\n",
        ),
        (
            "collections",
            "grimoire\n    bind xs = Vec[1, 2, 3]\n    morph total = 0\n    for x in xs\n        total = total + x\n    bind m = Map[\"a\": total]\n    print(m[\"a\"])\n",
        ),
        (
            "closure",
            "rune Counter\n    value: Int\n\nritual Counter\n    bump = (@mut) -> Unit\n        @.value = @.value + 1\n\ngrimoire\n    morph c = Counter(value: 0)\n    c.bump()\n    bind f = (x: Int) => x + c.value\n    print(f(2))\n",
        ),
        (
            "modules",
            "scroll geometry\n    unveil rune Point\n        x: Float\n    unveil length = (p: Point) -> Float\n        p.x\n    unveil make = () -> Point\n        Point(x: 3.0)\n\n\
             grimoire\n    bind p = geometry::make()\n    print(geometry::length(p))\n",
        ),
        (
            "pacts",
            "pact Shape\n    area = (@) -> Float\n\nrune Circle\n    r: Float\n\n\
             ritual Circle for Shape\n    area = (@) -> Float\n        @.r * @.r\n\n\
             grimoire\n    bind c = Circle(r: 2.0)\n    print(c.area())\n",
        ),
        (
            "generic-record",
            "rune Wrap[T]\n    value: T\n\nritual[T] Wrap[T]\n    get = (@own) -> T\n        @.value\n\n\
             grimoire\n    bind w = Wrap(value: 7)\n    print(w.get())\n",
        ),
        (
            "iterators",
            "grimoire\n    bind xs = Vec[1, 2, 3]\n    bind doubled = xs.iter().map((x: Int) => x * 2).collect()\n    for x in doubled\n        print(x)\n",
        ),
        (
            "map-destructure",
            "grimoire\n    bind m = Map[\"a\": 1, \"b\": 2]\n    morph total = 0\n    for (k, v) in m\n        total = total + v\n    print(total)\n",
        ),
        (
            "nested-destructure",
            "grimoire\n    bind m = Map[\"a\": (1, (2, 3))]\n    morph total = 0\n    for (k, (x, (y, z))) in m\n        total = total + x + y + z\n    print(total)\n",
        ),
        (
            "user-show",
            "rune Point\n    x: Int\n    y: Int\n\nritual Point for Show\n    show = (@) -> String\n        format(\"point\")\n\n\
             grimoire\n    print(Point(x: 1, y: 2))\n",
        ),
        (
            "option-result",
            "f = (x: ?Int) -> Int\n    bind some(v) = x else\n        return 0\n    v\n\ngrimoire\n    print(f(some(3)))\n    print(f(none))\n",
        ),
    ];
    for (name, source) in cases {
        if let Err(error) = build(name, source) {
            failures.push(error);
        }
    }
    assert!(failures.is_empty(), "{}", failures.join("\n\n"));
}
