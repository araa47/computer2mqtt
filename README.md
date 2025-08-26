# Computer2Mqtt

This project is a multi-system and multi-OS adaptation of [mac2mqtt](https://github.com/bessarabov/mac2mqtt). It allows you to execute any command on your system, providing endless possibilities for automation and control.

## Running

1. Simply install `computer2mqtt` from pypi with `pip install computer2mqtt` or run directly with uv without installing with `uvx computer2mqtt --help`. Note you will need to pass a config file, more explained below.

1. Create a `computer2mqtt.yaml` by copying [computer2mqtt-example.yaml](computer2mqtt-example.yaml) configuration file in the project root.
There are 2 important sections first the mqtt config, and second the commands you want to run.
In the example below these are commands for macs to turn on/off the display. This should be changed to commands for your target system. Possibility is endless.

```yaml
mqtt:
  ip: 192.168.1.100
  port: 1883
  user: username
  password: password
  hostname: macmini  # This will be used in MQTT topics: mac2mqtt/macmini/command/...

commands:
  # Example mac command to wake/sleep display
  displaysleep: "pmset displaysleepnow"
  displaywake: "caffeinate -u -t 1"
```

4. Run `uvx computer2mqtt` and note down the hostname being used. This will either be:
   - The `hostname` specified in your `computer2mqtt.yaml` config file, OR
   - The auto-detected hostname if none is specified in the config

5. Set up Home Assistant Scripts to trigger commands. Here is an example from my `scripts.yaml` file in Home Assistant

```yaml
macmini_displaysleep:
  alias: Mac Mini Display Sleep
  icon: mdi:laptop
  sequence:
    - service: mqtt.publish
      data:
        topic: "mac2mqtt/macmini/command/displaysleep"
        payload: "displaysleep"

macmini_displaywake:
  alias: Mac Mini Display Wake
  icon: mdi:laptop
  sequence:
    - service: mqtt.publish
      data:
        topic: "mac2mqtt/macmini/command/displaywake"
        payload: "displaywake"
```
Replace `macmini` with the hostname from your configuration or as shown in the application logs!




## Local Development Requirements

This assumes you have [direnv](https://direnv.net/) and [uv](https://github.com/astral-sh/uv) installed

Simply run `direnv allow` to setup the environment, you can read the contents of [.envrc](.envrc) to see what it does behind the scenes.


## Setup

1. Clone this repository to your local machine.
2. Run `direnv allow` in the project directory. This will set up the Python environment using `uv` and also sync all dependencies.


# Running in the background

To run the script in the background, you can use the screen command. screen is a full-screen window manager that multiplexes a physical terminal between several processes.

1. Start a new screen session with name of your choice with the command `screen -S {mysession}`.
1. Run the script with the command `uvx computer2mqtt` or `computer2mqtt` if you installed it.
1. Detach from the screen session with the command Ctrl-a d.
1. You can reattach to the session at any time with the command `screen -r {mysession}`. This will keep the script running in the background, even if you close the terminal.
