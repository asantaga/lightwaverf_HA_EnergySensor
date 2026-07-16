# Issue 9 Energy Dashboard metadata

## Scope

Make the existing legacy LightwaveRF Energy Sensor entities eligible for Home
Assistant statistics and the Energy Dashboard without changing their state
values, names, UDP listener, or configuration.

## Design

`LightwaveEnergy` remains a legacy `Entity`.  It exposes metadata properties
based on the existing `sensor_type`:

- `CURRENT_USAGE`: `device_class` `power` and `state_class` `measurement`.
- `TODAY_USAGE`: `device_class` `energy` and `state_class`
  `total_increasing`.

The daily kWh counter is a positive total that resets each day, which matches
`total_increasing`.  No `last_reset` attribute will be added.

## Error handling

When the energy value has not yet been received, the sensor returns `None`
rather than a non-numeric empty string, keeping its states valid for
statistics.

## Tests

Add focused unit tests covering both entities' device and state classes and
the missing-data state.  Run the focused tests and a syntax compilation check.
