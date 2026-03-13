# computer2mqtt

Run local shell commands from MQTT topics. Inspired by [mac2mqtt](https://github.com/bessarabov/mac2mqtt), but intended to work across operating systems.

## Quickstart

1. Copy the sample config:
   - `cp computer2mqtt-example.yaml computer2mqtt.yaml`
2. Edit `computer2mqtt.yaml` with your MQTT broker and commands.
3. Run directly without installing:
   - `uvx computer2mqtt --config computer2mqtt.yaml`

## Install As A Tool

Install once, then call the command directly:

- `uv tool install computer2mqtt`
- Run: `computer2mqtt --config computer2mqtt.yaml`
- Upgrade later: `uv tool upgrade computer2mqtt`

This package also exposes an alias command:

- `orm --config computer2mqtt.yaml`

## Use With `uvx`

- Run latest published version directly: `uvx computer2mqtt --config computer2mqtt.yaml`
- Run the alias directly: `uvx --from computer2mqtt orm --config computer2mqtt.yaml`

## MQTT Topic Pattern

The service subscribes to:

- `mac2mqtt/<hostname>/command/#`

For each configured command key (for example `displaysleep`), publish:

- Topic: `mac2mqtt/<hostname>/command/displaysleep`
- Payload: `displaysleep`

See `computer2mqtt-example.yaml` for a full config example.

## Development

Requirements:

- [uv](https://github.com/astral-sh/uv)
- [direnv](https://direnv.net/)

Setup:

- `direnv allow`

Code quality hooks are managed with [prek](https://github.com/j178/prek):

- `uv run prek run --all-files`
