//! What a parcel costs to send, in cents.

use std::fmt;

pub const MAX_WEIGHT_GRAMS: u32 = 30_000;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Zone {
    Local,
    National,
    Abroad,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FeeError {
    EmptyParcel,
    TooHeavy,
}

impl FeeError {
    /// The code the screen maps to a message.
    pub fn code(self) -> &'static str {
        match self {
            FeeError::EmptyParcel => "EMPTY_PARCEL",
            FeeError::TooHeavy => "TOO_HEAVY",
        }
    }
}

impl fmt::Display for FeeError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.code())
    }
}

impl std::error::Error for FeeError {}

/// A base price per zone, plus a price per started kilogram.
pub fn quote(weight_grams: u32, zone: Zone) -> Result<u32, FeeError> {
    if weight_grams == 0 {
        return Err(FeeError::EmptyParcel);
    }
    if weight_grams > MAX_WEIGHT_GRAMS {
        return Err(FeeError::TooHeavy);
    }
    let (base, per_kilogram) = match zone {
        Zone::Local => (350, 50),
        Zone::National => (590, 120),
        Zone::Abroad => (1490, 400),
    };
    Ok(base + per_kilogram * weight_grams.div_ceil(1000))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_started_kilogram_is_charged_whole() {
        assert_eq!(quote(1, Zone::Local), Ok(400));
        assert_eq!(quote(1000, Zone::Local), Ok(400));
        assert_eq!(quote(1001, Zone::Local), Ok(450));
    }

    #[test]
    fn each_zone_has_its_own_price() {
        assert_eq!(quote(2000, Zone::National), Ok(830));
        assert_eq!(quote(2000, Zone::Abroad), Ok(2290));
    }

    #[test]
    fn an_empty_parcel_is_refused() {
        assert_eq!(quote(0, Zone::Local), Err(FeeError::EmptyParcel));
    }

    #[test]
    fn a_parcel_over_the_limit_is_refused() {
        assert_eq!(quote(MAX_WEIGHT_GRAMS, Zone::Abroad), Ok(13_490));
        assert_eq!(quote(MAX_WEIGHT_GRAMS + 1, Zone::Abroad), Err(FeeError::TooHeavy));
    }
}
