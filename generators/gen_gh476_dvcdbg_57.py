"""
Parameterized generator for GH476_dvcdbg_57.

Source PR:    https://github.com/p14c31355/dvcdbg/pull/57
Source Issue: N/A

Seed varies: renames 'absorption' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH476_dvcdbg_57'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH476_dvcdbg_57'
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
                files[fpath] = files[fpath].replace('absorption', 'absorption' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH476_dvcdbg_57',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'p14c31355/dvcdbg',
                "pr_number": 57,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/p14c31355/dvcdbg/pull/57",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'src/lib.rs': '#![no_std]\n\n//! # dvcdbg\n//!\n//! Lightweight logging and diagnostic utilities for embedded Rust.\n//! Compatible with `no_std` and multiple HAL backends.\n\n#[cfg(feature = "logger")]\npub mod logger;\n\n#[cfg(feature = "scanner")]\npub mod scanner;\n\n#[cfg(feature = "macros")]\n#[macro_use]\npub mod macros;\n\n/// Prelude module for easy import of commonly used types and macros.\n///\n/// Users can simply:\n/// ```rust\n/// use dvcdbg::prelude::*;\n/// ```\npub mod prelude;\n',
            'src/macros.rs': '//! # dvcdbg Macros\n//!\n//! This module contains a collection of useful macros for embedded environments.\n//! - Convert UART/Serial type to `core::fmt::Write`\n//! - Hexadecimal representation of byte sequence\n//! - I2C scan\n//! - Debugging assistance (assert, delayed loop, cycle measurement)\n//!\n\n/// Macro to adapt a serial peripheral into a fmt::Write + embedded_io::Write bridge.\n///\n/// # Arguments\n/// - \'$name\' -> Name of the generated structure\n/// - \'nb_write\' -> Serial write function name required by HAL\n/// - \'flush(optional)\' -> Function for non-blocking transmission of one byte at a time using the nb crate function\n///\n/// # Example\n///\n/// ## Using Arduino HAL Serial\n/// ```ignore\n/// use arduino_hal::prelude::*;\n/// use dvcdbg::adapt_serial;\n/// use core::fmt::Write;\n///\n/// // Wrap the built-in serial\n/// adapt_serial!(UsartAdapter, nb_write = write, flush = flush);\n///\n/// let dp = arduino_hal::Peripherals::take().unwrap();\n/// let pins = arduino_hal::pins!(dp);\n/// let serial = arduino_hal::default_serial!(dp, pins, 57600);\n/// let mut dbg_uart = UsartAdapter(serial);\n///\n/// writeln!(dbg_uart, "Hello from embedded-io bridge!").unwrap();\n/// embedded_io::Write::write_all(&mut dbg_uart, &[0x01, 0x02, 0x03]).unwrap();\n/// ```\n///\n/// ## Using a custom serial-like type\n/// ```ignore\n/// use dvcdbg::adapt_serial;\n/// use core::convert::Infallible;\n/// use core::fmt::Write;\n/// use nb;\n///\n/// // Define a simple serial-like type\n/// struct MySerial;\n///\n/// impl nb::serial::Write<u8> for MySerial {\n///     type Error = Infallible;\n///\n///     fn write(&mut self, _byte: u8) -> nb::Result<(), Self::Error> {\n///         Ok(())\n///     }\n///\n///     fn flush(&mut self) -> nb::Result<(), Self::Error> {\n///         Ok(())\n///     }\n/// }\n///\n/// // Adapt it with the macro\n/// adapt_serial!(MyAdapter, nb_write = write, flush = flush);\n///\n/// let mut uart = MyAdapter(MySerial);\n/// writeln!(uart, "Hello via custom serial").unwrap();\n/// embedded_io::Write::write_all(&mut uart, &[0xAA, 0xBB]).unwrap();\n/// ```\n#[macro_export]\nmacro_rules! adapt_serial {\n    // nb_write variant\n    ($name:ident, nb_write = $write_fn:ident $(, flush = $flush_fn:ident)?) => {\n        /// Serial adapter wrapper\n        pub struct $name<T>(pub T);\n\n        /// Implement embedded-io Write for the wrapper\n        impl<T> embedded_io::Write for $name<T>\n        where\n            T: nb::serial::Write<u8, Error = core::convert::Infallible>,\n        {\n            type Error = core::convert::Infallible;\n\n            fn write(&mut self, buf: &[u8]) -> Result<usize, Self::Error> {\n                for &b in buf {\n                    nb::block!(self.0.$write_fn(b))?;\n                }\n                Ok(buf.len())\n            }\n\n            fn flush(&mut self) -> Result<(), Self::Error> {\n                $(\n                    nb::block!(self.0.$flush_fn())?;\n                )?\n                Ok(())\n            }\n        }\n\n        /// Implement core::fmt::Write for use with writeln! / write!\n        impl<T> core::fmt::Write for $name<T>\n        where\n            T: nb::serial::Write<u8, Error = core::convert::Infallible>,\n        {\n            fn write_str(&mut self, s: &str) -> core::fmt::Result {\n                <Self as embedded_io::Write>::write_all(self, s.as_bytes())\n                    .map_err(|_| core::fmt::Error)\n            }\n        }\n    }\n}\n\n/// Writes a byte slice in hexadecimal format to a `fmt::Write` target.\n///\n/// # Example\n/// ```ignore\n/// let buf = [0x12, 0xAB, 0xFF];\n/// write_hex!(logger, &buf);\n/// ```\n#[macro_export]\nmacro_rules! write_hex {\n    ($dst:expr, $data:expr) => {\n        for &b in $data {\n            let _ = core::write!($dst, "{:02X} ", b);\n        }\n    };\n}\n\n/// Writes a byte slice in binary format to a `fmt::Write` target.\n///\n/// Each byte is printed as an 8-bit binary number followed by a space.\n///\n/// # Arguments\n/// - `$dst`: Destination implementing `core::fmt::Write`\n/// - `$data`: Slice of bytes to print\n///\n/// # Example\n/// ```ignore\n/// let buf = [0b10101010, 0b11110000];\n/// write_bin!(logger, &buf);\n/// // Output: "10101010 11110000 "\n/// ```\n#[macro_export]\nmacro_rules! write_bin {\n    ($dst:expr, $data:expr) => {\n        for &b in $data {\n            let _ = core::write!($dst, "{:08b} ", b);\n        }\n    };\n}\n\n/// Measures execution cycles (or timestamps) for an expression using a timer.\n///\n/// # Example\n/// ```ignore\n/// let (result, elapsed) = measure_cycles!(my_func(), timer);\n/// ```\n#[macro_export]\nmacro_rules! measure_cycles {\n    ($expr:expr, $timer:expr) => {{\n        let start = $timer.now();\n        let result = $expr;\n        let elapsed = $timer.now().wrapping_sub(start);\n        (result, elapsed)\n    }};\n}\n\n/// Runs a loop with a fixed delay between iterations.\n///\n/// # Example\n/// ```ignore\n/// loop_with_delay!(delay, 100, { blink_led(); });\n/// ```\n#[macro_export]\nmacro_rules! loop_with_delay {\n    ($delay:expr, $delay_ms:expr, $body:block) => {\n        loop {\n            $body\n            $delay.delay_ms($delay_ms);\n        }\n    };\n}\n\n/// Logs a simple assertion failure to a logger without panicking.\n///\n/// # Example\n/// ```ignore\n/// assert_log!(x == 42, logger, "Unexpected value: {}", x);\n/// ```\n#[macro_export]\nmacro_rules! assert_log {\n    ($cond:expr, $logger:expr, $($arg:tt)*) => {\n        if !$cond {\n            let _ = core::write!($logger, "ASSERT FAILED: ");\n            let _ = core::writeln!($logger, $($arg)*);\n        }\n    };\n}\n\n/// Scans I2C bus for devices and logs found addresses.\n///\n/// # Example\n/// ```ignore\n/// scan_i2c!(i2c, logger);\n/// ```\n#[macro_export]\nmacro_rules! scan_i2c {\n    ($i2c:expr, $logger:expr) => {{\n        $crate::scanner::scan_i2c($i2c, $logger);\n    }};\n}\n\n/// Quick diagnostic workflow for a new board.\n///\n/// Automatically performs:\n/// 1. Serial logger check\n/// 2. I2C bus scan\n/// 3. Optional cycle measurement of a test expression\n///\n/// # Arguments\n/// - `$serial`: Serial logger implementing `core::fmt::Write`\n/// - `$i2c`: I2C bus instance\n/// - `$timer`: Timer implementing `.now()`\n/// - `$test_expr`: Optional expression to measure cycles for (can be `{}` block)\n///\n/// # Example\n/// ```ignore\n/// quick_diag!(logger, i2c, timer, { my_func(); });\n/// ```\n#[macro_export]\nmacro_rules! quick_diag {\n    ($serial:expr, $i2c:expr, $timer:expr, $test_expr:block) => {{\n        quick_diag!(@inner $serial, $i2c);\n\n        // Test expression timing\n        let (_result, cycles) = $crate::measure_cycles!($test_expr, $timer);\n        let _ = core::writeln!($serial, "Test expression cycles: {}", cycles);\n\n        let _ = core::writeln!($serial, "=== Quick Diagnostic Complete ===");\n    }};\n    ($serial:expr, $i2c:expr) => {{\n        quick_diag!(@inner $serial, $i2c);\n        let _ = core::writeln!($serial, "=== Quick Diagnostic Complete ===");\n    }};\n    // Internal rule for common diagnostic steps.\n    (@inner $serial:expr, $i2c:expr) => {\n        let _ = core::writeln!($serial, "=== Quick Diagnostic Start ===");\n        // I2C bus scan\n        let _ = core::writeln!($serial, "Scanning I2C bus...");\n        $crate::scan_i2c!($i2c, $serial);\n    };\n}\n',
        }
