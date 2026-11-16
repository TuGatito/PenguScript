#[repr(C)]
struct Pair {
    a: u8,
    b: u32,
}

fn main() {
    println!("{}", std::mem::size_of::<Pair>());
    println!("{}", std::mem::align_of::<Pair>());
}
