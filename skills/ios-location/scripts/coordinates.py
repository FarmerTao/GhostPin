"""Explicit GCJ-02 to approximate WGS84 conversion; no geocoding or device access."""
import argparse
import json
import math


def validate(lat, lon):
    if not (math.isfinite(lat) and math.isfinite(lon)):
        raise ValueError("Coordinates must be finite")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("Latitude must be in [-90,90], longitude in [-180,180]")


def wgs_to_gcj(lat, lon):
    validate(lat, lon)
    if not (72.004 <= lon <= 137.8347 and 0.8293 <= lat <= 55.8271):
        raise ValueError("Outside the approximate GCJ-02 conversion region; provide WGS84 coordinates")
    x, y = lon - 105, lat - 35
    a = -100 + 2*x + 3*y + .2*y*y + .1*x*y + .2*math.sqrt(abs(x))
    a += (20*math.sin(6*x*math.pi) + 20*math.sin(2*x*math.pi))*2/3
    a += (20*math.sin(y*math.pi) + 40*math.sin(y/3*math.pi))*2/3
    a += (160*math.sin(y/12*math.pi) + 320*math.sin(y*math.pi/30))*2/3
    b = 300 + x + 2*y + .1*x*x + .1*x*y + .1*math.sqrt(abs(x))
    b += (20*math.sin(6*x*math.pi) + 20*math.sin(2*x*math.pi))*2/3
    b += (20*math.sin(x*math.pi) + 40*math.sin(x/3*math.pi))*2/3
    b += (150*math.sin(x/12*math.pi) + 300*math.sin(x/30*math.pi))*2/3
    rad = lat/180*math.pi
    magic = 1 - .00669342162296594323*math.sin(rad)**2
    a = a*180/((6378245*(1-.00669342162296594323))/(magic*math.sqrt(magic))*math.pi)
    b = b*180/(6378245/math.sqrt(magic)*math.cos(rad)*math.pi)
    return lat+a, lon+b


def to_wgs84(lat, lon, source):
    validate(lat, lon)
    if source == "wgs84":
        return lat, lon
    if source != "gcj02":
        raise ValueError("Specify wgs84 or gcj02 explicitly; coordinate systems are not inferred")
    target_lat, target_lon = lat, lon
    for _ in range(10):
        projected_lat, projected_lon = wgs_to_gcj(lat, lon)
        lat -= projected_lat - target_lat
        lon -= projected_lon - target_lon
    return lat, lon


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lon", type=float, required=True)
    p.add_argument("--source", choices=["wgs84", "gcj02"], required=True)
    args = p.parse_args()
    try:
        lat, lon = to_wgs84(args.lat, args.lon, args.source)
    except ValueError as e:
        p.error(str(e))
    print(json.dumps({"latitude": round(lat, 7), "longitude": round(lon, 7),
                      "coordinate_system": "WGS84", "approximate_conversion": args.source == "gcj02"}))


if __name__ == "__main__":
    main()
