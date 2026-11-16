#[derive(Debug, Clone)]
struct Point {
    x: i32,
    y: i32,
}

#[cfg(debug_assertions)]
fn debug_only() -> bool {
    true
}

fn main() {
    println!("{:?}", Point { x: 1, y: 2 });
}
