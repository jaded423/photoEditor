import json
from pathlib import Path
import logging


def get_settings_path():
    """
    Returns the path to the settings file, ensuring the directory exists.
    Uses a platform-appropriate application support directory.
    """
    try:
        # macOS standard location
        app_support_dir = Path.home() / 'Library' / 'Application Support' / 'CombinedProcessor'
    except Exception:
        # Fallback for other systems
        app_support_dir = Path.home() / '.CombinedProcessor'

    app_support_dir.mkdir(parents=True, exist_ok=True)
    return app_support_dir / 'settings.json'


def load_settings():
    """
    Loads settings from the JSON file.
    Returns a dictionary with settings, or a default dictionary if the file doesn't exist.
    """
    settings_file = get_settings_path()
    if not settings_file.exists():
        logging.info("Settings file not found. Using defaults.")
        return {
            'webhook_url': '',
            'api_key': '',
            'api_key_header': 'Authorization',
            'default_raw_folder': str(Path.home() / 'Downloads')
        }

    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            logging.info(f"Loaded settings from {settings_file}")
            return settings
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Could not read settings file {settings_file}: {e}. Using defaults.")
        return {
            'webhook_url': '',
            'api_key': '',
            'api_key_header': 'Authorization',
            'default_raw_folder': str(Path.home() / 'Downloads')
        }


def save_settings(settings):
    """Saves the provided settings dictionary to the JSON file."""
    settings_file = get_settings_path()
    try:
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4)
            logging.info(f"Saved settings to {settings_file}")
    except IOError as e:
        logging.error(f"Could not save settings to {settings_file}: {e}")