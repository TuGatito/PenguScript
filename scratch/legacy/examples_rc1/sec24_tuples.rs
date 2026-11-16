fn min_max(a: i32, b: i32) -> (i32, i32) {
    if a <= b { (a, b) } else { (b, a) }
}

fn main() {
    let (low, high) = min_max(7, 3);
    println!("{}", low);
    println!("{}", high);
}
