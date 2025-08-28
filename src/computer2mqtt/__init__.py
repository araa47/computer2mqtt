import asyncio
import logging
import os
import re
import signal
import sys
from importlib.metadata import version
from typing import TYPE_CHECKING, Any, Dict

import aiomqtt
import click
import yaml

# Version information
try:
    __version__ = version("computer2mqtt")
except Exception:
    __version__ = "unknown"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

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
        self.hostname: str = ""

        self.commands: Dict[str, Any] = {}
        self.load_config(config_path)

    def load_config(self, config_path: str) -> None:
        """Loads configuration from a YAML file."""
        try:
            logger.info(f"Loading configuration from: {config_path}")
            with open(config_path, "r") as stream:
                config = yaml.safe_load(stream)
                mqtt_config = config.get("mqtt", {})
                self.ip = mqtt_config.get("ip", "")
                self.port = mqtt_config.get("port", 1883)
                self.user = mqtt_config.get("user", "")
                self.password = mqtt_config.get("password", "")
                self.hostname = mqtt_config.get("hostname", "")
                # Load command configurations
                self.commands = config.get("commands", {})

                logger.info("MQTT Configuration loaded:")
                logger.info(f"  - Broker IP: {self.ip}")
                logger.info(f"  - Port: {self.port}")
                logger.info(f"  - Username: {self.user}")
                logger.info(
                    f"  - Password: {'*' * len(self.password) if self.password else 'Not set'}"
                )
                logger.info(f"  - Hostname: {self.hostname}")
                logger.info(f"  - Commands loaded: {list(self.commands.keys())}")

        except (FileNotFoundError, yaml.YAMLError) as exc:
            logger.error(f"Error loading config: {exc}")
            raise


def get_hostname() -> str:
    """Returns a sanitized hostname suitable for use in topics."""
    hostname = os.uname()[1]
    sanitized_hostname = re.sub(r"[^a-zA-Z0-9_-]", "", hostname.split(".")[0])
    logger.info(f"Auto-detected hostname: {hostname}")
    logger.info(f"Sanitized auto-detected hostname: {sanitized_hostname}")
    return sanitized_hostname


def get_effective_hostname(config: Config) -> str:
    """Returns the hostname to use for MQTT topics - either from config or auto-detected."""
    if config.hostname:
        logger.info(f"Using hostname from config: {config.hostname}")
        return config.hostname
    else:
        auto_hostname = get_hostname()
        logger.info(f"No hostname in config, using auto-detected: {auto_hostname}")
        return auto_hostname


