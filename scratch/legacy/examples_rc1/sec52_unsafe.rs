unsafe fn read(ptr: *const i32) -> i32 {
    unsafe { *ptr }
}

fn main() {
    let value = 41;
    let ptr: *const i32 = &value;
    println!("{}", unsafe { read(ptr) });
}
