struct Pair<A, B> {
    first: A,
    second: B,
}

fn identity<T>(value: T) -> T {
    value
}

fn main() {
    let p = Pair { first: 1, second: "one" };
    println!("{}", identity::<i32>(42));
    println!("{}", p.first);
    println!("{}", p.second);
}
