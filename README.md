# ha-prana
Prana recuperators (fan) for Home Assistant over bluetooth

![](../master/PR_PLUS_150.png)

Supported operations:
  - control speed (1 - 10)
  - auto / night / heat mode
  - read sensor values: VOC, CO2
  - air direction
  
## Find mac address of your device on linux
```
sudo hcitool lescan
```

## Installation

1. Create ```custom_components/prana/``` in your homeassistant config directory.
2. Copy the files of this repository into this directory.
3. Add the config to your configuration.yaml file as explained below.
4. Restart Home Assistant or Hass.io.
5. When running Home Assistant in docker add ```-v /var/run/dbus/:/var/run/dbus/:z``` in order to Forward /var/run/dbus/ from host OS to docker

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
 - reading device name, temperatures, humidity and air pressure aren't yet supported
 
