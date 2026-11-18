use anyhow::Result;
use chatgpt_oauth_test::jev_adapter::{CANONICAL_MOODS, JevConfig, JevDecisionClient};

#[tokio::main]
async fn main() -> Result<()> {
    dotenvy::dotenv().ok();

    println!("=== JEV Decision Model Adapter (System One) Test ===");

    let sample_text = "The rain fell silently across the deserted platform, blurring the taillights into streaks of amber as the last train vanished into the night.";
    println!("\nSample Input Text:\n\"{}\"\n", sample_text);

    // Build the request payload
    let req = JevDecisionClient::build_mood_request("jev-1.13", sample_text);
    let serialized = serde_json::to_string_pretty(&req)?;
    println!("Constructed System One Request Payload:\n{}\n", serialized);

    // Check if API key is provided for a live run
    match JevConfig::from_env() {
        Ok(config) => {
            println!(
                "API key found. Running live request to: {}",
                config.endpoint
            );
            println!("Model: {}", config.model);

            let client = JevDecisionClient::new(config)?;
            match client.classify_mood(sample_text).await {
                Ok(moods) => {
                    println!("\nLive Classification Result (Normalized Probabilities):");
                    for mood in &CANONICAL_MOODS {
                        println!("  {:12}: {:.4}", mood, moods.get(*mood).unwrap_or(&0.0));
                    }
                }
                Err(e) => {
                    eprintln!("Live request error: {}", e);
                }
            }
        }
        Err(_) => {
            println!("OPENCODE_API_KEY / SYSTEMONE_API_KEY not set in environment.");
            println!("Simulating offline mock response parsing & verification...");

            let mock_response_json = r#"{
                "model": "jev-1.13",
                "answers": {
                    "mood": {
                        "type": "choice",
                        "choice": "melancholy",
                        "confidence": 0.8452,
                        "probabilities": {
                            "melancholy": 0.845213,
                            "dark": 0.10214,
                            "calm": 0.04118,
                            "quirky": 0.00621,
                            "romantic": 0.00312,
                            "energetic": 0.002137
                        }
                    }
                }
            }"#;

            let parsed: chatgpt_oauth_test::jev_adapter::SystemOneResponse =
                serde_json::from_str(mock_response_json)?;
            let mood_answer = parsed.answers.get("mood").unwrap();
            let normalized = JevDecisionClient::normalize_mood_probabilities(mood_answer);

            println!("\nNormalized Mock Output Probabilities (4 decimal places):");
            for mood in &CANONICAL_MOODS {
                println!(
                    "  {:12}: {:.4}",
                    mood,
                    normalized.get(*mood).unwrap_or(&0.0)
                );
            }
        }
    }

    Ok(())
}
