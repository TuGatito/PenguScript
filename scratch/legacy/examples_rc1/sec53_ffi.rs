#[link(name = "m")]
unsafe extern "C" {
    fn cos(x: f64) -> f64;
}

fn main() {
    println!("{}", unsafe { cos(0.0) });
}
