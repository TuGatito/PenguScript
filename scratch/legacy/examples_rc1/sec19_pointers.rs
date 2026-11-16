unsafe fn read(p: *const i32) -> i32 {
    unsafe { *p }
}

fn main() {
    let value = 42;
    let p = &raw const value;
    let copy = unsafe { *p };
    println!("{}", copy);
}
