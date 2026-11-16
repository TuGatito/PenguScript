trait Shape {
    fn area(&self) -> f64;
    fn name(&self) -> &str {
        "shape"
    }
}

struct Circle {
    radius: f64,
}

impl Shape for Circle {
    fn area(&self) -> f64 {
        3.14159 * self.radius * self.radius
    }
    fn name(&self) -> &str {
        "circle"
    }
}

fn main() {
    let s: &dyn Shape = &Circle { radius: 2.0 };
    println!("{}", s.name());
    println!("{}", s.area());
}
