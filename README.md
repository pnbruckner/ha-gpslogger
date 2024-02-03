# <img src="https://brands.home-assistant.io/gpslogger/icon.png" alt="GPSLogger" width="50" height="50"/> GPSLogger

This is a custom version of the Home Assistant built-in [GPSLogger](https://www.home-assistant.io/integrations/gpslogger/) integration.

It extends the built-in integration in ways that make sense but are no longer accepted.
Specifically, it allows additional attributes, especially `last_seen`,
which is crucial when combining entities from this Device Tracker integration with ones from other integrations,
e.g., via my [Composite Device Tracker](https://github.com/pnbruckner/ha-composite-tracker) integration.
Also, `last_seen` is important when dealing with packets received out of order from the corresponding Android app,
e.g., due to network delays.

## Installation

<details>
<summary>With HACS</summary>

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)

You can use HACS to manage the installation and provide update notifications.

1. Add this repo as a [custom repository](https://hacs.xyz/docs/faq/custom_repositories/).
   It should then appear as a new integration. Click on it. If necessary, search for "gpslogger".

   ```text
   https://github.com/pnbruckner/ha-gpslogger
   ```
   Or use this button:
   
   [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=pnbruckner&repository=ha-gpslogger&category=integration)

1. Download the integration using the appropriate button.

</details>

<details>
<summary>Manual</summary>

Place a copy of the files from [`custom_components/gpslogger`](custom_components/gpslogger)
in `<config>/custom_components/gpslogger`,
where `<config>` is your Home Assistant configuration directory.

>__NOTE__: When downloading, make sure to use the `Raw` button from each file's page.

</details>

## Setup

Please see the standard [GPSLogger](https://www.home-assistant.io/integrations/gpslogger/) documentation for basic set up.

The following should be added to the **HTTP Body** setting in the Android app (in addition to what the standard docs suggest):

```text
&last_seen=%TIME&battery_charging=%ISCHARGING
```

Note that `%TIME` provides the phone's time in UTC.
If you'd rather have the time specified in the phone's local time zone, use `%TIMEOFFSET` instead.
