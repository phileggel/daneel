mod fees;

pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![fees::api::quote_fee])
        .run(tauri::generate_context!())
        .expect("the window could not start");
}
