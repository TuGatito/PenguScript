mod inner {
    pub struct Public {
        pub value: i32,
    }

    pub fn new(value: i32) -> Public {
        Public { value }
    }

    pub(super) fn show(p: &Public) -> i32 {
        p.value
    }
}

fn main() {
    let p = inner::new(7);
    println!("{}", inner::show(&p));
}
