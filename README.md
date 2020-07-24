# ha-prana
Prana recuperators (fan) for Home Assistant over bluetooth

## Find mac address of your device on linux
```
sudo hcitool lescan
```

## Installation

1. Create ```custom_components/prana/``` in your homeassistant config directory.
2. Copy the files of this repository into this directory.
3. Add the config to your configuration.yaml file as explained below.
4. Restart Home Assistant or Hass.io.


## Examples
### Basic
```
prana:
  scan_interval: 60 # refresh data in x seconds
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
    
## Complete
```
prana:
  scan_interval: 60 # refresh data in x seconds
  devices:
  - mac: 'XX:XX:XX:XX:XX:XX'
    name: 'Prana living room'
    monitored_conditions:
      - co2
      - voc
```

## Debugging problems

```
logger:
  default: error
  logs:
    custom_components.prana: debug
```

## Notes
 - password is not supported
 - tested only on prana-150 
 - device name, temperatures, humidity and air pressure aren't supported
 
