use std::error::Error;

async fn fetch(_url: &str) -> Result<String, Box<dyn Error + Send + Sync>> {
    Ok(String::from("pengu"))
}

async fn load(url: &str) -> Result<usize, Box<dyn Error + Send + Sync>> {
    let text = fetch(url).await?;
    Ok(text.len())
}

fn main() {
    let future = load("https://example.com");
    println!("future creado: {}", std::mem::size_of_val(&future) > 0);
}
