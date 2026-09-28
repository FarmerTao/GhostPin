# Fudan Handan Campus / WeChat example

[English](fudan-example.md) | [简体中文](fudan-example.zh-CN.md)

## Intent and evidence

A user requested that a physical iPhone report a location near Fudan University for the WeChat mini program “复旦学生注册,” then clarified **Handan Campus**. The agent chose a landmark near Guanghua Building. The user later requested restoration.

This is a reproducible **device-operation example**, not proof of successful student registration or acceptance by the mini program. Do not click or submit registration as part of the location skill.

| Item | Recorded observation |
|---|---|
| Host | macOS 15.4 |
| Runtime | Python 3.12.14; pymobiledevice3 11.19.4 |
| iPhone OS | Device query returned 26.6.1 |
| Developer Mode | Initially false; reveal succeeded; later query returned true after user action |
| Support image | Initial mounting failed with `DeviceLocked`; after user unlock, mount succeeded |
| Simulation | Upstream set command entered its persistent waiting state after native-tunnel fallback |
| Maps verification | Not recorded |
| Mini-program acceptance | Not recorded |
| Restoration | Set session interrupted; explicit clear command exited 0 |
| Maps verification after restoration | Not recorded |

These observations came from direct upstream commands in the original session. The repository's new wrappers are covered by mocked tests; they have not been rerun against the phone just to validate publication.

## Coordinate provenance

Source: [Amap, Guanghua Building, Fudan Handan Campus](https://ditu.amap.com/place/B00155K7SX), consulted on 2026-09-28. The map coordinates were treated as GCJ-02:

| Coordinate | Latitude | Longitude |
|---|---|---|
| Source GCJ-02 | 31.300023 | 121.505283 |
| Approximate WGS84 conversion | 31.3020138 | 121.5008487 |

This is a landmark coordinate, not an official registration geofence or a guaranteed permitted check-in point. Verify the map marker visually. The decimal precision does not imply centimeter accuracy.

Offline conversion (no phone access):

```bash
python3 skills/ios-location/scripts/coordinates.py \
  --lat 31.300023 --lon 121.505283 --source gcj02
```

With connection, Developer Mode, and preparation complete, run in a persistent terminal:

```bash
skills/ios-location/.venv/bin/python skills/ios-location/scripts/location.py \
  set --udid YOUR_DEVICE_ID --lat 31.300023 --lon 121.505283 --source gcj02
```

The helper converts once. If you supply the converted numbers instead, use `--source wgs84`; do not convert them twice. Keep the session alive while the user checks Maps and the mini program. Restore with Ctrl+C in that helper, or `clear --udid YOUR_DEVICE_ID` if needed, then verify current location again.

## Transferable lessons

- Ask which campus before selecting coordinates; preserve the answer.
- A connected phone still needs trust, Developer Mode, and an unlocked screen during mounting.
- A hidden Developer Mode setting can be requested with `reveal`; the user completes the phone steps.
- Treat a tunnel fallback warning separately from a terminal failure.
- API download can help when raw GitHub is unavailable, but validate the content and keep images out of Git.
- Report command results, Maps observations, and app results separately.
- Explicitly clear simulation; don't rely on unplugging the phone.
