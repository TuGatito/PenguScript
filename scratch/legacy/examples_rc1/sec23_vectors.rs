fn main() {
    let mut scores = vec![70, 90, 80];
    scores.push(100);
    scores.sort();
    println!("{}", scores.len());
    println!("{}", scores[0]);
    println!("{}", scores.pop().unwrap());
}
