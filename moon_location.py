 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/moon_location.py b/moon_location.py
new file mode 100644
index 0000000000000000000000000000000000000000..4be3a19bd667c0bfcea67e877c4aaa40689df656
--- /dev/null
+++ b/moon_location.py
@@ -0,0 +1,212 @@
+"""Command line tool to approximate the Moon's location for Hong Kong timestamps."""
+
+from __future__ import annotations
+
+import argparse
+from dataclasses import dataclass
+from datetime import UTC, datetime
+from math import asin, atan2, cos, degrees, fmod, radians, sin, tan
+from zoneinfo import ZoneInfo
+
+HK_TZ = ZoneInfo("Asia/Hong_Kong")
+
+
+@dataclass
+class MoonPosition:
+    altitude_deg: float
+    azimuth_deg: float
+    right_ascension_deg: float
+    declination_deg: float
+    earth_distance_km: float
+
+
+def normalize_angle(angle: float) -> float:
+    """Return an angle in the [0, 360) range."""
+
+    wrapped = fmod(angle, 360.0)
+    return wrapped + 360.0 if wrapped < 0 else wrapped
+
+
+def parse_hong_kong_datetime(value: str) -> datetime:
+    try:
+        parsed = datetime.fromisoformat(value)
+    except ValueError as exc:
+        raise argparse.ArgumentTypeError(
+            "Date time must be in ISO format, e.g. 2024-08-12 21:30"
+        ) from exc
+
+    if parsed.tzinfo is None:
+        parsed = parsed.replace(tzinfo=HK_TZ)
+    else:
+        parsed = parsed.astimezone(HK_TZ)
+
+    return parsed
+
+
+def julian_day(moment: datetime) -> float:
+    """Julian Day for the given (UTC) datetime."""
+
+    moment = moment.astimezone(UTC)
+    year = moment.year
+    month = moment.month
+    frac_day = (
+        moment.day
+        + (moment.hour + (moment.minute + (moment.second + moment.microsecond / 1e6) / 60) / 60)
+        / 24.0
+    )
+
+    if month <= 2:
+        year -= 1
+        month += 12
+
+    a = year // 100
+    b = 2 - a + a // 4
+
+    jd = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + frac_day + b - 1524.5
+    return jd
+
+
+def moon_ecliptic_coordinates(jd: float) -> tuple[float, float, float]:
+    """Approximate geocentric ecliptic longitude, latitude, and distance."""
+
+    d = jd - 2451543.5
+
+    l0 = normalize_angle(218.3164477 + 13.17639648 * d)
+    d_moon = normalize_angle(297.8501921 + 12.19074912 * d)
+    m_sun = normalize_angle(357.5291092 + 0.98560028 * d)
+    m_moon = normalize_angle(134.9633964 + 13.06499295 * d)
+    f = normalize_angle(93.2720950 + 13.22935024 * d)
+
+    lon = l0
+    lon += 6.289 * sin(radians(m_moon))
+    lon += 1.274 * sin(radians(2 * d_moon - m_moon))
+    lon += 0.658 * sin(radians(2 * d_moon))
+    lon += 0.214 * sin(radians(2 * m_moon))
+    lon += 0.11 * sin(radians(d_moon))
+    lon += 0.208 * sin(radians(2 * d_moon - m_sun))
+
+    lat = 5.128 * sin(radians(f))
+    lat += 0.28 * sin(radians(m_moon + f))
+    lat += 0.277 * sin(radians(m_moon - f))
+    lat += 0.173 * sin(radians(2 * d_moon - f))
+    lat += 0.055 * sin(radians(2 * d_moon + f))
+    lat += 0.046 * sin(radians(2 * d_moon - m_moon + f))
+    lat += 0.033 * sin(radians(2 * d_moon - m_moon - f))
+    lat += 0.017 * sin(radians(2 * m_moon + f))
+
+    distance = 385000.56
+    distance -= 20905.0 * cos(radians(m_moon))
+    distance -= 3699.0 * cos(radians(2 * d_moon - m_moon))
+    distance -= 2956.0 * cos(radians(2 * d_moon))
+    distance -= 570.0 * cos(radians(2 * d_moon + m_moon))
+
+    return normalize_angle(lon), lat, distance
+
+
+def ecliptic_to_equatorial(lon_deg: float, lat_deg: float, jd: float) -> tuple[float, float]:
+    t = (jd - 2451545.0) / 36525.0
+    eps = radians(23.439291 - 0.0000137 * t)
+
+    lon = radians(lon_deg)
+    lat = radians(lat_deg)
+
+    x = cos(lon)
+    y = sin(lon) * cos(eps) - tan(lat) * sin(eps)
+    ra = atan2(y, x)
+    dec = asin(sin(lat) * cos(eps) + cos(lat) * sin(eps) * sin(lon))
+
+    return normalize_angle(degrees(ra)), degrees(dec)
+
+
+def local_sidereal_time(jd: float, longitude_deg: float) -> float:
+    t = (jd - 2451545.0) / 36525.0
+    theta = 280.46061837 + 360.98564736629 * (jd - 2451545.0)
+    theta += 0.000387933 * t * t - t * t * t / 38710000.0
+    return normalize_angle(theta + longitude_deg)
+
+
+def horizontal_coordinates(
+    latitude_deg: float, declination_deg: float, hour_angle_deg: float
+) -> tuple[float, float]:
+    lat = radians(latitude_deg)
+    dec = radians(declination_deg)
+    ha = radians(hour_angle_deg)
+
+    altitude = asin(sin(dec) * sin(lat) + cos(dec) * cos(lat) * cos(ha))
+    azimuth = atan2(
+        -sin(ha),
+        tan(dec) * cos(lat) - sin(lat) * cos(ha),
+    )
+
+    return degrees(altitude), normalize_angle(degrees(azimuth))
+
+
+def compute_moon_position(
+    when_hk: datetime, latitude: float, longitude: float, elevation_m: float | None = None
+) -> MoonPosition:
+    if when_hk.tzinfo is None:
+        when_hk = when_hk.replace(tzinfo=HK_TZ)
+
+    jd = julian_day(when_hk)
+    lon_ecl, lat_ecl, distance_km = moon_ecliptic_coordinates(jd)
+    ra_deg, dec_deg = ecliptic_to_equatorial(lon_ecl, lat_ecl, jd)
+
+    lst = local_sidereal_time(jd, longitude)
+    hour_angle = lst - ra_deg
+    if hour_angle > 180:
+        hour_angle -= 360
+    elif hour_angle < -180:
+        hour_angle += 360
+
+    altitude, azimuth = horizontal_coordinates(latitude, dec_deg, hour_angle)
+
+    return MoonPosition(altitude, azimuth, ra_deg, dec_deg, distance_km)
+
+
+def build_parser() -> argparse.ArgumentParser:
+    parser = argparse.ArgumentParser(
+        description=(
+            "Compute the Moon's altitude, azimuth, and distance for a Hong Kong local"
+            " date/time and a given observing location."
+        )
+    )
+    parser.add_argument(
+        "datetime",
+        type=parse_hong_kong_datetime,
+        help=(
+            "Hong Kong local time in ISO format (e.g. '2024-08-12 21:30' or"
+            " '2024-08-12T21:30:00')."
+        ),
+    )
+    parser.add_argument("latitude", type=float, help="Latitude in decimal degrees")
+    parser.add_argument("longitude", type=float, help="Longitude in decimal degrees")
+    parser.add_argument(
+        "--elevation",
+        type=float,
+        default=0.0,
+        help="Observer elevation in meters above sea level (currently informational)",
+    )
+    return parser
+
+
+def main() -> None:
+    parser = build_parser()
+    args = parser.parse_args()
+
+    position = compute_moon_position(args.datetime, args.latitude, args.longitude)
+
+    print("Moon location for:")
+    print(f"  Hong Kong time: {args.datetime.isoformat(sep=' ', timespec='seconds')}")
+    print(f"  UTC time      : {args.datetime.astimezone(UTC).isoformat(timespec='seconds')}")
+    print(f"  Latitude/Long.: {args.latitude:.4f}°, {args.longitude:.4f}°")
+    print()
+    print("Results:")
+    print(f"  Altitude            : {position.altitude_deg:.2f}°")
+    print(f"  Azimuth             : {position.azimuth_deg:.2f}°")
+    print(f"  Right Ascension     : {position.right_ascension_deg:.2f}°")
+    print(f"  Declination         : {position.declination_deg:.2f}°")
+    print(f"  Earth-Moon distance : {position.earth_distance_km:,.0f} km")
+
+
+if __name__ == "__main__":
+    main()
 
EOF
)
