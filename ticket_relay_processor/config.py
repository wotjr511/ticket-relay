"""Configuration loading and safe updates for TicketRelayProcessor."""

from __future__ import annotations

import configparser
import logging
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

LOGGER = logging.getLogger(__name__)


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config.ini"
_CONFIG_LOCK = threading.RLock()
_ACTIVE_CONFIG: Optional["Config"] = None


@dataclass(frozen=True)
class WatchConfig:
    """Settings for the ticket directory watcher."""

    directory: Path
    poll_interval: float


@dataclass(frozen=True)
class ApiConfig:
    """Settings for API health checks and ticket forwarding."""

    target_url: str
    health_check_url: str
    timeout: float
    max_retries: int


@dataclass(frozen=True)
class LoggingConfig:
    """Settings for ticket processing history logs."""

    log_dir: Path
    log_level: str


class Config:
    """Load and expose application configuration from an INI file."""

    REQUIRED_KEYS = {
        "watch": ("directory", "poll_interval"),
        "api": ("target_url", "health_check_url", "timeout", "max_retries"),
    }
    OPTIONAL_KEYS = {
        "logging": ("log_dir", "log_level"),
    }

    def __init__(self, path: Union[Path, str] = DEFAULT_CONFIG_PATH) -> None:
        """Create a Config instance bound to an INI file path."""

        self.path = Path(path).resolve()
        self.parser = configparser.ConfigParser(inline_comment_prefixes=(";", "#"))
        self.watch: WatchConfig
        self.api: ApiConfig
        self.logging: LoggingConfig
        self.reload()

    def reload(self) -> None:
        """Reload configuration from disk and validate required values."""

        with _CONFIG_LOCK:
            if not self.path.exists():
                raise FileNotFoundError(f"Configuration file not found: {self.path}")

            parser = configparser.ConfigParser(inline_comment_prefixes=(";", "#"))
            read_files = parser.read(self.path)
            if not read_files:
                raise RuntimeError(f"Unable to read configuration file: {self.path}")

            self._validate(parser)
            self.parser = parser
            self.watch = WatchConfig(
                directory=self._resolve_directory(parser.get("watch", "directory")),
                poll_interval=parser.getfloat("watch", "poll_interval"),
            )
            self.api = ApiConfig(
                target_url=parser.get("api", "target_url").strip(),
                health_check_url=parser.get("api", "health_check_url").strip(),
                timeout=parser.getfloat("api", "timeout"),
                max_retries=parser.getint("api", "max_retries"),
            )
            log_dir = "./logs"
            log_level = "INFO"
            if parser.has_section("logging"):
                log_dir = parser.get("logging", "log_dir", fallback=log_dir)
                log_level = parser.get("logging", "log_level", fallback=log_level)
            self.logging = LoggingConfig(
                log_dir=self._resolve_directory(log_dir),
                log_level=log_level.strip(),
            )
            self._validate_values()
            LOGGER.debug("Configuration loaded from %s", self.path)

    def _resolve_directory(self, configured_path: str) -> Path:
        """Resolve watch directory relative to the config file location."""

        path = Path(configured_path.strip()).expanduser()
        if not path.is_absolute():
            path = self.path.parent / path
        return path.resolve()

    def _validate(self, parser: configparser.ConfigParser) -> None:
        """Validate that the INI file contains all required sections and keys."""

        for section, keys in self.REQUIRED_KEYS.items():
            if not parser.has_section(section):
                raise ValueError(f"Missing required config section: [{section}]")
            for key in keys:
                if not parser.has_option(section, key):
                    raise ValueError(f"Missing required config key: [{section}] {key}")

    def _validate_values(self) -> None:
        """Validate parsed configuration values."""

        if self.watch.poll_interval <= 0:
            raise ValueError("[watch] poll_interval must be greater than zero")
        if self.api.timeout <= 0:
            raise ValueError("[api] timeout must be greater than zero")
        if self.api.max_retries < 0:
            raise ValueError("[api] max_retries must be zero or greater")
        if not self.api.target_url:
            raise ValueError("[api] target_url cannot be empty")
        if not self.api.health_check_url:
            raise ValueError("[api] health_check_url cannot be empty")
        if not self.logging.log_level:
            raise ValueError("[logging] log_level cannot be empty")


def get_config(path: Union[Path, str] = DEFAULT_CONFIG_PATH) -> Config:
    """Return the active configuration, creating or reloading it when needed."""

    global _ACTIVE_CONFIG
    requested_path = Path(path).resolve()
    with _CONFIG_LOCK:
        if _ACTIVE_CONFIG is None or _ACTIVE_CONFIG.path != requested_path:
            _ACTIVE_CONFIG = Config(requested_path)
        return _ACTIVE_CONFIG


def set_config(section: str, key: str, value: str) -> Config:
    """Safely update config.ini and reload the active configuration.

    The update is written to a temporary file and atomically replaced to avoid
    leaving a partially written configuration behind if the process is stopped.
    """

    global _ACTIVE_CONFIG
    with _CONFIG_LOCK:
        config = get_config()
        parser = configparser.ConfigParser(inline_comment_prefixes=(";", "#"))
        parser.read(config.path)

        allowed_keys = (
            Config.REQUIRED_KEYS.get(section, ())
            + Config.OPTIONAL_KEYS.get(section, ())
        )
        if key not in allowed_keys:
            raise ValueError(f"Unknown config key: [{section}] {key}")
        if not parser.has_section(section):
            parser.add_section(section)

        parser.set(section, key, value)

        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=config.path.parent,
            delete=False,
        ) as temp_file:
            parser.write(temp_file)
            temp_path = Path(temp_file.name)

        temp_path.replace(config.path)
        config.reload()
        _ACTIVE_CONFIG = config
        LOGGER.info("Updated configuration value [%s] %s", section, key)
        return config
