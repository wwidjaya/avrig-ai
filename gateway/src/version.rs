use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq)]
pub struct VersionInfo {
    pub semver: String,
    pub major: u64,
    pub minor: u64,
    pub patch: u64,
    pub prerelease: Option<String>,
    pub build_metadata: Option<String>,
    pub commit_sha: String,
    pub commit_short_sha: String,
    pub build_timestamp: String,
    pub target_triple: String,
    pub dirty: bool,
}

impl VersionInfo {
    pub fn current() -> Self {
        let raw_semver = env!("AVRIG_PKG_VERSION");
        let (major, minor, patch, prerelease, build_metadata) = parse_semver_parts(raw_semver);

        let dirty = match env!("AVRIG_GIT_DIRTY") {
            "true" | "1" => true,
            _ => false,
        };

        Self {
            semver: raw_semver.to_string(),
            major,
            minor,
            patch,
            prerelease,
            build_metadata,
            commit_sha: env!("AVRIG_COMMIT_SHA").to_string(),
            commit_short_sha: env!("AVRIG_COMMIT_SHORT_SHA").to_string(),
            build_timestamp: env!("AVRIG_BUILD_TIMESTAMP").to_string(),
            target_triple: env!("AVRIG_TARGET_TRIPLE").to_string(),
            dirty,
        }
    }

    pub fn verbose_string(&self) -> String {
        format!(
            "avrig {}\ncommit: {}{}\nbuilt:  {}\ntarget: {}",
            self.semver,
            self.commit_sha,
            if self.dirty { " (dirty)" } else { "" },
            self.build_timestamp,
            self.target_triple
        )
    }
}

fn parse_semver_parts(raw: &str) -> (u64, u64, u64, Option<String>, Option<String>) {
    let mut parts = raw.splitn(2, '+');
    let main_and_prerelease = parts.next().unwrap_or(raw);
    let build_metadata = parts.next().map(|s| s.to_string());

    let mut pre_parts = main_and_prerelease.splitn(2, '-');
    let numbers = pre_parts.next().unwrap_or(main_and_prerelease);
    let prerelease = pre_parts.next().map(|s| s.to_string());

    let mut num_iter = numbers.split('.');
    let major = num_iter.next().and_then(|s| s.parse().ok()).unwrap_or(0);
    let minor = num_iter.next().and_then(|s| s.parse().ok()).unwrap_or(0);
    let patch = num_iter.next().and_then(|s| s.parse().ok()).unwrap_or(0);

    (major, minor, patch, prerelease, build_metadata)
}
