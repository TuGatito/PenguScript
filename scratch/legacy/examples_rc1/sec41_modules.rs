mod geometry {
    pub struct Point {
        pub x: f64,
        pub y: f64,
    }

    pub fn distance(a: &Point, b: &Point) -> f64 {
        let dx = a.x - b.x;
        let dy = a.y - b.y;
        (dx * dx + dy * dy).sqrt()
    }
}

fn main() {
    let a = geometry::Point { x: 0.0, y: 0.0 };
    let b = geometry::Point { x: 3.0, y: 4.0 };
    println!("{}", geometry::distance(&a, &b));
}
