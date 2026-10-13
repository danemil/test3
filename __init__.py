"""
Inițializarea integrării Rețele Electrice România.

Folosește pattern-ul modern `entry.runtime_data` pentru stocarea
coordinator-ului (disponibil din HA 2024.x).
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import ReteleElectriceCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]

type ReteleElectriceConfigEntry = ConfigEntry[ReteleElectriceCoordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: ReteleElectriceConfigEntry
) -> bool:
    """Configurare intrare: creează coordinator, face primul refresh, setează platformele."""
    _LOGGER.debug("[ReteleElectrice] Setup entry_id=%s", entry.entry_id)

    hass.data.setdefault(DOMAIN, {})

    coordinator = ReteleElectriceCoordinator(hass, entry)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.error("[ReteleElectrice] Prima actualizare eșuată: %s", err)
        raise

    # Stocăm coordinator-ul direct pe entry (pattern modern)
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.debug("[ReteleElectrice] Setup complet pentru entry_id=%s", entry.entry_id)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: ReteleElectriceConfigEntry
) -> bool:
    """Descarcă platformele la eliminarea intrării."""
    _LOGGER.info(
        "[ReteleElectrice] ── async_unload_entry ── entry_id=%s",
        entry.entry_id,
    )

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    _LOGGER.debug(
        "[ReteleElectrice] Unload platforme: %s", "OK" if unload_ok else "EȘUAT"
    )

    if not unload_ok:
        _LOGGER.error(
            "[ReteleElectrice] Unload EȘUAT pentru entry_id=%s", entry.entry_id
        )
        return unload_ok

    # Închide sesiunea API
    coordinator = getattr(entry, "runtime_data", None)
    if coordinator and hasattr(coordinator, "api"):
        await coordinator.api.async_close()

    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)

    # Curăță domeniul complet dacă nu mai există alte intrări
    entry_ids_ramase = {
        e.entry_id
        for e in hass.config_entries.async_entries(DOMAIN)
        if e.entry_id != entry.entry_id
    }

    if not entry_ids_ramase:
        _LOGGER.info(
            "[ReteleElectrice] Ultima entry descărcată — curăț domeniul complet"
        )
        hass.data.pop(DOMAIN, None)

    return unload_ok
