import os
import re
import subprocess
from typing import Any, Dict

import paho.mqtt.client as mqtt
import yaml


class Config:
    """Handles loading and accessing configuration from a YAML file."""

    def __init__(self, config_path: str = "computer2mqtt.yaml") -> None:
        """Initializes the configuration from the given YAML file."""
        self.ip: str = ""
        self.port: int = 1883  # Default MQTT port
        self.user: str = ""
        self.password: str = ""

        self.commands: Dict[str, Any] = {}
        self.load_config(config_path)

    def load_config(self, config_path: str) -> None:
        """Loads configuration from a YAML file."""
        try:
            with open(config_path, "r") as stream:
                config = yaml.safe_load(stream)
                mqtt_config = config.get("mqtt", {})
                self.ip = mqtt_config.get("ip", "")
                self.port = mqtt_config.get("port", 1883)
                self.user = mqtt_config.get("user", "")
                self.password = mqtt_config.get("password", "")
                # Load command configurations
                self.commands = config.get("commands", {})
        except (FileNotFoundError, yaml.YAMLError) as exc:
            print(f"Error loading config: {exc}")


def get_hostname() -> str:
    """Returns a sanitized hostname suitable for use in topics."""
    hostname = os.uname()[1]
    sanitized_hostname = re.sub(r"[^a-zA-Z0-9_-]", "", hostname.split(".")[0])
    print(f"Sanitized hostname: {sanitized_hostname}")
    return sanitized_hostname


def run_command(command: str, *args: str) -> None:
    """Executes the given command with the provided arguments."""
    subprocess.run([command] + list(args), check=True)


def command_executor(config: Config, command_key: str) -> None:
    """Executes a command based on the key from the configuration."""
    command = config.commands.get(command_key)
    if command:
        command_list = command.split()
        run_command(*command_list)
    else:
        print(f"Command for '{command_key}' not found in the configuration.")


def on_connect(
    client: mqtt.Client, userdata: Any, flags: Dict[str, Any], rc: int
) -> None:
    """Callback for when the client receives a CONNACK response from the server."""
    print(f"Connected with result code {rc}")
    client.subscribe(f"mac2mqtt/{get_hostname()}/command/+")


def on_message(
    client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage, config: Config
) -> None:
    """Callback for when a PUBLISH message is received from the server."""
    print(f"Received a message on topic: {msg.topic}")
    topic_parts = msg.topic.split("/")
    payload = msg.payload.decode()

    if len(topic_parts) == 4:
        command_key = topic_parts[3]
        if payload == command_key:
            command_executor(config, command_key)


def main() -> None:
    """Main function to initialize and run the MQTT client."""
    config = Config()
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1)  # type: ignore
    client.username_pw_set(
        config.user or "default_user", config.password or "default_password"
    )
    client.on_connect = on_connect
    # Using a lambda to pass the config object to the on_message callback
    client.on_message = lambda c, u, m: on_message(c, u, m, config)

    if config.ip != "":
        client.connect(config.ip, config.port, 60)
    else:
        print("MQTT broker IP address or port is not configured properly.")
        return

    client.loop_forever()


main()
