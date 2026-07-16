# Energy dashboard metadata design

## Scope

Make the LightwaveRF energy sensors eligible for Home Assistant's Energy
dashboard without changing their UDP data collection or entity names.

## Design

`LightwaveEnergy` will inherit from Home Assistant's `SensorEntity` rather
than the generic `Entity`. This exposes `device_class`, `state_class`, and
`unit_of_measurement` as sensor state attributes, which lets Home Assistant
create statistics and include the entities in the Energy dashboard picker.

The current-usage entity remains a power measurement in watts:

- `device_class`: `power`
- `state_class`: `measurement`
- `unit_of_measurement`: `W`

The today-usage entity is a daily kWh total that resets at the start of each
day. It will be declared as:

- `device_class`: `energy`
- `state_class`: `total`
- `unit_of_measurement`: `kWh`

`total` is used rather than `total_increasing` because this source can reset.

## Tests

Extend the metadata tests to require `SensorEntity` inheritance and to verify
the exact device class, state class, and unit for both entities. Run the
targeted test module, then the full test suite.
