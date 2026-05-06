"""State calculation for Homeagotchi."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt as dt_util

from .const import (
    ACK_SUPPRESS_MINUTES,
    CONF_BIN_ENTITY,
    CONF_DRYER_ENTITY,
    CONF_ENERGY_PRICE_ENTITY,
    CONF_ENERGY_PRICE_HIGH,
    CONF_IGNORED_DELAY_MINUTES,
    CONF_LIGHT_ENTITIES,
    CONF_QUIET_HOURS_END,
    CONF_QUIET_HOURS_START,
    CONF_WASHING_MACHINE_ENTITY,
    CONF_WEATHER_ENTITY,
    DEFAULT_ATTENTION_LED_BRIGHTNESS,
    DEFAULT_IGNORED_DELAY_MINUTES,
    DEFAULT_LED_BRIGHTNESS,
    DEFAULT_QUIET_HOURS_END,
    DEFAULT_QUIET_HOURS_START,
    DEFAULT_URGENT_LED_BRIGHTNESS,
)


@dataclass(slots=True)
class SourceSnapshot:
    """Normalized source states used by the scene engine."""

    now: datetime
    weather: str | None = None
    washing_machine: str | None = None
    washing_machine_last_changed: datetime | None = None
    dryer: str | None = None
    lights_on: bool = False
    bin_state: str | None = None
    energy_price: str | None = None
    energy_price_value: float | None = None
    energy_price_high: float | None = None
    ignored_delay_minutes: int = DEFAULT_IGNORED_DELAY_MINUTES
    quiet_hours_start: time = DEFAULT_QUIET_HOURS_START
    quiet_hours_end: time = DEFAULT_QUIET_HOURS_END
    acknowledged: dict[str, datetime] = field(default_factory=dict)


class HomeagotchiCoordinator:
    """Own Homeagotchi state and acknowledgement timestamps."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._listeners: list[Callable[[], None]] = []
        self.acknowledged: dict[str, datetime] = {}
        self.state: dict[str, Any] = calculate_state(
            SourceSnapshot(now=dt_util.utcnow())
        )

    @callback
    def async_add_listener(self, update_callback: Callable[[], None]) -> Callable[[], None]:
        """Register a listener for state updates."""

        self._listeners.append(update_callback)

        @callback
        def _remove_listener() -> None:
            self._listeners.remove(update_callback)

        return _remove_listener

    async def async_update(self) -> None:
        """Recalculate Homeagotchi state from current Home Assistant states."""

        self.state = calculate_state(self._snapshot())
        for listener in list(self._listeners):
            listener()

    async def async_acknowledge(self, scene: str) -> dict[str, Any]:
        """Acknowledge the active scene and refresh the exposed state."""

        self.acknowledged[scene] = dt_util.utcnow()
        async_call_later(
            self.hass,
            ACK_SUPPRESS_MINUTES * 60,
            lambda _now: self.acknowledged.pop(scene, None),
        )
        await self.async_update()
        return {"ok": True, "acknowledged_scene": scene}

    def _snapshot(self) -> SourceSnapshot:
        """Build a normalized snapshot from configured entities."""

        data = {**self.entry.data, **self.entry.options}

        washer_state = self._state(data.get(CONF_WASHING_MACHINE_ENTITY))
        energy_state = self._state(data.get(CONF_ENERGY_PRICE_ENTITY))
        energy_value = _as_float(energy_state)

        washer_entity = self.hass.states.get(data.get(CONF_WASHING_MACHINE_ENTITY))

        return SourceSnapshot(
            now=dt_util.utcnow(),
            weather=self._state(data.get(CONF_WEATHER_ENTITY)),
            washing_machine=washer_state,
            washing_machine_last_changed=(
                washer_entity.last_changed if washer_entity is not None else None
            ),
            dryer=self._state(data.get(CONF_DRYER_ENTITY)),
            lights_on=self._any_lights_on(data.get(CONF_LIGHT_ENTITIES) or []),
            bin_state=self._state(data.get(CONF_BIN_ENTITY)),
            energy_price=energy_state,
            energy_price_value=energy_value,
            energy_price_high=_as_float(data.get(CONF_ENERGY_PRICE_HIGH)),
            ignored_delay_minutes=int(
                data.get(CONF_IGNORED_DELAY_MINUTES, DEFAULT_IGNORED_DELAY_MINUTES)
            ),
            quiet_hours_start=_parse_time(
                data.get(CONF_QUIET_HOURS_START),
                DEFAULT_QUIET_HOURS_START,
            ),
            quiet_hours_end=_parse_time(
                data.get(CONF_QUIET_HOURS_END),
                DEFAULT_QUIET_HOURS_END,
            ),
            acknowledged=self.acknowledged,
        )

    def _state(self, entity_id: str | None) -> str | None:
        """Return a lower-case entity state, if available."""

        if not entity_id:
            return None

        state = self.hass.states.get(entity_id)
        if state is None:
            return None

        return str(state.state).lower()

    def _any_lights_on(self, entity_ids: list[str]) -> bool:
        """Return whether any configured light entity is on."""

        return any(self._state(entity_id) == "on" for entity_id in entity_ids)


