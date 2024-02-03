# <img src="https://brands.home-assistant.io/gpslogger/icon.png" alt="GPSLogger" width="50" height="50"/> GPSLogger

This is a custom version of the Home Assistant built-in [GPSLogger](https://www.home-assistant.io/integrations/gpslogger/) integration.

It extends the built-in integration in ways that make sense but are no longer accepted.
Specifically, it allows additional attributes, especially `last_seen`,
which is crucial when combining entities from this Device Tracker integration with ones from other integrations,
e.g., via my [Composite Device Tracker](https://github.com/pnbruckner/ha-composite-tracker) integration.
Also, `last_seen` is important when dealing with packets received out of order from the corresponding Android app,
e.g., due to network delays.
