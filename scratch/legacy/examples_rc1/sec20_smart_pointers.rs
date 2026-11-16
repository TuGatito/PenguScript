use std::cell::RefCell;
use std::rc::Rc;

struct Node {
    value: i32,
    next: Option<Box<Node>>,
}

fn main() {
    let list = Box::new(Node {
        value: 1,
        next: Some(Box::new(Node { value: 2, next: None })),
    });
    println!("{}", list.value);

    let a = Rc::new(String::from("pengu"));
    let b = Rc::clone(&a);
    println!("{}", Rc::strong_count(&a));
    println!("{}", b);

    let cell = RefCell::new(1);
    *cell.borrow_mut() += 1;
    println!("{}", *cell.borrow());
}
