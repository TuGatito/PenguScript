fn main() {
    let mut acc: i64 = 0;
    for i in 0..50000 { let s = format!("item-{}", i); acc += s.len() as i64; }
    println!("{}", acc);
}
