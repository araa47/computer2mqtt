import asyncio
import os
import re
import signal
import sys
from typing import TYPE_CHECKING, Any, Dict

import aiomqtt
import yaml

if TYPE_CHECKING or (sys.platform.lower() == "win32" or os.name.lower() == "nt"):
    pass  # type: ignore


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


async def run_command(command: str, *args: str) -> None:
    """Executes the given command with the provided arguments asynchronously."""
    await asyncio.create_subprocess_exec(command, *args)


async def command_executor(config: Config, command_key: str) -> None:
    """Executes a command based on the key from the configuration."""
    command = config.commands.get(command_key)
    if command:
        command_list = command.split()
        await run_command(*command_list)
    else:
        print(f"Command for '{command_key}' not found in the configuration.")


async def mqtt_client_task(config: Config):
    """Task for running the MQTT client and handling messages with reconnection logic."""
    while True:
        try:
            async with aiomqtt.Client(
                config.ip,
                username=config.user or "default_user",
                password=config.password or "default_password",
                port=config.port,
            ) as client:
                await client.subscribe(f"mac2mqtt/{get_hostname()}/command/#")
                async for message in client.messages:
                    print(
                        f"Received message: {str(message.topic)} => {str(message.payload)}"
                    )
                    topic_parts = str(message.topic).split("/")
                    if isinstance(message.payload, bytes):
                        payload = message.payload.decode()
                    else:
                        payload = str(message.payload)

                    if len(topic_parts) == 4:
                        command_key = topic_parts[3]
                        if payload == command_key:
                            await command_executor(config, command_key)
        except aiomqtt.exceptions.MqttError as e:
            print(f"MQTT Error: {e}, attempting to reconnect in 10 seconds...")
            await asyncio.sleep(10)  # Wait for 10 seconds before reconnecting
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            break  # Exit the loop if an unexpected error occurs


async def main() -> None:
    """Main function to setup and run the application."""
    config = Config()
    main_task = asyncio.create_task(mqtt_client_task(config))

    def signal_handler():
        print("Caught SIGINT signal, stopping...")
        main_task.cancel()

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, signal_handler)

    try:
        await main_task
    except asyncio.CancelledError:
        print("Main task cancelled, application shutting down.")
    finally:
        print("Cleaning up...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Application interrupted, exiting...")
