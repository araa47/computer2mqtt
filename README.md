# Computer2Mqtt

This project is a multi-system and multi-OS adaptation of [mac2mqtt](https://github.com/bessarabov/mac2mqtt). It allows you to execute any command on your system, providing endless possibilities for automation and control.


## Requirements

This assumes you have [direnv](https://direnv.net/) and [uv](https://github.com/astral-sh/uv) installed

Simply run `direnv allow` to setup the environment, you can read the contents of [.envrc](.envrc) to see what it does behind the scenes.


## Setup

1. Clone this repository to your local machine.
2. Run `direnv allow` in the project directory. This will set up the Python environment using `pyenv`.
3. Create a `computer2mqtt.yaml` by copying [computer2mqtt-example.yaml](computer2mqtt-example.yaml) configuration file in the project root.
There are 2 important sections first the mqtt config, and second the commands you want to run.
In the example below these are commands for macs to turn on/off the display. This should be changed to commands for your target system. Possibility is endless.

```yaml
mqtt:
  ip: 192.168.1.100
  port: 1883
  user: username
  password: password


commands:
  # Example mac command to wake/sleep display
  displaysleep: "pmset displaysleepnow"
  displaywake: "caffeinate -u -t 1"
```

4. Run `c2m` and note down the `Sanitized hostname: Mac-mini`, Mac-mini in this case.
5. Set up Home Assistant Scripts to trigger commands. Here is an example from my `scripts.yaml` file in Home Assistant

```yaml
macmini_displaysleep:
  alias: Mac Mini Display Sleep
  icon: mdi:laptop
  sequence:
    - service: mqtt.publish
      data:
        topic: "mac2mqtt/{device_name}/command/displaysleep"
        payload: "displaysleep"

macmini_displaywake:
  alias: Mac Mini Display Wake
  icon: mdi:laptop
  sequence:
    - service: mqtt.publish
      data:
        topic: "mac2mqtt/{device_name}/command/displaywake"
        payload: "displaywake"
```
Replace {device_name} with the name of your device from the previous step!

# Running in the background

To run the script in the background, you can use the screen command. screen is a full-screen window manager that multiplexes a physical terminal between several processes.

1. Start a new screen session with name of your choice with the command `screen -S {mysession}`.
1. Run the script with the command `c2m`.
1. Detach from the screen session with the command Ctrl-a d.
1. You can reattach to the session at any time with the command `screen -r {mysession}`. This will keep the script running in the background, even if you close the terminal.