def calculate_state(snapshot: SourceSnapshot) -> dict[str, Any]:
    """Calculate a compact Homeagotchi state object from source states."""

    if _laundry_ignored(snapshot):
        return _state(
            "laundry_ignored",
            "angry",
            "Still waiting",
            "Move the washing please",
            {"left": "washer", "right": "dryer", "arrow": True},
            {
                "color": "red",
                "mode": "fast_pulse",
                "brightness": DEFAULT_URGENT_LED_BRIGHTNESS,
                "speed": "fast",
            },
            snapshot,
        )

    if snapshot.lights_on:
        return _state(
            "lights_left_on",
            "frustrated",
            "Lights are on",
            "A room still has lights on",
            {"left": "bulb", "right": "warning", "arrow": False},
            {
                "color": "yellow",
                "mode": "slow_pulse",
                "brightness": DEFAULT_ATTENTION_LED_BRIGHTNESS,
                "speed": "slow",
            },
            snapshot,
        )

    if _bin_due(snapshot.bin_state):
        return _state(
            "bins_due",
            "frustrated",
            "Bins due",
            "Take the bins out",
            {"left": "bin", "right": "warning", "arrow": False},
            {
                "color": "yellow",
                "mode": "slow_pulse",
                "brightness": DEFAULT_ATTENTION_LED_BRIGHTNESS,
                "speed": "slow",
            },
            snapshot,
        )

    if snapshot.washing_machine == "done":
        return _state(
            "laundry_done",
            "frustrated",
            "Laundry ready",
            "Move washing to dryer",
            {"left": "washer", "right": "dryer", "arrow": True},
            {
                "color": "orange",
                "mode": "pulse",
                "brightness": DEFAULT_ATTENTION_LED_BRIGHTNESS,
                "speed": "slow",
            },
            snapshot,
        )

    if _energy_expensive(snapshot):
        return _state(
            "energy_expensive",
            "sad",
            "Energy is pricey",
            "Maybe wait before running appliances",
            {"left": "energy", "right": "warning", "arrow": False},
            {
                "color": "orange",
                "mode": "slow_pulse",
                "brightness": DEFAULT_ATTENTION_LED_BRIGHTNESS,
                "speed": "slow",
            },
            snapshot,
        )

    if snapshot.washing_machine == "running":
        return _state(
            "laundry_running",
            "neutral",
            "Laundry running",
            "The washing is on",
            {"left": "washer", "right": None, "arrow": False},
            {
                "color": "white",
                "mode": "solid",
                "brightness": DEFAULT_LED_BRIGHTNESS,
                "speed": "slow",
            },
            snapshot,
        )

    if _weather_sunny(snapshot.weather):
        return _state(
            "sunny",
            "happy",
            "Sunny",
            "A good day for the house",
            {"left": "sun", "right": None, "arrow": False},
            {
                "color": "green",
                "mode": "solid",
                "brightness": DEFAULT_LED_BRIGHTNESS,
                "speed": "slow",
            },
            snapshot,
        )

    if _weather_sad(snapshot.weather):
        return _state(
            "idle",
            "sad",
            "Grey outside",
            "Homeagotchi is keeping cozy",
            {"left": "cloud", "right": "rain", "arrow": False},
            {
                "color": "blue",
                "mode": "solid",
                "brightness": DEFAULT_LED_BRIGHTNESS,
                "speed": "slow",
            },
            snapshot,
        )

    if _is_quiet_hours(snapshot.now, snapshot.quiet_hours_start, snapshot.quiet_hours_end):
        return _state(
            "night_mode",
            "sleeping",
            "Good night",
            "Homeagotchi is sleeping",
            {"left": "none", "right": None, "arrow": False},
            {"color": "blue", "mode": "off", "brightness": 0.0, "speed": "slow"},
            snapshot,
        )

    return _state(
        "idle",
        "neutral",
        "All quiet",
        "Nothing needs attention",
        {"left": "none", "right": None, "arrow": False},
        {
            "color": "white",
            "mode": "solid",
            "brightness": DEFAULT_LED_BRIGHTNESS,
            "speed": "slow",
        },
        snapshot,
    )


