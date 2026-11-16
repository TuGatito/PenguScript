fn make_adder(n: i32) -> impl Fn(i32) -> i32 {
    move |x| x + n
}

fn main() {
    let add5 = make_adder(5);
    println!("{}", add5(3));

    let mut count = 0;
    let mut inc = || count += 1;
    inc();
    drop(inc);
    println!("{}", count);
}
