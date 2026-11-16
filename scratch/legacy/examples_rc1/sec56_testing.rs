fn add(a: i32, b: i32) -> i32 {
    a + b
}

#[test]
fn add_works() {
    assert_eq!(add(2, 3), 5);
}

fn main() {
    assert_eq!(add(2, 3), 5);
}
