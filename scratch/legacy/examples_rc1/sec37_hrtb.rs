fn first(s: &str) -> &str {
    &s[..1]
}

fn apply<F>(f: F, s: &str) -> &str
where
    F: for<'a> Fn(&'a str) -> &'a str,
{
    f(s)
}

fn main() {
    println!("{}", apply(first, "pengu"));
}
