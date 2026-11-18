export interface VersionInfo {
  semver: string;
  major: number;
  minor: number;
  patch: number;
  prerelease?: string | null;
  build_metadata?: string | null;
  commit_sha: string;
  commit_short_sha: string;
  build_timestamp: string;
  target_triple: string;
  dirty: boolean;
}
