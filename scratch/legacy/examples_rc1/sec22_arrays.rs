fn main() {
    let scores = [90, 80, 70];

    let total = scores[0] + scores[1] + scores[2];
    println!("{}", total);

    let average = total / scores.len() as i32;
    println!("{}", average);

    let top = &scores[0..2];
    println!("{}", top.len());
}
