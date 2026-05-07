"""
Parameterized generator for GH352_core_143286.

Source PR:    https://github.com/home-assistant/core/pull/143286
Source Issue: https://github.com/home-assistant/core/issues/143149

Seed varies: renames 'callback' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH352_core_143286'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH352_core_143286'
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
                files[fpath] = files[fpath].replace('callback', 'callback' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH352_core_143286',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'home-assistant/core',
                "pr_number": 143286,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/home-assistant/core/pull/143286",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'homeassistant/components/surepetcare/binary_sensor.py': '"""Support for Sure PetCare Flaps/Pets binary sensors."""\n\nfrom __future__ import annotations\n\nfrom typing import cast\n\nfrom surepy.entities import SurepyEntity\nfrom surepy.entities.pet import Pet as SurepyPet\nfrom surepy.enums import EntityType, Location\n\nfrom homeassistant.components.binary_sensor import (\n    BinarySensorDeviceClass,\n    BinarySensorEntity,\n)\nfrom homeassistant.config_entries import ConfigEntry\nfrom homeassistant.const import EntityCategory\nfrom homeassistant.core import HomeAssistant, callback\nfrom homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback\n\nfrom .const import DOMAIN\nfrom .coordinator import SurePetcareDataCoordinator\nfrom .entity import SurePetcareEntity\n\n\nasync def async_setup_entry(\n    hass: HomeAssistant,\n    entry: ConfigEntry,\n    async_add_entities: AddConfigEntryEntitiesCallback,\n) -> None:\n    """Set up Sure PetCare Flaps binary sensors based on a config entry."""\n\n    entities: list[SurePetcareBinarySensor] = []\n\n    coordinator: SurePetcareDataCoordinator = hass.data[DOMAIN][entry.entry_id]\n\n    for surepy_entity in coordinator.data.values():\n        # connectivity\n        if surepy_entity.type in [\n            EntityType.CAT_FLAP,\n            EntityType.PET_FLAP,\n            EntityType.FEEDER,\n            EntityType.FELAQUA,\n        ]:\n            entities.append(DeviceConnectivity(surepy_entity.id, coordinator))\n        elif surepy_entity.type == EntityType.PET:\n            entities.append(Pet(surepy_entity.id, coordinator))\n        elif surepy_entity.type == EntityType.HUB:\n            entities.append(Hub(surepy_entity.id, coordinator))\n\n    async_add_entities(entities)\n\n\nclass SurePetcareBinarySensor(SurePetcareEntity, BinarySensorEntity):\n    """A binary sensor implementation for Sure Petcare Entities."""\n\n    def __init__(\n        self,\n        surepetcare_id: int,\n        coordinator: SurePetcareDataCoordinator,\n    ) -> None:\n        """Initialize a Sure Petcare binary sensor."""\n        super().__init__(surepetcare_id, coordinator)\n\n        self._attr_name = self._device_name\n        self._attr_unique_id = self._device_id\n\n\nclass Hub(SurePetcareBinarySensor):\n    """Sure Petcare Hub."""\n\n    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY\n    _attr_entity_category = EntityCategory.DIAGNOSTIC\n\n    @property\n    def available(self) -> bool:\n        """Return True if entity is available."""\n        return super().available and bool(self._attr_is_on)\n\n    @callback\n    def _update_attr(self, surepy_entity: SurepyEntity) -> None:\n        """Get the latest data and update the state."""\n        state = surepy_entity.raw_data()["status"]\n        self._attr_is_on = self._attr_available = bool(state["online"])\n        if surepy_entity.raw_data():\n            self._attr_extra_state_attributes = {\n                "led_mode": int(surepy_entity.raw_data()["status"]["led_mode"]),\n                "pairing_mode": bool(\n                    surepy_entity.raw_data()["status"]["pairing_mode"]\n                ),\n            }\n        else:\n            self._attr_extra_state_attributes = {}\n\n\nclass Pet(SurePetcareBinarySensor):\n    """Sure Petcare Pet."""\n\n    _attr_device_class = BinarySensorDeviceClass.PRESENCE\n\n    @callback\n    def _update_attr(self, surepy_entity: SurepyEntity) -> None:\n        """Get the latest data and update the state."""\n        surepy_entity = cast(SurepyPet, surepy_entity)\n        state = surepy_entity.location\n        try:\n            self._attr_is_on = bool(Location(state.where) == Location.INSIDE)\n        except (KeyError, TypeError):\n            self._attr_is_on = False\n        if state:\n            self._attr_extra_state_attributes = {\n                "since": state.since,\n                "where": state.where,\n            }\n        else:\n            self._attr_extra_state_attributes = {}\n\n\nclass DeviceConnectivity(SurePetcareBinarySensor):\n    """Sure Petcare Device."""\n\n    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY\n    _attr_entity_category = EntityCategory.DIAGNOSTIC\n\n    def __init__(\n        self,\n        surepetcare_id: int,\n        coordinator: SurePetcareDataCoordinator,\n    ) -> None:\n        """Initialize a Sure Petcare Device."""\n        super().__init__(surepetcare_id, coordinator)\n        self._attr_name = f"{self._device_name} Connectivity"\n        self._attr_unique_id = f"{self._device_id}-connectivity"\n\n    @callback\n    def _update_attr(self, surepy_entity: SurepyEntity) -> None:\n        state = surepy_entity.raw_data()["status"]\n        self._attr_is_on = bool(state)\n        if state:\n            self._attr_extra_state_attributes = {\n                "device_rssi": f"{state[\'signal\'][\'device_rssi\']:.2f}",\n                "hub_rssi": f"{state[\'signal\'][\'hub_rssi\']:.2f}",\n            }\n        else:\n            self._attr_extra_state_attributes = {}\n',
            'tests/components/surepetcare/__init__.py': '"""Tests for Sure Petcare integration."""\n\nHOUSEHOLD_ID = 987654321\nHUB_ID = 123456789\n\nMOCK_HUB = {\n    "id": HUB_ID,\n    "product_id": 1,\n    "household_id": HOUSEHOLD_ID,\n    "name": "Hub",\n    "status": {"online": True, "led_mode": 0, "pairing_mode": 0},\n}\n\nMOCK_FEEDER = {\n    "id": 12345,\n    "product_id": 4,\n    "household_id": HOUSEHOLD_ID,\n    "name": "Feeder",\n    "parent": {"product_id": 1, "id": HUB_ID},\n    "status": {\n        "battery": 6.4,\n        "locking": {"mode": 0},\n        "learn_mode": 0,\n        "signal": {"device_rssi": 60, "hub_rssi": 65},\n    },\n}\n\nMOCK_FELAQUA = {\n    "id": 31337,\n    "product_id": 8,\n    "household_id": HOUSEHOLD_ID,\n    "name": "Felaqua",\n    "parent": {"product_id": 1, "id": HUB_ID},\n    "status": {\n        "battery": 6.4,\n        "signal": {"device_rssi": 70, "hub_rssi": 65},\n        "online": True,\n    },\n}\n\nMOCK_CAT_FLAP = {\n    "id": 13579,\n    "product_id": 6,\n    "household_id": HOUSEHOLD_ID,\n    "name": "Cat Flap",\n    "parent": {"product_id": 1, "id": HUB_ID},\n    "status": {\n        "battery": 6.4,\n        "locking": {"mode": 0},\n        "learn_mode": 0,\n        "signal": {"device_rssi": 65, "hub_rssi": 64},\n        "online": True,\n    },\n}\n\nMOCK_PET_FLAP = {\n    "id": 13576,\n    "product_id": 3,\n    "household_id": HOUSEHOLD_ID,\n    "name": "Pet Flap",\n    "parent": {"product_id": 1, "id": HUB_ID},\n    "status": {\n        "battery": 6.4,\n        "locking": {"mode": 0},\n        "learn_mode": 0,\n        "signal": {"device_rssi": 70, "hub_rssi": 65},\n        "online": True,\n    },\n}\n\nMOCK_PET = {\n    "id": 24680,\n    "household_id": HOUSEHOLD_ID,\n    "name": "Pet",\n    "position": {"since": "2020-08-23T23:10:50", "where": 1},\n    "status": {},\n}\n\nMOCK_API_DATA = {\n    "devices": [MOCK_HUB, MOCK_CAT_FLAP, MOCK_PET_FLAP, MOCK_FEEDER, MOCK_FELAQUA],\n    "pets": [MOCK_PET],\n}\n',
        }
