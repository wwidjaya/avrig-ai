fn main() {
    // If icons are missing, avoid failing during tauri_build on Windows
    let icon_path = std::path::Path::new("icons/icon.ico");
    if !icon_path.exists() {
        if let Some(parent) = icon_path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        // Write minimal 1x1 ICO file header and bitmap
        let minimal_ico: [u8; 22] = [
            0, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 32, 0, 0, 0, 0, 0, 22, 0, 0, 0
        ];
        let _ = std::fs::write(icon_path, minimal_ico);
    }
    tauri_build::build()
}
