fn find(items: &[i32], target: i32) -> Option<usize> {
    for (i, item) in items.iter().enumerate() {
        if *item == target {
            return Some(i);
        }
    }
    None
}

fn main() {
    println!("{}", find(&[1, 2, 3], 2).unwrap());
}
