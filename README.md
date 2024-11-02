# Custom component for Silvercrest SWS-A1

This is a Home Assisstant custom component for interfacing with old (ca 2015) LIDL Silvercrest SWS-A1 Wifi plugs.

## Installation

Copy `custom_components/silvercrest` into your `custom_components` directory and configure your plug in your configuration YAML like this:

```yaml
switch:
  - platform: silvercrest
    host: "192.168.0.123" # Your plug's ip address
    name: silvercrestplug1 # entityId for homeassisstant
```
