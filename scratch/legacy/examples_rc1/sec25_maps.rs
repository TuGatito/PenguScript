use std::collections::HashMap;

fn main() {
    let text = "pengu pengu seal";
    let mut counts = HashMap::new();

    for word in text.split_whitespace() {
        let count = counts.entry(word).or_insert(0);
        *count += 1;
    }

    println!("{}", counts.len());
    println!("{}", counts.get("pengu").unwrap());
}
