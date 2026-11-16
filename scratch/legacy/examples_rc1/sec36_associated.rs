trait Container {
    type Item;
    fn first(&self) -> Option<&Self::Item>;
}

struct Numbers {
    values: Vec<i32>,
}

impl Container for Numbers {
    type Item = i32;
    fn first(&self) -> Option<&i32> {
        self.values.first()
    }
}

fn main() {
    let n = Numbers { values: vec![10, 20] };
    println!("{}", n.first().unwrap_or(&0));
}
