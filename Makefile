.PHONY: help build deploy bump-patch bump-minor bump-major bump-version check-version-sync release-patch release-minor release-major release

help:
	@echo "Available make targets:"
	@echo "  build               - Build both Windows PE and Linux ELF binaries"
	@echo "  deploy              - Deploy binaries to Windows D:\avrig and Linux /opt/avrig"
	@echo "  bump-patch          - Increment SemVer patch version (x.y.Z+1)"
	@echo "  bump-minor          - Increment SemVer minor version (x.Y+1.0)"
	@echo "  bump-major          - Increment SemVer major version (X+1.0.0)"
	@echo "  bump-version        - Set specific SemVer version (usage: make bump-version VERSION=1.2.3)"
	@echo "  check-version-sync  - Validate version parity between Cargo.toml and apps/web/package.json"
	@echo "  release-patch       - Bump patch, commit, tag and push all four repositories"
	@echo "  release-minor       - Bump minor, commit, tag and push all four repositories"
	@echo "  release-major       - Bump major, commit, tag and push all four repositories"
	@echo "  release             - Bump, commit, tag and push all four repositories (VERSION=X.Y.Z)"

bump-patch:
	@powershell -NoProfile -ExecutionPolicy Bypass -File scripts/bump-version.ps1 patch

bump-minor:
	@powershell -NoProfile -ExecutionPolicy Bypass -File scripts/bump-version.ps1 minor

bump-major:
	@powershell -NoProfile -ExecutionPolicy Bypass -File scripts/bump-version.ps1 major

bump-version:
	@if [ -z "$(VERSION)" ]; then \
		powershell -NoProfile -ExecutionPolicy Bypass -Command "Write-Error 'VERSION parameter required, e.g. make bump-version VERSION=1.2.3'"; exit 1; \
	else \
		powershell -NoProfile -ExecutionPolicy Bypass -File scripts/bump-version.ps1 $(VERSION); \
	fi

check-version-sync:
	@powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check-version-sync.ps1

build:
	@powershell -NoProfile -ExecutionPolicy Bypass -Command "cargo build --release"

deploy:
	@echo "Deploying avrig binaries..."

release-patch:
	@powershell -NoProfile -ExecutionPolicy Bypass -File scripts/release.ps1 patch

release-minor:
	@powershell -NoProfile -ExecutionPolicy Bypass -File scripts/release.ps1 minor

release-major:
	@powershell -NoProfile -ExecutionPolicy Bypass -File scripts/release.ps1 major

release:
	@if [ -z "$(VERSION)" ]; then echo "VERSION parameter required, e.g. make release VERSION=1.2.3"; exit 1; else powershell -NoProfile -ExecutionPolicy Bypass -File scripts/release.ps1 $(VERSION); fi
