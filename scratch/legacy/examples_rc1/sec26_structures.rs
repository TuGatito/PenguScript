use std::collections::BinaryHeap;

fn main() {
    let mut tasks = BinaryHeap::new();
    tasks.push(2);
    tasks.push(5);
    tasks.push(1);

    println!("{}", tasks.pop().unwrap());
    println!("{}", tasks.pop().unwrap());
    println!("{}", tasks.pop().unwrap());
}
