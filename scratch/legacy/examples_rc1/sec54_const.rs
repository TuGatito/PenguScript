const LIMIT: i32 = 64;

const fn square(x: i32) -> i32 {
    x * x
}

fn main() {
    let answer = const { square(8) + 1 };
    println!("{}", LIMIT);
    println!("{}", answer);
}
