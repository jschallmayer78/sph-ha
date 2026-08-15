# SPH Home Assistant

Home Assistant integration for Schulportal Hessen (SPH), using the protocol and timetable parsing concepts from lanis-mobile/liblanis, LanisAPI and Lanis-mobile.

## Current version

0.2.0

## Installation

Copy `custom_components/sph_stundenplan` into `/config/custom_components/` and restart Home Assistant.

Copy `www/sph-stundenplan-card.js` to `/config/www/` and register it as a JavaScript module.

```yaml
type: custom:sph-stundenplan-card
entity: sensor.schulportal_hessen_stundenplan
title: Stundenplan
```

## Configuration

Settings → Devices & services → Add integration → Schulportal Hessen.

Required: school number, SPH username, password, class and update interval.

## Reference projects

- https://github.com/lanis-mobile/liblanis
- https://github.com/lanis-mobile/LanisAPI
- https://github.com/lanis-mobile/Lanis-mobile
