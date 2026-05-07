"""
Parameterized generator for GH233_core_146639.

Source PR:    https://github.com/home-assistant/core/pull/146639
Source Issue: https://github.com/home-assistant/core/issues/110098

Seed varies: renames 'annotations' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH233_core_146639'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH233_core_146639'
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
                files[fpath] = files[fpath].replace('annotations', 'annotations' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH233_core_146639',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'home-assistant/core',
                "pr_number": 146639,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/home-assistant/core/pull/146639",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'homeassistant/components/traccar_server/coordinator.py': '"""Data update coordinator for Traccar Server."""\n\nfrom __future__ import annotations\n\nimport asyncio\nfrom datetime import datetime\nfrom logging import DEBUG as LOG_LEVEL_DEBUG\nfrom typing import TYPE_CHECKING, Any, TypedDict\n\nfrom pytraccar import (\n    ApiClient,\n    DeviceModel,\n    GeofenceModel,\n    PositionModel,\n    SubscriptionData,\n    TraccarException,\n)\n\nfrom homeassistant.config_entries import ConfigEntry\nfrom homeassistant.core import HomeAssistant\nfrom homeassistant.helpers.dispatcher import async_dispatcher_send\nfrom homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed\nfrom homeassistant.util import dt as dt_util\n\nfrom .const import (\n    CONF_CUSTOM_ATTRIBUTES,\n    CONF_EVENTS,\n    CONF_MAX_ACCURACY,\n    CONF_SKIP_ACCURACY_FILTER_FOR,\n    DOMAIN,\n    EVENTS,\n    LOGGER,\n)\nfrom .helpers import get_device, get_first_geofence\n\n\nclass TraccarServerCoordinatorDataDevice(TypedDict):\n    """Traccar Server coordinator data."""\n\n    device: DeviceModel\n    geofence: GeofenceModel | None\n    position: PositionModel\n    attributes: dict[str, Any]\n\n\ntype TraccarServerCoordinatorData = dict[int, TraccarServerCoordinatorDataDevice]\n\n\nclass TraccarServerCoordinator(DataUpdateCoordinator[TraccarServerCoordinatorData]):\n    """Class to manage fetching Traccar Server data."""\n\n    config_entry: ConfigEntry\n\n    def __init__(\n        self,\n        hass: HomeAssistant,\n        config_entry: ConfigEntry,\n        client: ApiClient,\n    ) -> None:\n        """Initialize global Traccar Server data updater."""\n        super().__init__(\n            hass=hass,\n            logger=LOGGER,\n            config_entry=config_entry,\n            name=DOMAIN,\n            update_interval=None,\n        )\n        self.client = client\n        self.custom_attributes = config_entry.options.get(CONF_CUSTOM_ATTRIBUTES, [])\n        self.events = config_entry.options.get(CONF_EVENTS, [])\n        self.max_accuracy = config_entry.options.get(CONF_MAX_ACCURACY, 0.0)\n        self.skip_accuracy_filter_for = config_entry.options.get(\n            CONF_SKIP_ACCURACY_FILTER_FOR, []\n        )\n        self._geofences: list[GeofenceModel] = []\n        self._last_event_import: datetime | None = None\n        self._should_log_subscription_error: bool = True\n\n    async def _async_update_data(self) -> TraccarServerCoordinatorData:\n        """Fetch data from Traccar Server."""\n        LOGGER.debug("Updating device data")\n        data: TraccarServerCoordinatorData = {}\n        try:\n            (\n                devices,\n                positions,\n                geofences,\n            ) = await asyncio.gather(\n                self.client.get_devices(),\n                self.client.get_positions(),\n                self.client.get_geofences(),\n            )\n        except TraccarException as ex:\n            raise UpdateFailed(f"Error while updating device data: {ex}") from ex\n\n        if TYPE_CHECKING:\n            assert isinstance(devices, list[DeviceModel])  # type: ignore[misc]\n            assert isinstance(positions, list[PositionModel])  # type: ignore[misc]\n            assert isinstance(geofences, list[GeofenceModel])  # type: ignore[misc]\n\n        self._geofences = geofences\n\n        if self.logger.isEnabledFor(LOG_LEVEL_DEBUG):\n            self.logger.debug("Received devices: %s", devices)\n            self.logger.debug("Received positions: %s", positions)\n\n        for position in positions:\n            device_id = position["deviceId"]\n            if (device := get_device(device_id, devices)) is None:\n                self.logger.debug(\n                    "Device %s not found for position: %s",\n                    device_id,\n                    position["id"],\n                )\n                continue\n\n            if (\n                attr\n                := self._return_custom_attributes_if_not_filtered_by_accuracy_configuration(\n                    device, position\n                )\n            ) is None:\n                self.logger.debug(\n                    "Skipping position update %s for %s due to accuracy filter",\n                    position["id"],\n                    device_id,\n                )\n                continue\n\n            data[device_id] = {\n                "device": device,\n                "geofence": get_first_geofence(\n                    geofences,\n                    position["geofenceIds"] or [],\n                ),\n                "position": position,\n                "attributes": attr,\n            }\n\n        return data\n\n    async def handle_subscription_data(self, data: SubscriptionData) -> None:\n        """Handle subscription data."""\n        self.logger.debug("Received subscription data: %s", data)\n        self._should_log_subscription_error = True\n        update_devices = set()\n        for device in data.get("devices") or []:\n            if (device_id := device["id"]) not in self.data:\n                self.logger.debug("Device %s not found in data", device_id)\n                continue\n\n            if (\n                attr\n                := self._return_custom_attributes_if_not_filtered_by_accuracy_configuration(\n                    device, self.data[device_id]["position"]\n                )\n            ) is None:\n                continue\n\n            self.data[device_id]["device"] = device\n            self.data[device_id]["attributes"] = attr\n            update_devices.add(device_id)\n\n        for position in data.get("positions") or []:\n            if (device_id := position["deviceId"]) not in self.data:\n                self.logger.debug(\n                    "Device %s for position %s not found in data",\n                    device_id,\n                    position["id"],\n                )\n                continue\n\n            if (\n                attr\n                := self._return_custom_attributes_if_not_filtered_by_accuracy_configuration(\n                    self.data[device_id]["device"], position\n                )\n            ) is None:\n                self.logger.debug(\n                    "Skipping position update %s for %s due to accuracy filter",\n                    position["id"],\n                    device_id,\n                )\n                continue\n\n            self.data[device_id]["position"] = position\n            self.data[device_id]["attributes"] = attr\n            self.data[device_id]["geofence"] = get_first_geofence(\n                self._geofences,\n                position["geofenceIds"] or [],\n            )\n            update_devices.add(device_id)\n\n        for device_id in update_devices:\n            async_dispatcher_send(self.hass, f"{DOMAIN}_{device_id}")\n\n    async def import_events(self, _: datetime) -> None:\n        """Import events from Traccar."""\n        start_time = dt_util.utcnow().replace(tzinfo=None)\n        end_time = None\n\n        if self._last_event_import is not None:\n            end_time = start_time - (start_time - self._last_event_import)\n\n        events = await self.client.get_reports_events(\n            devices=list(self.data),\n            start_time=start_time,\n            end_time=end_time,\n            event_types=self.events,\n        )\n        if not events:\n            return\n\n        self._last_event_import = start_time\n        for event in events:\n            device = self.data[event["deviceId"]]["device"]\n            self.hass.bus.async_fire(\n                # This goes against two of the HA core guidelines:\n                # 1. Event names should be prefixed with the domain name of\n                #    the integration\n                # 2. This should be event entities\n                #\n                # However, to not break it for those who currently use\n                # the "old" integration, this is kept as is.\n                f"traccar_{EVENTS[event[\'type\']]}",\n                {\n                    "device_traccar_id": event["deviceId"],\n                    "device_name": device["name"] if device else None,\n                    "type": event["type"],\n                    "serverTime": event["eventTime"],\n                    "attributes": event["attributes"],\n                },\n            )\n\n    async def subscribe(self) -> None:\n        """Subscribe to events."""\n        try:\n            await self.client.subscribe(self.handle_subscription_data)\n        except TraccarException as ex:\n            if self._should_log_subscription_error:\n                self._should_log_subscription_error = False\n                LOGGER.error("Error while subscribing to Traccar: %s", ex)\n            # Retry after 10 seconds\n            await asyncio.sleep(10)\n            await self.subscribe()\n\n    def _return_custom_attributes_if_not_filtered_by_accuracy_configuration(\n        self,\n        device: DeviceModel,\n        position: PositionModel,\n    ) -> dict[str, Any] | None:\n        """Return a dictionary of custom attributes if not filtered by accuracy configuration."""\n        attr = {}\n        skip_accuracy_filter = False\n\n        for custom_attr in self.custom_attributes:\n            if custom_attr in self.skip_accuracy_filter_for:\n                skip_accuracy_filter = True\n            attr[custom_attr] = device["attributes"].get(\n                custom_attr,\n                position["attributes"].get(custom_attr, None),\n            )\n\n        accuracy = position["accuracy"] or 0.0\n        if (\n            not skip_accuracy_filter\n            and self.max_accuracy > 0\n            and accuracy > self.max_accuracy\n        ):\n            return None\n        return attr\n',
            'homeassistant/components/traccar_server/helpers.py': '"""Helper functions for the Traccar Server integration."""\n\nfrom __future__ import annotations\n\nfrom pytraccar import DeviceModel, GeofenceModel\n\n\ndef get_device(device_id: int, devices: list[DeviceModel]) -> DeviceModel | None:\n    """Return the device."""\n    return next(\n        (dev for dev in devices if dev["id"] == device_id),\n        None,\n    )\n\n\ndef get_first_geofence(\n    geofences: list[GeofenceModel],\n    target: list[int],\n) -> GeofenceModel | None:\n    """Return the geofence."""\n    return next(\n        (geofence for geofence in geofences if geofence["id"] in target),\n        None,\n    )\n',
        }
