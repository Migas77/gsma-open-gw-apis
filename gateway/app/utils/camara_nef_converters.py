from app.schemas.common import TimeUnitEnum, Duration
from app.schemas.application_profiles import RateUnitEnum, Rate
from app.schemas.nef_schemas.analytics_exposure import BitRate

UNIT_TO_MILLISECONDS = {
    TimeUnitEnum.Days: 86_400_000.0,
    TimeUnitEnum.Hours: 3_600_000.0,
    TimeUnitEnum.Minutes: 60_000.0,
    TimeUnitEnum.Seconds: 1_000.0,
    TimeUnitEnum.Milliseconds: 1.0,
    TimeUnitEnum.Microseconds: 1e-3,
    TimeUnitEnum.Nanoseconds: 1e-6,
}

_CAMARA_RATE_UNIT_TO_BASE = {
    RateUnitEnum.Bps: 1,
    RateUnitEnum.Kbps: 1_000,
    RateUnitEnum.Mbps: 1_000_000,
    RateUnitEnum.Gbps: 1_000_000_000,
    RateUnitEnum.Tbps: 1_000_000_000_000,
}

_NEF_BITRATE_UNIT_TO_BASE = {
    "bps": 1,
    "Kbps": 1_000,
    "Mbps": 1_000_000,
    "Gbps": 1_000_000_000,
    "Tbps": 1_000_000_000_000,
}

_NEF_UNIT_TO_CAMARA_RATE_UNIT = {
    "bps": RateUnitEnum.Bps,
    "Kbps": RateUnitEnum.Kbps,
    "Mbps": RateUnitEnum.Mbps,
    "Gbps": RateUnitEnum.Gbps,
    "Tbps": RateUnitEnum.Tbps,
}


def convert_duration_to_milliseconds(duration: Duration) -> float:
    assert duration.value is not None and duration.unit is not None
    return duration.value * UNIT_TO_MILLISECONDS[duration.unit]


def pick_higher_rate_unit(
    unit_a: RateUnitEnum,
    unit_b: RateUnitEnum,
) -> RateUnitEnum:
    return max(unit_a, unit_b, key=lambda u: _CAMARA_RATE_UNIT_TO_BASE[u])


def align_rates(
    rate: Rate,                                                 # Camara Rate
    bitrate: BitRate,                                           # NEF Bitrate
) -> tuple[float, float]:
    """Returns (camara_rate_value, nef_bitrate_value) both expressed in the higher of the two units."""
    assert rate.value is not None and rate.unit is not None
    nef_value_str, nef_unit_str = bitrate.split(" ")
    nef_unit = _NEF_UNIT_TO_CAMARA_RATE_UNIT[nef_unit_str]
    target_unit = pick_higher_rate_unit(nef_unit, rate.unit)
    target_unit_base = _CAMARA_RATE_UNIT_TO_BASE[target_unit]
    return (
        rate.value * _CAMARA_RATE_UNIT_TO_BASE[rate.unit] / target_unit_base,
        float(nef_value_str) * _NEF_BITRATE_UNIT_TO_BASE[nef_unit_str] / target_unit_base,
    )

