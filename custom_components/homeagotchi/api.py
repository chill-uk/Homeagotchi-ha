"""HTTP API views for Homeagotchi."""

from __future__ import annotations

from typing import Any

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.helpers.json import json_dumps

from .const import DOMAIN
from .coordinator import HomeagotchiCoordinator


def async_register_views(hass: HomeAssistant) -> None:
    """Register Homeagotchi HTTP views once."""

    if hass.data.setdefault(DOMAIN, {}).get("views_registered"):
        return

    hass.http.register_view(HomeagotchiStateView)
    hass.http.register_view(HomeagotchiAckView)
    hass.data[DOMAIN]["views_registered"] = True


class HomeagotchiStateView(HomeAssistantView):
    """Return the current Homeagotchi state."""

    url = "/api/homeagotchi/state"
    name = "api:homeagotchi:state"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """Handle state requests."""

        coordinator = _coordinator(request)
        if coordinator is None:
            return _json_response({"error": "Homeagotchi is not configured"}, status=404)

        await coordinator.async_update()
        return _json_response(coordinator.state)


class HomeagotchiAckView(HomeAssistantView):
    """Acknowledge the current Homeagotchi scene."""

    url = "/api/homeagotchi/ack"
    name = "api:homeagotchi:ack"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        """Handle acknowledgement requests."""

        coordinator = _coordinator(request)
        if coordinator is None:
            return _json_response({"error": "Homeagotchi is not configured"}, status=404)

        try:
            payload = await request.json()
        except ValueError:
            return _json_response({"error": "Invalid JSON"}, status=400)

        scene = str(payload.get("scene") or coordinator.state["scene"])
        response = await coordinator.async_acknowledge(scene)
        return _json_response(response)


def _coordinator(request: web.Request) -> HomeagotchiCoordinator | None:
    hass: HomeAssistant = request.app["hass"]
    return hass.data.get(DOMAIN, {}).get("coordinator")


def _json_response(payload: dict[str, Any], status: int = 200) -> web.Response:
    return web.Response(
        text=json_dumps(payload),
        status=status,
        content_type="application/json",
    )
