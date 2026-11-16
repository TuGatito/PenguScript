fn main() {
    let values = [1, 2, 3, 4, 5];
    let doubled: Vec<i32> = values.iter().map(|x| *x * 2).collect();
    println!("{:?}", doubled);
}