def _state(
    scene: str,
    emotion: str,
    title: str,
    message: str,
    props: dict[str, Any],
    led: dict[str, Any],
    snapshot: SourceSnapshot,
) -> dict[str, Any]:
    """Build the public state payload."""

    return {
        "scene": scene,
        "emotion": emotion,
        "title": title,
        "message": message,
        "props": props,
        "led": led,
        "status": {
            "weather": _weather_status(snapshot.weather),
            "laundry": _laundry_status(snapshot.washing_machine),
            "lights": "on" if snapshot.lights_on else "ok",
            "bins": "due_today" if _bin_due(snapshot.bin_state) else "ok",
            "energy": "expensive" if _energy_expensive(snapshot) else "normal",
        },
        "updated_at": snapshot.now.isoformat().replace("+00:00", "Z"),
    }


def _laundry_ignored(snapshot: SourceSnapshot) -> bool:
    """Return whether finished laundry should escalate."""

    if snapshot.washing_machine != "done" or snapshot.washing_machine_last_changed is None:
        return False

    acknowledged_at = snapshot.acknowledged.get("laundry_done") or snapshot.acknowledged.get(
        "laundry_ignored"
    )
    if acknowledged_at is not None and snapshot.now - acknowledged_at < timedelta(
        minutes=ACK_SUPPRESS_MINUTES
    ):
        return False

    return snapshot.now - snapshot.washing_machine_last_changed > timedelta(
        minutes=snapshot.ignored_delay_minutes
    )


def _energy_expensive(snapshot: SourceSnapshot) -> bool:
    """Return whether energy price should trigger a reminder."""

    if snapshot.energy_price in {"expensive", "high", "peak"}:
        return True

    return (
        snapshot.energy_price_value is not None
        and snapshot.energy_price_high is not None
        and snapshot.energy_price_value >= snapshot.energy_price_high
    )


def _bin_due(bin_state: str | None) -> bool:
    return bin_state in {"on", "due", "due_today", "today", "true"}


def _weather_sunny(weather: str | None) -> bool:
    return weather in {"sunny", "clear", "clear-night"}


def _weather_sad(weather: str | None) -> bool:
    return weather in {"rainy", "pouring", "snowy", "snowy-rainy", "hail", "lightning"}


def _weather_status(weather: str | None) -> str:
    if _weather_sunny(weather):
        return "sunny"
    if _weather_sad(weather):
        return "bad"
    return weather or "unknown"


def _laundry_status(washing_machine: str | None) -> str:
    if washing_machine in {"running", "done"}:
        return washing_machine
    return "ok"


def _is_quiet_hours(now: datetime, start: time, end: time) -> bool:
    current = now.time()
    if start < end:
        return start <= current < end
    return current >= start or current < end


def _parse_time(value: Any, fallback: time) -> time:
    if isinstance(value, time):
        return value
    if not isinstance(value, str):
        return fallback

    try:
        hour, minute = value.split(":", 1)
        return time(int(hour), int(minute))
    except (TypeError, ValueError):
        return fallback


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
