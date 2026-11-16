fn main() {
    let nums = [1, 2, 3, 4];
    let doubled = nums.iter().map(|x| *x * 2).collect::<Vec<i32>>();
    println!("{:?}", doubled);

    let value: Option<i32> = Some(3);
    println!("{}", value.map(|x| x * 2).unwrap_or(0));
}
