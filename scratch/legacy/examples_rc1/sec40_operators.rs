use std::ops::Add;

struct Point {
    x: i32,
    y: i32,
}

impl Add for Point {
    type Output = Point;
    fn add(self, other: Point) -> Point {
        Point {
            x: self.x + other.x,
            y: self.y + other.y,
        }
    }
}

fn main() {
    let p = Point { x: 1, y: 2 } + Point { x: 3, y: 4 };
    println!("{}", p.x);
    println!("{}", p.y);
}
