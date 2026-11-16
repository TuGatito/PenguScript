mod app {
    pub fn answer() -> i32 {
        42
    }
}

fn main() {
    println!("{}", app::answer());
}
