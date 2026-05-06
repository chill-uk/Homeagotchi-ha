# Homeagotchi Home Assistant Integration

Homeagotchi is a custom Home Assistant integration for an ESP32 e-ink virtual pet. Home Assistant owns the decision-making and exposes one compact state payload. The ESP32 stays focused on rendering the hamster, props, text, and NeoPixels.

## MVP Features

- HACS-style custom integration under `custom_components/homeagotchi`.
- Config flow for selecting source entities.
- Authenticated JSON endpoint at `GET /api/homeagotchi/state`.
- Authenticated acknowledgement endpoint at `POST /api/homeagotchi/ack`.
- Scene, emotion, message, prop, LED, and status calculation.
- Debug sensors:
  - `sensor.homeagotchi_scene`
  - `sensor.homeagotchi_emotion`
  - `sensor.homeagotchi_message`
  - `sensor.homeagotchi_led_color`
  - `sensor.homeagotchi_led_mode`
  - `sensor.homeagotchi_last_update`

## Install Locally

Copy this repository into your Home Assistant `custom_components` path so the integration lives at:

```text
custom_components/homeagotchi/
```

Restart Home Assistant, then add **Homeagotchi** from **Settings > Devices & services > Add integration**.

For the MVP, all source entities are optional. If nothing is configured, Homeagotchi returns an idle state.

## Configured Entities

The config flow can watch:

- Weather entity
- Washing machine state sensor
- Dryer state sensor
- Light entities
- Bin collection calendar or sensor
- Energy price sensor
- Expensive energy threshold
- Ignored delay in minutes
- Quiet hours start and end

The washing machine sensor currently recognizes:

```text
running
done
```

Bin collection recognizes:

```text
on
due
due_today
today
true
```

Energy price can be a state string of `expensive`, `high`, or `peak`, or a numeric value greater than or equal to the configured expensive threshold.

## ESP32 JSON Contract

The ESP32 should poll:

```http
GET /api/homeagotchi/state
Authorization: Bearer <HOME_ASSISTANT_LONG_LIVED_ACCESS_TOKEN>
```

Example response:

```json
{
  "scene": "laundry_done",
  "emotion": "frustrated",
  "title": "Laundry ready",
  "message": "Move washing to dryer",
  "props": {
    "left": "washer",
    "right": "dryer",
    "arrow": true
  },
  "led": {
    "color": "orange",
    "mode": "pulse",
    "brightness": 0.2,
    "speed": "slow"
  },
  "status": {
    "weather": "sunny",
    "laundry": "done",
    "lights": "ok",
    "bins": "ok",
    "energy": "normal"
  },
  "updated_at": "2026-05-05T13:00:00Z"
}
```

The ESP32 should treat `scene`, `emotion`, `props`, and `led` as asset and behavior IDs. It should not need to know Home Assistant entity IDs.

## Acknowledgement

The ESP32 button can acknowledge the current scene:

```http
POST /api/homeagotchi/ack
Authorization: Bearer <HOME_ASSISTANT_LONG_LIVED_ACCESS_TOKEN>
Content-Type: application/json
```

```json
{
  "scene": "laundry_done",
  "action": "acknowledge"
}
```

Example response:

```json
{
  "ok": true,
  "acknowledged_scene": "laundry_done"
}
```

Acknowledging `laundry_done` suppresses the ignored-laundry escalation for 30 minutes.

## Scene Priority

Only one scene is active at a time. The MVP priority is:

1. Night mode
2. Ignored laundry
3. Lights left on
4. Bins due
5. Laundry done
6. Energy expensive
7. Laundry running
8. Weather mood
9. Idle

## Non-Goals

The integration does not send images to the ESP32, implement a visual rule editor, manage multiple Homeagotchi devices, or use cloud services.

