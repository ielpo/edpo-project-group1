use rand::Rng;
use rdkafka::config::ClientConfig;
use rdkafka::producer::{FutureProducer, FutureRecord};
use rdkafka::util::Timeout;
use serde::Deserialize;
use serde_json::json;
use std::sync::Arc;
use std::time::Duration;
use warp::Filter;

const KAFKA_BROKERS: &str = "localhost:9092";
const COLOR_TOPIC: &str = "sensor.color.raw.v1";

// RGB profiles that BlockColor.from() in kafka-streams will classify correctly
const COLOR_PROFILES: [(u8, u8, u8); 4] = [
    (200, 50, 50),  // RED:    r > g, r > b
    (50, 200, 50),  // GREEN:  g > r, g > b
    (50, 50, 200),  // BLUE:   b > r, b > g
    (200, 180, 50), // YELLOW: r > g > b
];

#[derive(Deserialize)]
struct ActivateRequest {
    #[serde(rename = "cubeId")]
    cube_id: String,
    readings: Option<u32>,
    #[serde(rename = "intervalMs")]
    interval_ms: Option<u64>,
}

#[tokio::main]
async fn main() {
    let producer: Arc<FutureProducer> = Arc::new(
        ClientConfig::new()
            .set("bootstrap.servers", KAFKA_BROKERS)
            .create()
            .expect("Failed to create Kafka producer"),
    );

    // GET /color — legacy single-shot endpoint
    let color_route = warp::path("color")
        .and(warp::get())
        .map(|| {
            let mut rng = rand::rng();
            let r: u8 = rng.random();
            let g: u8 = rng.random();
            let b: u8 = rng.random();
            warp::reply::json(&json!({"r": r, "g": g, "b": b}))
        });

    // POST /activate — start publishing colour readings for a block to Kafka
    let activate_route = {
        let producer = Arc::clone(&producer);
        warp::path("activate")
            .and(warp::post())
            .and(warp::body::json())
            .map(move |req: ActivateRequest| {
                let producer = Arc::clone(&producer);
                let readings = req.readings.unwrap_or(10);
                let interval_ms = req.interval_ms.unwrap_or(200);
                let cube_id = req.cube_id;

                // Pick a stable colour profile for this activation
                let idx = rand::rng().random_range(0..COLOR_PROFILES.len());
                let (r, g, b) = COLOR_PROFILES[idx];

                let cube_id_task = cube_id.clone();
                tokio::spawn(async move {
                    for _ in 0..readings {
                        let payload =
                            json!({"cubeId": cube_id_task, "r": r, "g": g, "b": b}).to_string();
                        let record = FutureRecord::to(COLOR_TOPIC)
                            .key(cube_id_task.as_str())
                            .payload(payload.as_str());
                        let _ = producer
                            .send(record, Timeout::After(Duration::from_secs(5)))
                            .await;
                        tokio::time::sleep(Duration::from_millis(interval_ms)).await;
                    }
                });

                warp::reply::json(&json!({"status": "activated", "cubeId": cube_id}))
            })
    };

    warp::serve(color_route.or(activate_route))
        .run(([0, 0, 0, 0], 8202))
        .await;
}
