use warp::Filter;
use rand::prelude::*;

#[tokio::main]
async fn main() {
    // Define the `/color` route
    let color_route = warp::path("color")
        .map(|| {
            let mut rng = rand::rng();
            let r: u8 = rng.random();
            let g: u8 = rng.random();
            let b: u8 = rng.random();

            warp::reply::json(&serde_json::json!({
                "r": r,
                "g": g,
                "b": b
            }))
        });

    // Start the warp server
    warp::serve(color_route)
        .run(([0, 0, 0, 0], 3030))
        .await;
}
