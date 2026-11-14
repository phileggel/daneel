//! The fee commands: the IPC boundary, with no rule of its own.

use acme_core::fees::{quote, Zone};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ZoneArg {
    Local,
    National,
    Abroad,
}

#[derive(Debug, Serialize)]
pub struct FeeErrorDto {
    code: &'static str,
}

#[tauri::command]
pub fn quote_fee(weight_grams: u32, zone: ZoneArg) -> Result<u32, FeeErrorDto> {
    let zone = match zone {
        ZoneArg::Local => Zone::Local,
        ZoneArg::National => Zone::National,
        ZoneArg::Abroad => Zone::Abroad,
    };
    quote(weight_grams, zone).map_err(|error| FeeErrorDto { code: error.code() })
}
