type Meters = f64;

struct UserId(u32);

fn main() {
    let distance: Meters = 3.5;
    let id = UserId(7);
    let a: i32 = 300;
    let small = a as u8;

    println!("{}", distance);
    println!("{}", id.0);
    println!("{}", small);
}
