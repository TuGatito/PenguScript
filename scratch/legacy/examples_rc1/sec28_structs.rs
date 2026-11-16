struct Point {
    x: f64,
    y: f64,
}

struct Pair(i32, i32);

fn main() {
    let p = Point { x: 3.0, y: 4.0 };
    let q = Point { x: 1.0, ..p };
    let pair = Pair(7, 8);

    println!("{}", p.x + q.y);
    println!("{}", pair.0 + pair.1);
}
