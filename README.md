# Moon-location-01

Simple command line utility for computing the Moon's location for a Hong Kong local
date/time and arbitrary latitude/longitude using a lightweight approximation of the
Meeus lunar algorithms.

## Usage

```
python moon_location.py "2024-08-12 21:30" 22.3193 114.1694 --elevation 50
```

The command above reports the Moon's altitude, azimuth, equatorial coordinates, and
Earth-Moon distance for Hong Kong time *2024-08-12 21:30* observed from latitude
22.3193° N, longitude 114.1694° E at 50 meters above sea level.

> **Note:** The calculations follow a truncated version of Jean Meeus' algorithms and
> are suitable for educational and general-observation purposes. For scientific work,
> consider using a high-precision ephemeris such as JPL DE430.
