"""
Parameterized generator for GH230_core_163096.

Source PR:    https://github.com/home-assistant/core/pull/163096
Source Issue: https://github.com/home-assistant/core/issues/150737

Seed varies: renames 'annotations' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH230_core_163096'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH230_core_163096'
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
            task_id='GH230_core_163096',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'home-assistant/core',
                "pr_number": 163096,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/home-assistant/core/pull/163096",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'homeassistant/components/dwd_weather_warnings/sensor.py': '"""Support for getting statistical data from a DWD Weather Warnings.\n\nData is fetched from DWD:\nhttps://rcccm.dwd.de/DE/wetter/warnungen_aktuell/objekt_einbindung/objekteinbindung.html\n\nWarnungen vor extremem Unwetter (Stufe 4)  # codespell:ignore vor,extremem\nUnwetterwarnungen (Stufe 3)\nWarnungen vor markantem Wetter (Stufe 2)  # codespell:ignore vor\nWetterwarnungen (Stufe 1)\n"""\n\nfrom __future__ import annotations\n\nfrom typing import Any\n\nfrom homeassistant.components.sensor import SensorEntity, SensorEntityDescription\nfrom homeassistant.core import HomeAssistant\nfrom homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo\nfrom homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback\nfrom homeassistant.helpers.update_coordinator import CoordinatorEntity\n\nfrom .const import (\n    ADVANCE_WARNING_SENSOR,\n    API_ATTR_WARNING_COLOR,\n    API_ATTR_WARNING_DESCRIPTION,\n    API_ATTR_WARNING_END,\n    API_ATTR_WARNING_HEADLINE,\n    API_ATTR_WARNING_INSTRUCTION,\n    API_ATTR_WARNING_LEVEL,\n    API_ATTR_WARNING_NAME,\n    API_ATTR_WARNING_PARAMETERS,\n    API_ATTR_WARNING_START,\n    API_ATTR_WARNING_TYPE,\n    ATTR_LAST_UPDATE,\n    ATTR_REGION_ID,\n    ATTR_REGION_NAME,\n    ATTR_WARNING_COUNT,\n    CURRENT_WARNING_SENSOR,\n    DOMAIN,\n)\nfrom .coordinator import DwdWeatherWarningsConfigEntry, DwdWeatherWarningsCoordinator\n\nSENSOR_TYPES: tuple[SensorEntityDescription, ...] = (\n    SensorEntityDescription(\n        key=CURRENT_WARNING_SENSOR,\n        translation_key=CURRENT_WARNING_SENSOR,\n    ),\n    SensorEntityDescription(\n        key=ADVANCE_WARNING_SENSOR,\n        translation_key=ADVANCE_WARNING_SENSOR,\n    ),\n)\n\n\nasync def async_setup_entry(\n    hass: HomeAssistant,\n    entry: DwdWeatherWarningsConfigEntry,\n    async_add_entities: AddConfigEntryEntitiesCallback,\n) -> None:\n    """Set up entities from config entry."""\n    coordinator = entry.runtime_data\n\n    unique_id = entry.unique_id\n    assert unique_id\n\n    async_add_entities(\n        DwdWeatherWarningsSensor(coordinator, description, unique_id)\n        for description in SENSOR_TYPES\n    )\n\n\nclass DwdWeatherWarningsSensor(\n    CoordinatorEntity[DwdWeatherWarningsCoordinator], SensorEntity\n):\n    """Representation of a DWD-Weather-Warnings sensor."""\n\n    _attr_attribution = "Data provided by DWD"\n    _attr_has_entity_name = True\n\n    def __init__(\n        self,\n        coordinator: DwdWeatherWarningsCoordinator,\n        description: SensorEntityDescription,\n        unique_id: str,\n    ) -> None:\n        """Initialize a DWD-Weather-Warnings sensor."""\n        super().__init__(coordinator)\n\n        self.entity_description = description\n        self._attr_unique_id = f"{unique_id}-{description.key}"\n\n        self._attr_device_info = DeviceInfo(\n            identifiers={(DOMAIN, unique_id)},\n            name=coordinator.api.warncell_name,\n            entry_type=DeviceEntryType.SERVICE,\n        )\n\n    @property\n    def native_value(self) -> int | None:\n        """Return the state of the sensor."""\n        if self.entity_description.key == CURRENT_WARNING_SENSOR:\n            return self.coordinator.api.current_warning_level\n\n        return self.coordinator.api.expected_warning_level\n\n    @property\n    def extra_state_attributes(self) -> dict[str, Any]:\n        """Return the state attributes of the sensor."""\n        data = {\n            ATTR_REGION_NAME: self.coordinator.api.warncell_name,\n            ATTR_REGION_ID: self.coordinator.api.warncell_id,\n            ATTR_LAST_UPDATE: self.coordinator.api.last_update,\n        }\n\n        if self.entity_description.key == CURRENT_WARNING_SENSOR:\n            searched_warnings = self.coordinator.api.current_warnings\n        else:\n            searched_warnings = self.coordinator.api.expected_warnings\n\n        data[ATTR_WARNING_COUNT] = len(searched_warnings)\n\n        for i, warning in enumerate(searched_warnings, 1):\n            data[f"warning_{i}_name"] = warning[API_ATTR_WARNING_NAME]\n            data[f"warning_{i}_type"] = warning[API_ATTR_WARNING_TYPE]\n            data[f"warning_{i}_level"] = warning[API_ATTR_WARNING_LEVEL]\n            data[f"warning_{i}_headline"] = warning[API_ATTR_WARNING_HEADLINE]\n            data[f"warning_{i}_description"] = warning[API_ATTR_WARNING_DESCRIPTION]\n            data[f"warning_{i}_instruction"] = warning[API_ATTR_WARNING_INSTRUCTION]\n            data[f"warning_{i}_start"] = warning[API_ATTR_WARNING_START]\n            data[f"warning_{i}_end"] = warning[API_ATTR_WARNING_END]\n            data[f"warning_{i}_parameters"] = warning[API_ATTR_WARNING_PARAMETERS]\n            data[f"warning_{i}_color"] = warning[API_ATTR_WARNING_COLOR]\n\n            # Dictionary for the attribute containing the complete warning.\n            warning_copy = warning.copy()\n            warning_copy[API_ATTR_WARNING_START] = data[f"warning_{i}_start"]\n            warning_copy[API_ATTR_WARNING_END] = data[f"warning_{i}_end"]\n            data[f"warning_{i}"] = warning_copy\n\n        return data\n\n    @property\n    def available(self) -> bool:\n        """Could the device be accessed during the last update call."""\n        return self.coordinator.api.data_valid\n',
            'tests/components/dwd_weather_warnings/test_init.py': '"""Tests for Deutscher Wetterdienst (DWD) Weather Warnings integration."""\n\nfrom unittest.mock import MagicMock\n\nfrom homeassistant.components.dwd_weather_warnings.const import (\n    CONF_REGION_DEVICE_TRACKER,\n    DOMAIN,\n)\nfrom homeassistant.components.dwd_weather_warnings.coordinator import (\n    DwdWeatherWarningsCoordinator,\n)\nfrom homeassistant.config_entries import ConfigEntryState\nfrom homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE, STATE_HOME\nfrom homeassistant.core import HomeAssistant\nfrom homeassistant.helpers import device_registry as dr, entity_registry as er\nfrom homeassistant.helpers.device_registry import DeviceEntryType\n\nfrom . import init_integration\n\nfrom tests.common import MockConfigEntry\n\n\nasync def test_load_unload_entry(\n    hass: HomeAssistant,\n    mock_identifier_entry: MockConfigEntry,\n    mock_dwdwfsapi: MagicMock,\n) -> None:\n    """Test loading and unloading the integration with a region identifier based entry."""\n    entry = await init_integration(hass, mock_identifier_entry)\n\n    assert entry.state is ConfigEntryState.LOADED\n    assert isinstance(entry.runtime_data, DwdWeatherWarningsCoordinator)\n\n    assert await hass.config_entries.async_unload(entry.entry_id)\n    await hass.async_block_till_done()\n\n    assert entry.state is ConfigEntryState.NOT_LOADED\n\n\nasync def test_removing_old_device(\n    hass: HomeAssistant,\n    mock_identifier_entry: MockConfigEntry,\n    mock_dwdwfsapi: MagicMock,\n    device_registry: dr.DeviceRegistry,\n) -> None:\n    """Test removing old device when reloading the integration."""\n\n    mock_identifier_entry.add_to_hass(hass)\n\n    device_registry.async_get_or_create(\n        identifiers={(DOMAIN, mock_identifier_entry.entry_id)},\n        config_entry_id=mock_identifier_entry.entry_id,\n        entry_type=DeviceEntryType.SERVICE,\n        name="test",\n    )\n\n    assert (\n        device_registry.async_get_device(\n            identifiers={(DOMAIN, mock_identifier_entry.entry_id)}\n        )\n        is not None\n    )\n\n    await hass.config_entries.async_setup(mock_identifier_entry.entry_id)\n    await hass.async_block_till_done()\n\n    assert (\n        device_registry.async_get_device(\n            identifiers={(DOMAIN, mock_identifier_entry.entry_id)}\n        )\n        is None\n    )\n\n\nasync def test_load_invalid_registry_entry(\n    hass: HomeAssistant, mock_tracker_entry: MockConfigEntry\n) -> None:\n    """Test loading the integration with an invalid registry entry ID."""\n    INVALID_DATA = mock_tracker_entry.data.copy()\n    INVALID_DATA[CONF_REGION_DEVICE_TRACKER] = "invalid_registry_id"\n\n    entry = await init_integration(\n        hass, MockConfigEntry(domain=DOMAIN, data=INVALID_DATA)\n    )\n    assert entry.state is ConfigEntryState.SETUP_RETRY\n\n\nasync def test_load_missing_device_tracker(\n    hass: HomeAssistant, mock_tracker_entry: MockConfigEntry\n) -> None:\n    """Test loading the integration with a missing device tracker."""\n    entry = await init_integration(hass, mock_tracker_entry)\n    assert entry.state is ConfigEntryState.SETUP_RETRY\n\n\nasync def test_load_missing_required_attribute(\n    hass: HomeAssistant, mock_tracker_entry: MockConfigEntry\n) -> None:\n    """Test loading the integration with a device tracker missing a required attribute."""\n    mock_tracker_entry.add_to_hass(hass)\n    hass.states.async_set(\n        mock_tracker_entry.data[CONF_REGION_DEVICE_TRACKER],\n        STATE_HOME,\n        {ATTR_LONGITUDE: "7.610263"},\n    )\n\n    await hass.config_entries.async_setup(mock_tracker_entry.entry_id)\n    await hass.async_block_till_done()\n    assert mock_tracker_entry.state is ConfigEntryState.SETUP_RETRY\n\n\nasync def test_load_valid_device_tracker(\n    hass: HomeAssistant,\n    entity_registry: er.EntityRegistry,\n    mock_tracker_entry: MockConfigEntry,\n    mock_dwdwfsapi: MagicMock,\n) -> None:\n    """Test loading the integration with a valid device tracker based entry."""\n    mock_tracker_entry.add_to_hass(hass)\n    entity_registry.async_get_or_create(\n        "device_tracker",\n        mock_tracker_entry.domain,\n        "uuid",\n        suggested_object_id="test_gps",\n        config_entry=mock_tracker_entry,\n    )\n\n    hass.states.async_set(\n        mock_tracker_entry.data[CONF_REGION_DEVICE_TRACKER],\n        STATE_HOME,\n        {ATTR_LATITUDE: "50.180454", ATTR_LONGITUDE: "7.610263"},\n    )\n\n    await hass.config_entries.async_setup(mock_tracker_entry.entry_id)\n    await hass.async_block_till_done()\n\n    assert mock_tracker_entry.state is ConfigEntryState.LOADED\n    assert isinstance(mock_tracker_entry.runtime_data, DwdWeatherWarningsCoordinator)\n',
        }
