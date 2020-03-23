# ha-prana
Prana recuperators (fan) for Home Assistant


## Installation

1. Create ```custom_components/prana/``` in your homeassistant config directory.
2. Copy the files of this repository into this directory.
3. Add the config to your configuration.yaml file as explained below.
4. Restart Home Assistant or Hass.io.


## Examples
### Basic
```
prana:
  devices:
  - mac: 'XX:XX:XX:XX:XX:XX'
```

### Limit sensors
```
prana:
  devices:
  - mac: 'XX:XX:XX:XX:XX:XX'
    monitored_conditions:
      - voc
```

## Available sensors & switches
    - co2
    - voc

## Debugging problems

```
logger:
  default: error
  logs:
    custom_components.prana: debug
```