async def run_command(command: str, *args: str) -> None:
    """Executes the given command with the provided arguments asynchronously."""
    logger.info(f"Executing command: {command} {' '.join(args)}")
    try:
        process = await asyncio.create_subprocess_exec(
            command,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            logger.info(f"Command executed successfully: {command}")
            if stdout:
                logger.debug(f"Command output: {stdout.decode().strip()}")
        else:
            logger.error(
                f"Command failed with return code {process.returncode}: {command}"
            )
            if stderr:
                logger.error(f"Command error: {stderr.decode().strip()}")
    except Exception as e:
        logger.error(f"Failed to execute command '{command}': {e}")


async def command_executor(config: Config, command_key: str) -> None:
    """Executes a command based on the key from the configuration."""
    command = config.commands.get(command_key)
    if command:
        logger.info(f"Found command for '{command_key}': {command}")
        command_list = command.split()
        await run_command(*command_list)
    else:
        logger.warning(f"Command for '{command_key}' not found in the configuration.")
        logger.debug(f"Available commands: {list(config.commands.keys())}")


async def mqtt_client_task(config: Config):
    """Task for running the MQTT client and handling messages with reconnection logic."""
    hostname = get_effective_hostname(config)
    subscription_topic = f"mac2mqtt/{hostname}/command/#"

    connection_attempts = 0
    while True:
        connection_attempts += 1
        try:
            logger.info(f"MQTT Connection attempt #{connection_attempts}")
            logger.info(f"Connecting to MQTT broker at {config.ip}:{config.port}")
            logger.info(f"Using username: {config.user}")

            # Create a descriptive client ID using the hostname from earlier
            client_id = f"computer2mqtt-{hostname}-{hash(config.user) % 10000:04d}"
            logger.info(f"Using client ID: {client_id}")

            # Add connection timeout and keepalive settings
            async with aiomqtt.Client(
                config.ip,
                username=config.user or "default_user",
                password=config.password or "default_password",
                port=config.port,
                identifier=client_id,
                keepalive=60,  # Send keepalive packets every 60 seconds
                timeout=30,  # Connection timeout of 30 seconds
            ) as client:
                logger.info("✅ Successfully connected to MQTT broker!")
                logger.info(f"Subscribing to topic: {subscription_topic}")

                await client.subscribe(subscription_topic)
                logger.info("✅ Successfully subscribed to topic!")
                logger.info("🔄 Listening for messages...")

                # Reset connection attempts on successful connection
                connection_attempts = 0

                async for message in client.messages:
                    logger.info("📨 Received MQTT message:")
                    logger.info(f"  📍 Topic: {str(message.topic)}")
                    logger.info(f"  📝 Payload: {str(message.payload)}")

                    topic_parts = str(message.topic).split("/")
                    if isinstance(message.payload, bytes):
                        payload = message.payload.decode()
                    else:
                        payload = str(message.payload)

                    logger.info(f"  🔍 Topic parts: {topic_parts}")
                    logger.info(f"  📦 Decoded payload: '{payload}'")

                    if len(topic_parts) == 4:
                        command_key = topic_parts[3]
                        logger.info(f"  🎯 Extracted command key: '{command_key}'")
                        if payload == command_key:
                            logger.info(
                                "  ✅ Payload matches command key, executing command"
                            )
                            await command_executor(config, command_key)
                        else:
                            logger.warning(
                                f"  ❌ Payload '{payload}' does not match command key '{command_key}'"
                            )
                    else:
                        logger.warning(
                            f"  ❌ Invalid topic structure. Expected 4 parts, got {len(topic_parts)}"
                        )

        except aiomqtt.exceptions.MqttError as e:
            error_msg = str(e).lower()
            if (
                "not authorized" in error_msg
                or "authentication" in error_msg
                or "bad username or password" in error_msg
            ):
                logger.error(f"🔐 Authentication Error: {e}")
                logger.error(
                    "❌ Check your MQTT username and password in the config file"
                )
                logger.error(
                    "❌ Verify the user exists in Home Assistant and has proper permissions"
                )
                logger.info(
                    f"   Using username: '{config.user}' and password: '{'*' * len(config.password)}'"
                )
            elif "connection refused" in error_msg:
                logger.error(f"🚫 Connection Refused: {e}")
                logger.error("❌ The MQTT broker rejected the connection")
            elif "timed out" in error_msg or "timeout" in error_msg:
                logger.error(f"⏰ Connection Timeout: {e}")
                logger.error("❌ The connection to the MQTT broker timed out")
                logger.info(
                    "💡 This might be due to network issues or broker authentication delays"
                )
            else:
                logger.error(f"❌ MQTT Error: {e}")

            logger.info(
                f"🔄 Attempting to reconnect in 10 seconds... (attempt #{connection_attempts})"
            )
            await asyncio.sleep(10)  # Wait for 10 seconds before reconnecting
        except Exception as e:
            logger.error(f"💥 An unexpected error occurred: {e}")
            logger.exception("Full exception details:")
            break  # Exit the loop if an unexpected error occurs


async def main(config_path: str) -> None:
    """Main function to setup and run the application."""
    logger.info("🚀 Starting computer2mqtt application")
    config = Config(config_path)

    logger.info("🔧 Creating MQTT client task")
    main_task = asyncio.create_task(mqtt_client_task(config))

    def signal_handler():
        logger.info("⛔ Caught SIGINT signal, stopping...")
        main_task.cancel()

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, signal_handler)

    try:
        await main_task
    except asyncio.CancelledError:
        logger.info("🛑 Main task cancelled, application shutting down.")
    finally:
        logger.info("🧹 Cleaning up...")


@click.command()
@click.option(
    "--config", default="computer2mqtt.yaml", help="Path to the configuration file."
)
@click.option(
    "--log-level",
    default="INFO",
    help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
)
@click.version_option(version=__version__)
def sync_main(config: str, log_level: str):
    """Synchronously runs the main function with the provided configuration file."""
    # Update logging level based on command line argument
    logging.getLogger().setLevel(getattr(logging, log_level.upper()))

    logger.info(f"📋 Using configuration file: {config}")
    logger.info(f"🔧 Log level set to: {log_level.upper()}")
    asyncio.run(main(config))


if __name__ == "__main__":
    sync_main()
