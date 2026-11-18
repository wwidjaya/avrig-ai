use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

fn main() {
    let pkg_version = std::env::var("CARGO_PKG_VERSION").unwrap_or_else(|_| "0.0.0".to_string());
    println!("cargo:rustc-env=AVRIG_PKG_VERSION={}", pkg_version);

    let target_triple = std::env::var("TARGET").unwrap_or_else(|_| "unknown".to_string());
    println!("cargo:rustc-env=AVRIG_TARGET_TRIPLE={}", target_triple);

    // Git commit SHA and branch detection
    let mut commit_sha = "unknown".to_string();
    let mut commit_short_sha = "unknown".to_string();
    let mut git_branch = "detached".to_string();
    let mut dirty = false;

    // First allow manual override via AVRIG_GIT_SHA environment variable
    if let Ok(env_sha) = std::env::var("AVRIG_GIT_SHA") {
        if !env_sha.trim().is_empty() {
            commit_sha = env_sha.trim().to_string();
            commit_short_sha = commit_sha.chars().take(7).collect();
        }
    }

    if commit_sha == "unknown" {
        if let Ok(output) = Command::new("git").args(["rev-parse", "HEAD"]).output() {
            if output.status.success() {
                if let Ok(sha) = String::from_utf8(output.stdout) {
                    let s = sha.trim().to_string();
                    if !s.is_empty() {
                        commit_sha = s.clone();
                        commit_short_sha = s.chars().take(7).collect();
                    }
                }
            }
        }
    }

    if let Ok(output) = Command::new("git").args(["rev-parse", "--abbrev-ref", "HEAD"]).output() {
        if output.status.success() {
            if let Ok(branch) = String::from_utf8(output.stdout) {
                let b = branch.trim().to_string();
                if !b.is_empty() {
                    git_branch = b;
                }
            }
        }
    }

    if let Ok(output) = Command::new("git").args(["status", "--porcelain"]).output() {
        if output.status.success() {
            if let Ok(status) = String::from_utf8(output.stdout) {
                dirty = !status.trim().is_empty();
            }
        }
    }

    // Build timestamp in ISO 8601 UTC format
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();

    let build_timestamp = format_timestamp_utc(now);

    println!("cargo:rustc-env=AVRIG_COMMIT_SHA={}", commit_sha);
    println!("cargo:rustc-env=AVRIG_COMMIT_SHORT_SHA={}", commit_short_sha);
    println!("cargo:rustc-env=AVRIG_GIT_BRANCH={}", git_branch);
    println!("cargo:rustc-env=AVRIG_GIT_DIRTY={}", dirty);
    println!("cargo:rustc-env=AVRIG_BUILD_TIMESTAMP={}", build_timestamp);

    // Watch git state if .git exists
    if std::path::Path::new("../.git").exists() {
        println!("cargo:rerun-if-changed=../.git/HEAD");
        println!("cargo:rerun-if-changed=../.git/index");
    } else if std::path::Path::new(".git").exists() {
        println!("cargo:rerun-if-changed=.git/HEAD");
        println!("cargo:rerun-if-changed=.git/index");
    }
}

fn format_timestamp_utc(secs: u64) -> String {
    let days = secs / 86400;
    let rem_secs = secs % 86400;
    let hours = rem_secs / 3600;
    let minutes = (rem_secs % 3600) / 60;
    let seconds = rem_secs % 60;

    let (year, month, day) = days_to_ymd(days);
    format!(
        "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}Z",
        year, month, day, hours, minutes, seconds
    )
}

fn days_to_ymd(days: u64) -> (u64, u64, u64) {
    let d = (days as i64) + 719468;
    let era = if d >= 0 { d } else { d - 146096 } / 146097;
    let doe = d - era * 146097;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let day = doy - (153 * mp + 2) / 5 + 1;
    let month = mp + (if mp < 10 { 3 } else { -9 });
    let year = y + (if month <= 2 { 1 } else { 0 });
    (year as u64, month as u64, day as u64)
}
