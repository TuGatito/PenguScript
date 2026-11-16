struct Token {
    id: i32,
}

fn main() {
    let a = Token { id: 1 };
    let b = a;
    println!("{}", b.id);

    let x = 10;
    let y = x;
    println!("{}", x + y);
}
