enum Shape {
    Circle(f64),
    Rectangle(f64, f64),
}

fn area(shape: &Shape) -> f64 {
    match shape {
        Shape::Circle(r) => 3.141592653589793 * r * r,
        Shape::Rectangle(w, h) => w * h,
    }
}

fn main() {
    let s = Shape::Circle(2.0);
    println!("{}", area(&s));
}
