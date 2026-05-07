"""
Parameterized generator for GH271_core_165288.

Source PR:    https://github.com/home-assistant/core/pull/165288
Source Issue: https://github.com/home-assistant/core/issues/162701

Seed varies: renames 'abort' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH271_core_165288'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH271_core_165288'
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
                files[fpath] = files[fpath].replace('abort', 'abort' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH271_core_165288',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'home-assistant/core',
                "pr_number": 165288,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/home-assistant/core/pull/165288",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'homeassistant/components/freebox/config_flow.py': '"""Config flow to configure the Freebox integration."""\n\nimport logging\nfrom typing import Any\n\nfrom freebox_api.exceptions import AuthorizationError, HttpRequestError\nimport voluptuous as vol\n\nfrom homeassistant.config_entries import ConfigFlow, ConfigFlowResult\nfrom homeassistant.const import CONF_HOST, CONF_PORT\nfrom homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo\n\nfrom .const import DOMAIN\nfrom .router import get_api, get_hosts_list_if_supported\n\n_LOGGER = logging.getLogger(__name__)\n\n\nclass FreeboxFlowHandler(ConfigFlow, domain=DOMAIN):\n    """Handle a config flow."""\n\n    VERSION = 1\n\n    def __init__(self) -> None:\n        """Initialize config flow."""\n        self._data: dict[str, Any] = {}\n\n    async def async_step_user(\n        self, user_input: dict[str, Any] | None = None\n    ) -> ConfigFlowResult:\n        """Handle a flow initiated by the user."""\n        if user_input is None:\n            return self.async_show_form(\n                step_id="user",\n                data_schema=vol.Schema(\n                    {\n                        vol.Required(CONF_HOST): str,\n                        vol.Required(CONF_PORT): int,\n                    }\n                ),\n                errors={},\n            )\n\n        self._data = user_input\n\n        # Check if already configured\n        await self.async_set_unique_id(self._data[CONF_HOST])\n        self._abort_if_unique_id_configured()\n\n        return await self.async_step_link()\n\n    async def async_step_link(\n        self, user_input: dict[str, Any] | None = None\n    ) -> ConfigFlowResult:\n        """Attempt to link with the Freebox router.\n\n        Given a configured host, will ask the user to press the button\n        to connect to the router.\n        """\n        if user_input is None:\n            return self.async_show_form(step_id="link")\n\n        errors = {}\n\n        fbx = await get_api(self.hass, self._data[CONF_HOST])\n        try:\n            # Open connection and check authentication\n            await fbx.open(self._data[CONF_HOST], self._data[CONF_PORT])\n\n            # Check permissions\n            await fbx.system.get_config()\n            await get_hosts_list_if_supported(fbx)\n\n            # Close connection\n            await fbx.close()\n\n            return self.async_create_entry(\n                title=self._data[CONF_HOST],\n                data=self._data,\n            )\n\n        except AuthorizationError as error:\n            _LOGGER.error(error)\n            errors["base"] = "register_failed"\n\n        except HttpRequestError:\n            _LOGGER.error(\n                "Error connecting to the Freebox router at %s", self._data[CONF_HOST]\n            )\n            errors["base"] = "cannot_connect"\n\n        except Exception:\n            _LOGGER.exception(\n                "Unknown error connecting with Freebox router at %s",\n                self._data[CONF_HOST],\n            )\n            errors["base"] = "unknown"\n\n        return self.async_show_form(step_id="link", errors=errors)\n\n    async def async_step_zeroconf(\n        self, discovery_info: ZeroconfServiceInfo\n    ) -> ConfigFlowResult:\n        """Initialize flow from zeroconf."""\n        zeroconf_properties = discovery_info.properties\n        host = zeroconf_properties["api_domain"]\n        port = zeroconf_properties["https_port"]\n        return await self.async_step_user({CONF_HOST: host, CONF_PORT: port})\n',
            'homeassistant/components/freebox/strings.json': '{\n  "config": {\n    "abort": {\n      "already_configured": "[%key:common::config_flow::abort::already_configured_device%]"\n    },\n    "error": {\n      "cannot_connect": "[%key:common::config_flow::error::cannot_connect%]",\n      "register_failed": "Failed to register, please try again",\n      "unknown": "[%key:common::config_flow::error::unknown%]"\n    },\n    "step": {\n      "link": {\n        "description": "Select **Submit**, then touch the right arrow on the router to register Freebox with Home Assistant.\\n\\n![Location of button on the router](/static/images/config_freebox.png)",\n        "title": "Link Freebox router"\n      },\n      "user": {\n        "data": {\n          "host": "[%key:common::config_flow::data::host%]",\n          "port": "[%key:common::config_flow::data::port%]"\n        },\n        "data_description": {\n          "host": "The hostname or IP address of your Freebox router."\n        }\n      }\n    }\n  },\n  "services": {\n    "reboot": {\n      "description": "Reboots the Freebox.",\n      "name": "Reboot"\n    }\n  }\n}\n',
            'tests/components/freebox/test_config_flow.py': '"""Tests for the Freebox config flow."""\n\nfrom ipaddress import ip_address\nfrom unittest.mock import Mock, patch\n\nfrom freebox_api.exceptions import (\n    AuthorizationError,\n    HttpRequestError,\n    InvalidTokenError,\n)\n\nfrom homeassistant.components.freebox.const import DOMAIN\nfrom homeassistant.config_entries import SOURCE_USER, SOURCE_ZEROCONF\nfrom homeassistant.const import CONF_HOST, CONF_PORT\nfrom homeassistant.core import HomeAssistant\nfrom homeassistant.data_entry_flow import FlowResultType\nfrom homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo\n\nfrom .const import MOCK_HOST, MOCK_PORT\n\nfrom tests.common import MockConfigEntry\n\nMOCK_ZEROCONF_DATA = ZeroconfServiceInfo(\n    ip_address=ip_address("192.168.0.254"),\n    ip_addresses=[ip_address("192.168.0.254")],\n    port=80,\n    hostname="Freebox-Server.local.",\n    type="_fbx-api._tcp.local.",\n    name="Freebox Server._fbx-api._tcp.local.",\n    properties={\n        "api_version": "8.0",\n        "device_type": "FreeboxServer1,2",\n        "api_base_url": "/api/",\n        "uid": "b15ab20debb399f95001a9ca207d2777",\n        "https_available": "1",\n        "https_port": f"{MOCK_PORT}",\n        "box_model": "fbxgw-r2/full",\n        "box_model_name": "Freebox Server (r2)",\n        "api_domain": MOCK_HOST,\n    },\n)\n\n\nasync def test_user(hass: HomeAssistant) -> None:\n    """Test user config."""\n    result = await hass.config_entries.flow.async_init(\n        DOMAIN, context={"source": SOURCE_USER}\n    )\n    assert result["type"] is FlowResultType.FORM\n    assert result["step_id"] == "user"\n\n    # test with all provided\n    result = await hass.config_entries.flow.async_init(\n        DOMAIN,\n        context={"source": SOURCE_USER},\n        data={CONF_HOST: MOCK_HOST, CONF_PORT: MOCK_PORT},\n    )\n    assert result["type"] is FlowResultType.FORM\n    assert result["step_id"] == "link"\n\n\nasync def test_zeroconf(hass: HomeAssistant) -> None:\n    """Test zeroconf step."""\n    result = await hass.config_entries.flow.async_init(\n        DOMAIN,\n        context={"source": SOURCE_ZEROCONF},\n        data=MOCK_ZEROCONF_DATA,\n    )\n    assert result["type"] is FlowResultType.FORM\n    assert result["step_id"] == "link"\n\n\nasync def internal_test_link(hass: HomeAssistant) -> None:\n    """Test linking internal, common to both router modes."""\n    with patch(\n        "homeassistant.components.freebox.async_setup_entry",\n        return_value=True,\n    ) as mock_setup_entry:\n        result = await hass.config_entries.flow.async_init(\n            DOMAIN,\n            context={"source": SOURCE_USER},\n            data={CONF_HOST: MOCK_HOST, CONF_PORT: MOCK_PORT},\n        )\n\n        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})\n        assert result["type"] is FlowResultType.CREATE_ENTRY\n        assert result["result"].unique_id == MOCK_HOST\n        assert result["title"] == MOCK_HOST\n        assert result["data"][CONF_HOST] == MOCK_HOST\n        assert result["data"][CONF_PORT] == MOCK_PORT\n\n        assert len(mock_setup_entry.mock_calls) == 1\n\n\nasync def test_link(hass: HomeAssistant, router: Mock) -> None:\n    """Test link with standard router mode."""\n    await internal_test_link(hass)\n\n\nasync def test_link_bridge_mode(hass: HomeAssistant, router_bridge_mode: Mock) -> None:\n    """Test linking for a freebox in bridge mode."""\n    await internal_test_link(hass)\n\n\nasync def test_link_bridge_mode_error(\n    hass: HomeAssistant, mock_router_bridge_mode_error: Mock\n) -> None:\n    """Test linking for a freebox in bridge mode, unknown error received from API."""\n    result = await hass.config_entries.flow.async_init(\n        DOMAIN,\n        context={"source": SOURCE_USER},\n        data={CONF_HOST: MOCK_HOST, CONF_PORT: MOCK_PORT},\n    )\n    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})\n    assert result["type"] is FlowResultType.FORM\n    assert result["errors"] == {"base": "cannot_connect"}\n\n\nasync def test_abort_if_already_setup(hass: HomeAssistant) -> None:\n    """Test we abort if component is already setup."""\n    MockConfigEntry(\n        domain=DOMAIN,\n        data={CONF_HOST: MOCK_HOST, CONF_PORT: MOCK_PORT},\n        unique_id=MOCK_HOST,\n    ).add_to_hass(hass)\n\n    # Should fail, same MOCK_HOST (flow)\n    result = await hass.config_entries.flow.async_init(\n        DOMAIN,\n        context={"source": SOURCE_USER},\n        data={CONF_HOST: MOCK_HOST, CONF_PORT: MOCK_PORT},\n    )\n    assert result["type"] is FlowResultType.ABORT\n    assert result["reason"] == "already_configured"\n\n\nasync def test_on_link_failed(hass: HomeAssistant) -> None:\n    """Test when we have errors during linking the router."""\n    result = await hass.config_entries.flow.async_init(\n        DOMAIN,\n        context={"source": SOURCE_USER},\n        data={CONF_HOST: MOCK_HOST, CONF_PORT: MOCK_PORT},\n    )\n\n    with patch(\n        "homeassistant.components.freebox.router.Freepybox.open",\n        side_effect=AuthorizationError(),\n    ):\n        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})\n        assert result["type"] is FlowResultType.FORM\n        assert result["errors"] == {"base": "register_failed"}\n\n    with patch(\n        "homeassistant.components.freebox.router.Freepybox.open",\n        side_effect=HttpRequestError(),\n    ):\n        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})\n        assert result["type"] is FlowResultType.FORM\n        assert result["errors"] == {"base": "cannot_connect"}\n\n    with patch(\n        "homeassistant.components.freebox.router.Freepybox.open",\n        side_effect=InvalidTokenError(),\n    ):\n        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})\n        assert result["type"] is FlowResultType.FORM\n        assert result["errors"] == {"base": "unknown"}\n',
        }
