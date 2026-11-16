fn main() {
    let text = String::from("pengu");
    let a = &text;
    let b = &text;
    println!("{}", a.len() + b.len());

    let mut numbers = [1, 2, 3, 4];
    let (left, right) = numbers.split_at_mut(2);
    left[0] = 10;
    right[0] = 30;
    println!("{} {} {} {}", numbers[0], numbers[1], numbers[2], numbers[3]);
}
