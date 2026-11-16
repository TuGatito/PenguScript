fn main() {
    let values = [10, 20, 30, 40, 50];
    let window = &values[1..4];
    println!("{}", window.len());

    let mut total = 0;
    for value in window {
        total += value;
    }
    println!("{}", total);

    for i in 0..3 {
        println!("{}", i);
    }
}
