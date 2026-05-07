"""
Parameterized generator for GH623_dvcdbg_85.

Source PR:    https://github.com/p14c31355/dvcdbg/pull/85
Source Issue: N/A

Seed varies: renames 'addr' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH623_dvcdbg_85'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH623_dvcdbg_85'
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
                files[fpath] = files[fpath].replace('addr', 'addr' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH623_dvcdbg_85',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'p14c31355/dvcdbg',
                "pr_number": 85,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/p14c31355/dvcdbg/pull/85",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'src/scanner.rs': '//! Scanner utilities for I2C bus device discovery and analysis.\n//!\n//! This module provides functions to scan the I2C bus for connected devices,\n//! optionally testing with control bytes or initialization command sequences,\n//! with detailed logging support.\n\nuse crate::log;\nuse crate::logger::Logger;\nuse heapless::Vec;\n\npub const I2C_SCAN_ADDR_START: u8 = 0x03;\npub const I2C_SCAN_ADDR_END: u8 = 0x77;\n\n#[cfg(all(feature = "ehal_0_2", not(feature = "ehal_1_0")))]\npub mod ehal_0_2 {\n    use crate::define_scanner;\n\n    define_scanner!(\n        crate::compat::I2cCompat,\n        crate::logger::Logger\n    );\n}\n\n#[cfg(feature = "ehal_1_0")]\npub mod ehal_1_0 {\n    use crate::define_scanner;\n    \n    define_scanner!(\n        crate::compat::I2cCompat,\n        crate::logger::Logger\n    );\n}\n\n#[cfg(feature = "ehal_1_0")]\npub use self::ehal_1_0::{scan_i2c, scan_i2c_with_ctrl, scan_init_sequence};\n\n#[cfg(all(feature = "ehal_0_2", not(feature = "ehal_1_0")))]\npub use self::ehal_0_2::{scan_i2c, scan_i2c_with_ctrl, scan_init_sequence};\n\n#[macro_export]\nmacro_rules! define_scanner {\n    ($i2c_trait:path, $logger_trait:path) => {\n        use $crate::error::{ErrorKind, I2cError};\n        use $crate::compat::HalErrorExt;\n        use $crate::log;\n        use heapless::Vec;\n        /// Scan the I2C bus for connected devices (addresses `0x03` to `0x77`).\n        ///\n        /// This function probes each possible I2C device address by attempting to\n        /// write an empty buffer (`[]`). Devices that acknowledge are reported\n        /// through the provided logger.\n        ///\n        /// # Arguments\n        ///\n        /// * `i2c` - Mutable reference to an I2C interface implementing the `write` method.\n        /// * `logger` - Mutable reference to a logger implementing the [`Logger`] trait.\n        ///\n        /// # Example\n        ///\n        /// ```ignore\n        /// use embedded_hal::i2c::I2c;\n        /// use dvcdbg::logger::SerialLogger;\n        /// use dvcdbg::scanner::scan_i2c;\n        ///\n        /// let mut i2c = /* your i2c interface */;\n        /// let mut logger = SerialLogger::new(/* serial */);\n        ///\n        /// scan_i2c(&mut i2c, &mut logger);\n        /// ```\n        pub fn scan_i2c<I2C, L>(i2c: &mut I2C, logger: &mut L)\n        where\n            I2C: $i2c_trait,\n            L: $logger_trait,\n            <I2C as $i2c_trait>::Error: HalErrorExt,\n        {\n            log!(logger, "[scan] Scanning I2C bus...");\n            if let Ok(found_addrs) = internal_scan(i2c, logger, &[]) {\n                for addr in found_addrs {\n                    log!(logger, "[ok] Found device at 0x{:02X}", addr);\n                }\n            }\n            log!(logger, "[info] I2C scan complete.");\n        }\n\n        /// Scan the I2C bus for devices by sending specified control bytes.\n        ///\n        /// This variant allows specifying control bytes (e.g., `0x00`) to send\n        /// alongside the probe. Devices that acknowledge the transmission are\n        /// reported via the logger.\n        ///\n        /// # Arguments\n        ///\n        /// * `i2c` - Mutable reference to an I2C interface implementing the `write` method.\n        /// * `logger` - Mutable reference to a logger implementing the [`Logger`] trait.\n        /// * `control_bytes` - Slice of bytes to send when probing each device.\n        ///\n        /// # Example\n        ///\n        /// ```ignore\n        /// use embedded_hal::i2c::I2c;\n        /// use dvcdbg::logger::SerialLogger;\n        /// use dvcdbg::scanner::scan_i2c_with_ctrl;\n        ///\n        /// let mut i2c = /* your i2c interface */;\n        /// let mut logger = SerialLogger::new(/* serial */);\n        ///\n        /// scan_i2c_with_ctrl(&mut i2c, &mut logger, &[0x00]);\n        /// ```\n        pub fn scan_i2c_with_ctrl<I2C, L>(\n            i2c: &mut I2C,\n            logger: &mut L,\n            control_bytes: &[u8],\n        ) where\n            I2C: $i2c_trait,\n            L: $logger_trait,\n            <I2C as $i2c_trait>::Error: HalErrorExt,\n        {\n            log!(logger, "[scan] Scanning I2C bus with control bytes: {:?}", control_bytes);\n            if let Ok(found_addrs) = internal_scan(i2c, logger, control_bytes) {\n                for addr in found_addrs {\n                    log!(logger, "[ok] Found device at 0x{:02X}", addr);\n                }\n            }\n            log!(logger, "[info] I2C scan complete.");\n        }\n\n        /// Scan the I2C bus using an initialization sequence of commands.\n        ///\n        /// Each command in the sequence is transmitted to all possible device\n        /// addresses using the control byte `0x00`. The function records which\n        /// commands receive responses and highlights any **differences** between\n        /// the expected and observed responses.\n        ///\n        /// This is useful for verifying whether a device supports the expected\n        /// initialization commands (e.g., when testing display controllers).\n        ///\n        /// # Arguments\n        ///\n        /// * `i2c` - Mutable reference to an I2C interface implementing the `write` method.\n        /// * `logger` - Mutable reference to a logger implementing the [`Logger`] trait.\n        /// * `init_sequence` - Slice of initialization commands to test.\n        ///\n        /// # Example\n        ///\n        /// ```ignore\n        /// use embedded_hal::i2c::I2c;\n        /// use dvcdbg::logger::SerialLogger;\n        /// use dvcdbg::scanner::scan_init_sequence;\n        ///\n        /// let mut i2c = /* your i2c interface */;\n        /// let mut logger = SerialLogger::new(/* serial */);\n        ///\n        /// let init_sequence: [u8; 3] = [0xAE, 0xA1, 0xAF]; // example init cmds\n        /// scan_init_sequence(&mut i2c, &mut logger, &init_sequence);\n        /// ```\n        pub fn scan_init_sequence<I2C, L>(\n            i2c: &mut I2C,\n            logger: &mut L,\n            init_sequence: &[u8],\n        ) where\n            I2C: $i2c_trait,\n            L: $logger_trait,\n            <I2C as $i2c_trait>::Error: HalErrorExt,\n        {\n            log!(logger, "[scan] Scanning I2C bus with init sequence: {:02X?}", init_sequence);\n            let mut detected_cmds: Vec<u8, 64> = Vec::new();\n\n            for &cmd in init_sequence {\n                match internal_scan(i2c, logger, &[0x00, cmd]) {\n                    Ok(found_addrs) => {\n                        if !found_addrs.is_empty() {\n                            for addr in found_addrs {\n                                log!(logger, "[ok] Found device at 0x{:02X} responding to 0x{:02X}", addr, cmd);\n                            }\n                            if detected_cmds.push(cmd).is_err() {\n                                log!(logger, "[warn] Detected commands buffer is full, results may be incomplete!");\n                            }\n                        }\n                    }\n                    Err(e) => {\n                        log!(logger, "[error] scan failed for 0x{:02X}: {:?}", cmd, e);\n                    }\n                }\n            }\n\n            super::log_differences(logger, init_sequence, &detected_cmds);\n            log!(logger, "[info] I2C scan with init sequence complete.");\n        }\n\n        fn internal_scan<I2C, L>(\n            i2c: &mut I2C,\n            logger: &mut L,\n            data: &[u8],\n        ) -> Result<Vec<u8, 128>, ErrorKind>\n        where\n            I2C: $i2c_trait,\n            L: $logger_trait,\n            <I2C as $i2c_trait>::Error: HalErrorExt,\n        {\n            let mut found_devices: Vec<u8, 128> = Vec::new();\n\n            for addr in super::I2C_SCAN_ADDR_START..=super::I2C_SCAN_ADDR_END {\n                match i2c.write(addr, data) {\n                    Ok(_) => {\n                        let _ = found_devices.push(addr);\n                    }\n                    Err(e) => {\n                        let e_kind = e.to_compat(Some(addr));\n                        if e_kind == ErrorKind::I2c(I2cError::Nack) {\n                            continue;\n                        } else {\n                            log!(logger, "[error] write failed at 0x{:02X}: {:?}", addr, e_kind);\n                            return Err(e_kind);\n                        }\n                    }\n                }\n            }\n\n            Ok(found_devices)\n        }\n    }\n}\n\nfn log_differences<L>(logger: &mut L, expected: &[u8], detected: &Vec<u8, 64>)\nwhere\n    L: Logger,\n{\n    log!(logger, "Expected sequence: {:02X?}", expected);\n    log!(\n        logger,\n        "Commands with response: {:02X?}",\n        detected.as_slice()\n    );\n\n    let mut sorted = detected.clone();\n    sorted.sort_unstable();\n    let mut missing_cmds: Vec<u8, 64> = Vec::new();\n    for cmd in expected\n        .iter()\n        .copied()\n        .filter(|c| sorted.binary_search(c).is_err())\n    {\n        if missing_cmds.push(cmd).is_err() {\n            log!(\n                logger,\n                "[warn] Missing commands buffer is full, list is truncated."\n            );\n            break;\n        }\n    }\n    log!(\n        logger,\n        "Commands with no response: {:02X?}",\n        missing_cmds.as_slice()\n    );\n}\n',
        }
