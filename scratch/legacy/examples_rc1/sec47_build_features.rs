#[cfg(debug_assertions)]
fn mode() -> &'static str {
    "debug"
}

#[cfg(not(debug_assertions))]
fn mode() -> &'static str {
    "release"
}

fn main() {
    println!("{}", mode());
    println!("{}", cfg!(debug_assertions));
}
