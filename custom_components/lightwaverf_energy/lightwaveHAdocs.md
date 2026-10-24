---
layout: page
title: "Lightwave Energy Components"
description: "Instructions on how to configure the lightwave energy component"
date: 2026-07-01 22:00
sidebar: true
comments: false
sharing: true
footer: true
logo: 
ha_category:
  - Energy
  - Sensor
ha_release: "2024.12"
ha_iot_class: Local Polling
redirect_from:
ha_config_flow: true
---

[Lightwave Energy](https://lightwaverf.com/products/jsjslw600-lightwaverf-electricity-monitor-and-energy-monitor) integration for the Lightwave RF Energy Monitor. It creates a device with two sensors: current electricity usage (W) and the total used so far today (kWh). Both can be added to the Energy dashboard.

There is currently support for the following device types within Home Assistant:

- Sensor

For this integration to work, port 9761 (UDP) must be open on your machine's firewall.

{% include integrations/config_flow.md %}

{% configuration_basic %}
Update interval:
  description: Seconds between readings. Defaults to 30.
{% endconfiguration_basic %}

YAML configuration (`lightwaverf_energy:`) from earlier versions is imported automatically.
