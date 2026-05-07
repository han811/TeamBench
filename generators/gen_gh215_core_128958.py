"""
Parameterized generator for GH215_core_128958.

Source PR:    https://github.com/home-assistant/core/pull/128958
Source Issue: https://github.com/home-assistant/core/issues/108296

Seed varies: renames 'async_create_task' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH215_core_128958'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH215_core_128958'
        )
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        files = self._base_workspace()
        # Apply seed-based renaming to prevent direct memorization
        suffixes = ["", "_alt", "_impl"]
        suffix = suffixes[seed % len(suffixes)]
        if suffix:
            for fpath in list(files.keys()):
                files[fpath] = files[fpath].replace('async_create_task', 'async_create_task' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH215_core_128958',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'home-assistant/core',
                "pr_number": 128958,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/home-assistant/core/pull/128958",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'homeassistant/components/nfandroidtv/__init__.py': '"""The NFAndroidTV integration."""\n\nfrom notifications_android_tv.notifications import ConnectError, Notifications\n\nfrom homeassistant.config_entries import ConfigEntry\nfrom homeassistant.const import CONF_HOST, Platform\nfrom homeassistant.core import HomeAssistant\nfrom homeassistant.exceptions import ConfigEntryNotReady\nfrom homeassistant.helpers import config_validation as cv, discovery\nfrom homeassistant.helpers.typing import ConfigType\n\nfrom .const import DATA_HASS_CONFIG, DOMAIN\n\nPLATFORMS = [Platform.NOTIFY]\n\nCONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)\n\n\nasync def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:\n    """Set up the NFAndroidTV component."""\n\n    hass.data[DATA_HASS_CONFIG] = config\n    return True\n\n\nasync def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:\n    """Set up NFAndroidTV from a config entry."""\n    try:\n        await hass.async_add_executor_job(Notifications, entry.data[CONF_HOST])\n    except ConnectError as ex:\n        raise ConfigEntryNotReady(\n            f"Failed to connect to host: {entry.data[CONF_HOST]}"\n        ) from ex\n\n    hass.data.setdefault(DOMAIN, {})\n\n    hass.async_create_task(\n        discovery.async_load_platform(\n            hass,\n            Platform.NOTIFY,\n            DOMAIN,\n            dict(entry.data),\n            hass.data[DATA_HASS_CONFIG],\n        )\n    )\n\n    return True\n\n\nasync def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:\n    """Unload a config entry."""\n    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)\n',
            'homeassistant/components/nfandroidtv/notify.py': '"""Notifications for Android TV notification service."""\n\nfrom __future__ import annotations\n\nfrom io import BufferedReader\nimport logging\nfrom typing import Any\n\nfrom notifications_android_tv import Notifications\nimport requests\nfrom requests.auth import HTTPBasicAuth, HTTPDigestAuth\nimport voluptuous as vol\n\nfrom homeassistant.components.notify import (\n    ATTR_DATA,\n    ATTR_TITLE,\n    ATTR_TITLE_DEFAULT,\n    BaseNotificationService,\n)\nfrom homeassistant.const import CONF_HOST\nfrom homeassistant.core import HomeAssistant\nfrom homeassistant.exceptions import ServiceValidationError\nfrom homeassistant.helpers import config_validation as cv\nfrom homeassistant.helpers.typing import ConfigType, DiscoveryInfoType\n\nfrom .const import (\n    ATTR_COLOR,\n    ATTR_DURATION,\n    ATTR_FONTSIZE,\n    ATTR_ICON,\n    ATTR_ICON_AUTH,\n    ATTR_ICON_AUTH_DIGEST,\n    ATTR_ICON_PASSWORD,\n    ATTR_ICON_PATH,\n    ATTR_ICON_URL,\n    ATTR_ICON_USERNAME,\n    ATTR_IMAGE,\n    ATTR_IMAGE_AUTH,\n    ATTR_IMAGE_AUTH_DIGEST,\n    ATTR_IMAGE_PASSWORD,\n    ATTR_IMAGE_PATH,\n    ATTR_IMAGE_URL,\n    ATTR_IMAGE_USERNAME,\n    ATTR_INTERRUPT,\n    ATTR_POSITION,\n    ATTR_TRANSPARENCY,\n    DEFAULT_TIMEOUT,\n    DOMAIN,\n)\n\n_LOGGER = logging.getLogger(__name__)\n\n\nasync def async_get_service(\n    hass: HomeAssistant,\n    config: ConfigType,\n    discovery_info: DiscoveryInfoType | None = None,\n) -> NFAndroidTVNotificationService | None:\n    """Get the NFAndroidTV notification service."""\n    if discovery_info is None:\n        return None\n    notify = await hass.async_add_executor_job(Notifications, discovery_info[CONF_HOST])\n    return NFAndroidTVNotificationService(\n        notify,\n        hass.config.is_allowed_path,\n    )\n\n\nclass NFAndroidTVNotificationService(BaseNotificationService):\n    """Notification service for Notifications for Android TV."""\n\n    def __init__(\n        self,\n        notify: Notifications,\n        is_allowed_path: Any,\n    ) -> None:\n        """Initialize the service."""\n        self.notify = notify\n        self.is_allowed_path = is_allowed_path\n\n    def send_message(self, message: str, **kwargs: Any) -> None:\n        """Send a message to a Android TV device."""\n        data: dict | None = kwargs.get(ATTR_DATA)\n        title = kwargs.get(ATTR_TITLE, ATTR_TITLE_DEFAULT)\n        duration = None\n        fontsize = None\n        position = None\n        transparency = None\n        bkgcolor = None\n        interrupt = False\n        icon = None\n        image_file = None\n        if data:\n            if ATTR_DURATION in data:\n                try:\n                    duration = int(\n                        data.get(ATTR_DURATION, Notifications.DEFAULT_DURATION)\n                    )\n                except ValueError:\n                    _LOGGER.warning(\n                        "Invalid duration-value: %s", data.get(ATTR_DURATION)\n                    )\n            if ATTR_FONTSIZE in data:\n                if data.get(ATTR_FONTSIZE) in Notifications.FONTSIZES:\n                    fontsize = data.get(ATTR_FONTSIZE)\n                else:\n                    _LOGGER.warning(\n                        "Invalid fontsize-value: %s", data.get(ATTR_FONTSIZE)\n                    )\n            if ATTR_POSITION in data:\n                if data.get(ATTR_POSITION) in Notifications.POSITIONS:\n                    position = data.get(ATTR_POSITION)\n                else:\n                    _LOGGER.warning(\n                        "Invalid position-value: %s", data.get(ATTR_POSITION)\n                    )\n            if ATTR_TRANSPARENCY in data:\n                if data.get(ATTR_TRANSPARENCY) in Notifications.TRANSPARENCIES:\n                    transparency = data.get(ATTR_TRANSPARENCY)\n                else:\n                    _LOGGER.warning(\n                        "Invalid transparency-value: %s",\n                        data.get(ATTR_TRANSPARENCY),\n                    )\n            if ATTR_COLOR in data:\n                if data.get(ATTR_COLOR) in Notifications.BKG_COLORS:\n                    bkgcolor = data.get(ATTR_COLOR)\n                else:\n                    _LOGGER.warning("Invalid color-value: %s", data.get(ATTR_COLOR))\n            if ATTR_INTERRUPT in data:\n                try:\n                    interrupt = cv.boolean(data.get(ATTR_INTERRUPT))\n                except vol.Invalid:\n                    _LOGGER.warning(\n                        "Invalid interrupt-value: %s", data.get(ATTR_INTERRUPT)\n                    )\n            if imagedata := data.get(ATTR_IMAGE):\n                if isinstance(imagedata, str):\n                    image_file = (\n                        self.load_file(url=imagedata)\n                        if imagedata.startswith("http")\n                        else self.load_file(local_path=imagedata)\n                    )\n                elif isinstance(imagedata, dict):\n                    image_file = self.load_file(\n                        url=imagedata.get(ATTR_IMAGE_URL),\n                        local_path=imagedata.get(ATTR_IMAGE_PATH),\n                        username=imagedata.get(ATTR_IMAGE_USERNAME),\n                        password=imagedata.get(ATTR_IMAGE_PASSWORD),\n                        auth=imagedata.get(ATTR_IMAGE_AUTH),\n                    )\n                else:\n                    raise ServiceValidationError(\n                        "Invalid image provided",\n                        translation_domain=DOMAIN,\n                        translation_key="invalid_notification_image",\n                        translation_placeholders={"type": type(imagedata).__name__},\n                    )\n            if icondata := data.get(ATTR_ICON):\n                if isinstance(icondata, str):\n                    icondata = (\n                        self.load_file(url=icondata)\n                        if icondata.startswith("http")\n                        else self.load_file(local_path=icondata)\n                    )\n                elif isinstance(icondata, dict):\n                    icon = self.load_file(\n                        url=icondata.get(ATTR_ICON_URL),\n                        local_path=icondata.get(ATTR_ICON_PATH),\n                        username=icondata.get(ATTR_ICON_USERNAME),\n                        password=icondata.get(ATTR_ICON_PASSWORD),\n                        auth=icondata.get(ATTR_ICON_AUTH),\n                    )\n                else:\n                    raise ServiceValidationError(\n                        "Invalid Icon provided",\n                        translation_domain=DOMAIN,\n                        translation_key="invalid_notification_icon",\n                        translation_placeholders={"type": type(icondata).__name__},\n                    )\n        self.notify.send(\n            message,\n            title=title,\n            duration=duration,\n            fontsize=fontsize,\n            position=position,\n            bkgcolor=bkgcolor,\n            transparency=transparency,\n            interrupt=interrupt,\n            icon=icon,\n            image_file=image_file,\n        )\n\n    def load_file(\n        self,\n        url: str | None = None,\n        local_path: str | None = None,\n        username: str | None = None,\n        password: str | None = None,\n        auth: str | None = None,\n    ) -> BufferedReader | bytes | None:\n        """Load image/document/etc from a local path or URL."""\n        try:\n            if url is not None:\n                # Check whether authentication parameters are provided\n                if username is not None and password is not None:\n                    # Use digest or basic authentication\n                    auth_: HTTPDigestAuth | HTTPBasicAuth\n                    if auth in (ATTR_IMAGE_AUTH_DIGEST, ATTR_ICON_AUTH_DIGEST):\n                        auth_ = HTTPDigestAuth(username, password)\n                    else:\n                        auth_ = HTTPBasicAuth(username, password)\n                    # Load file from URL with authentication\n                    req = requests.get(url, auth=auth_, timeout=DEFAULT_TIMEOUT)\n                else:\n                    # Load file from URL without authentication\n                    req = requests.get(url, timeout=DEFAULT_TIMEOUT)\n                return req.content\n\n            if local_path is not None:\n                # Check whether path is whitelisted in configuration.yaml\n                if self.is_allowed_path(local_path):\n                    return open(local_path, "rb")\n                _LOGGER.warning("\'%s\' is not secure to load data from!", local_path)\n            else:\n                _LOGGER.warning("Neither URL nor local path found in params!")\n\n        except OSError as error:\n            _LOGGER.error("Can\'t load from url or local path: %s", error)\n\n        return None\n',
        }
