#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default)]
struct Id {
    value: u32,
}

fn main() {
    let a = Id { value: 7 };
    let b = a;
    println!("{} {:?}", a == b, b);
}
