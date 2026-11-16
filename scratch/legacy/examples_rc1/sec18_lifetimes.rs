fn longest<'a>(a: &'a str, b: &'a str) -> &'a str {
    if a.len() >= b.len() { a } else { b }
}

fn main() {
    let a = "pengu";
    let b = "script";
    println!("{}", longest(a, b));
}
