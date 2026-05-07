"""
Parameterized generator for GH244_core_128267.

Source PR:    https://github.com/home-assistant/core/pull/128267
Source Issue: https://github.com/home-assistant/core/issues/128198

Seed varies: renames 'add_to_hass' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH244_core_128267'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH244_core_128267'
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
                files[fpath] = files[fpath].replace('add_to_hass', 'add_to_hass' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH244_core_128267',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'home-assistant/core',
                "pr_number": 128267,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/home-assistant/core/pull/128267",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'homeassistant/components/utility_meter/select.py': '"""Support for tariff selection."""\n\nfrom __future__ import annotations\n\nimport logging\n\nfrom homeassistant.components.select import SelectEntity\nfrom homeassistant.config_entries import ConfigEntry\nfrom homeassistant.const import CONF_UNIQUE_ID\nfrom homeassistant.core import HomeAssistant\nfrom homeassistant.helpers.device import async_device_info_to_link_from_entity\nfrom homeassistant.helpers.device_registry import DeviceInfo\nfrom homeassistant.helpers.entity_platform import AddEntitiesCallback\nfrom homeassistant.helpers.restore_state import RestoreEntity\nfrom homeassistant.helpers.typing import ConfigType, DiscoveryInfoType\n\nfrom .const import CONF_METER, CONF_SOURCE_SENSOR, CONF_TARIFFS, DATA_UTILITY\n\n_LOGGER = logging.getLogger(__name__)\n\n\nasync def async_setup_entry(\n    hass: HomeAssistant,\n    config_entry: ConfigEntry,\n    async_add_entities: AddEntitiesCallback,\n) -> None:\n    """Initialize Utility Meter config entry."""\n    name = config_entry.title\n    tariffs: list[str] = config_entry.options[CONF_TARIFFS]\n\n    unique_id = config_entry.entry_id\n\n    device_info = async_device_info_to_link_from_entity(\n        hass,\n        config_entry.options[CONF_SOURCE_SENSOR],\n    )\n\n    tariff_select = TariffSelect(\n        name,\n        tariffs,\n        unique_id,\n        device_info=device_info,\n    )\n    async_add_entities([tariff_select])\n\n\nasync def async_setup_platform(\n    hass: HomeAssistant,\n    conf: ConfigType,\n    async_add_entities: AddEntitiesCallback,\n    discovery_info: DiscoveryInfoType | None = None,\n) -> None:\n    """Set up the utility meter select."""\n    if discovery_info is None:\n        _LOGGER.error(\n            "This platform is not available to configure "\n            "from \'select:\' in configuration.yaml"\n        )\n        return\n\n    meter: str = discovery_info[CONF_METER]\n    conf_meter_unique_id: str | None = hass.data[DATA_UTILITY][meter].get(\n        CONF_UNIQUE_ID\n    )\n\n    async_add_entities(\n        [\n            TariffSelect(\n                meter,\n                discovery_info[CONF_TARIFFS],\n                conf_meter_unique_id,\n            )\n        ]\n    )\n\n\nclass TariffSelect(SelectEntity, RestoreEntity):\n    """Representation of a Tariff selector."""\n\n    _attr_translation_key = "tariff"\n\n    def __init__(\n        self,\n        name,\n        tariffs,\n        unique_id,\n        device_info: DeviceInfo | None = None,\n    ) -> None:\n        """Initialize a tariff selector."""\n        self._attr_name = name\n        self._attr_unique_id = unique_id\n        self._attr_device_info = device_info\n        self._current_tariff: str | None = None\n        self._tariffs = tariffs\n        self._attr_should_poll = False\n\n    @property\n    def options(self) -> list[str]:\n        """Return the available tariffs."""\n        return self._tariffs\n\n    @property\n    def current_option(self) -> str | None:\n        """Return current tariff."""\n        return self._current_tariff\n\n    async def async_added_to_hass(self) -> None:\n        """Run when entity about to be added."""\n        await super().async_added_to_hass()\n\n        state = await self.async_get_last_state()\n        if not state or state.state not in self._tariffs:\n            self._current_tariff = self._tariffs[0]\n        else:\n            self._current_tariff = state.state\n\n    async def async_select_option(self, option: str) -> None:\n        """Select new tariff (option)."""\n        self._current_tariff = option\n        self.async_write_ha_state()\n',
            'tests/components/utility_meter/test_select.py': '"""The tests for the utility_meter select platform."""\n\nfrom homeassistant.components.utility_meter.const import DOMAIN\nfrom homeassistant.core import HomeAssistant\nfrom homeassistant.helpers import device_registry as dr, entity_registry as er\n\nfrom tests.common import MockConfigEntry\n\n\nasync def test_device_id(\n    hass: HomeAssistant,\n    device_registry: dr.DeviceRegistry,\n    entity_registry: er.EntityRegistry,\n) -> None:\n    """Test for source entity device for Utility Meter."""\n    source_config_entry = MockConfigEntry()\n    source_config_entry.add_to_hass(hass)\n    source_device_entry = device_registry.async_get_or_create(\n        config_entry_id=source_config_entry.entry_id,\n        identifiers={("sensor", "identifier_test")},\n        connections={("mac", "30:31:32:33:34:35")},\n    )\n    source_entity = entity_registry.async_get_or_create(\n        "sensor",\n        "test",\n        "source",\n        config_entry=source_config_entry,\n        device_id=source_device_entry.id,\n    )\n    await hass.async_block_till_done()\n    assert entity_registry.async_get("sensor.test_source") is not None\n\n    utility_meter_config_entry = MockConfigEntry(\n        data={},\n        domain=DOMAIN,\n        options={\n            "cycle": "monthly",\n            "delta_values": False,\n            "name": "Energy",\n            "net_consumption": False,\n            "offset": 0,\n            "periodically_resetting": True,\n            "source": "sensor.test_source",\n            "tariffs": ["peak", "offpeak"],\n        },\n        title="Energy",\n    )\n\n    utility_meter_config_entry.add_to_hass(hass)\n\n    assert await hass.config_entries.async_setup(utility_meter_config_entry.entry_id)\n    await hass.async_block_till_done()\n\n    utility_meter_entity_select = entity_registry.async_get("select.energy")\n    assert utility_meter_entity_select is not None\n    assert utility_meter_entity_select.device_id == source_entity.device_id\n',
        }
