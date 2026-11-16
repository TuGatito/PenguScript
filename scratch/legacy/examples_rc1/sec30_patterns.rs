struct Point {
    x: i32,
    y: i32,
}

fn classify(n: i32) -> &'static str {
    match n {
        0 => "cero",
        1 | 2 | 3 => "pequeño",
        4..=9 => "mediano",
        _ => "grande",
    }
}

fn main() {
    let p = Point { x: 1, y: 2 };
    println!("{}", classify(7));

    let total = match p {
        Point { x: 0, y } => y,
        Point { x, y } => x + y,
    };
    println!("{}", total);
}
