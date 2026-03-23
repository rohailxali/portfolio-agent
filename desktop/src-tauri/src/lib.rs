use tauri::{
    Manager, SystemTray, SystemTrayMenu, SystemTrayMenuItem,
    CustomMenuItem, SystemTrayEvent,
};
use tauri_plugin_notification::NotificationExt;

/// Expose a command so the frontend can send a desktop notification
/// without needing direct OS access from JS.
#[tauri::command]
async fn send_desktop_notification(
    app: tauri::AppHandle,
    title: String,
    body: String,
) -> Result<(), String> {
    app.notification()
        .builder()
        .title(&title)
        .body(&body)
        .show()
        .map_err(|e| e.to_string())
}

/// Allow frontend to open an external URL in the default browser.
#[tauri::command]
async fn open_url(url: String) -> Result<(), String> {
    open::that(&url).map_err(|e| e.to_string())
}

/// Store and retrieve the API token securely via tauri-plugin-store.
#[tauri::command]
async fn store_token(
    app: tauri::AppHandle,
    token: String,
) -> Result<(), String> {
    let store = app.store("credentials.json").map_err(|e| e.to_string())?;
    store.set("access_token", serde_json::json!(token));
    store.save().map_err(|e| e.to_string())
}

#[tauri::command]
async fn get_stored_token(app: tauri::AppHandle) -> Result<Option<String>, String> {
    let store = app.store("credentials.json").map_err(|e| e.to_string())?;
    let token = store
        .get("access_token")
        .and_then(|v| v.as_str().map(|s| s.to_string()));
    Ok(token)
}

#[tauri::command]
async fn clear_stored_token(app: tauri::AppHandle) -> Result<(), String> {
    let store = app.store("credentials.json").map_err(|e| e.to_string())?;
    store.delete("access_token");
    store.save().map_err(|e| e.to_string())
}

pub fn run() {
    // System tray menu
    let show = CustomMenuItem::new("show", "Show Dashboard");
    let health = CustomMenuItem::new("health", "Check Health");
    let quit = CustomMenuItem::new("quit", "Quit");
    let tray_menu = SystemTrayMenu::new()
        .add_item(show)
        .add_item(health)
        .add_native_item(SystemTrayMenuItem::Separator)
        .add_item(quit);

    let tray = SystemTray::new().with_menu(tray_menu);

    tauri::Builder::default()
        .plugin(tauri_plugin_store::Builder::default().build())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_shell::init())
        .system_tray(tray)
        .on_system_tray_event(|app, event| match event {
            SystemTrayEvent::MenuItemClick { id, .. } => match id.as_str() {
                "show" => {
                    if let Some(window) = app.get_window("main") {
                        window.show().unwrap();
                        window.set_focus().unwrap();
                    }
                }
                "health" => {
                    // Send notification — actual check triggered via frontend polling
                    app.notification()
                        .builder()
                        .title("Portfolio Agent")
                        .body("Health check triggered from tray.")
                        .show()
                        .ok();
                }
                "quit" => std::process::exit(0),
                _ => {}
            },
            SystemTrayEvent::LeftClick { .. } => {
                if let Some(window) = app.get_window("main") {
                    if window.is_visible().unwrap_or(false) {
                        window.hide().unwrap();
                    } else {
                        window.show().unwrap();
                        window.set_focus().unwrap();
                    }
                }
            }
            _ => {}
        })
        .on_window_event(|event| {
            // Minimize to tray instead of closing
            if let tauri::WindowEvent::CloseRequested { api, .. } = event.event() {
                event.window().hide().unwrap();
                api.prevent_close();
            }
        })
        .invoke_handler(tauri::generate_handler![
            send_desktop_notification,
            open_url,
            store_token,
            get_stored_token,
            clear_stored_token,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}