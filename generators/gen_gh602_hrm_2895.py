"""
Parameterized generator for GH602_hrm_2895.

Source PR:    https://github.com/arii/hrm/pull/2895
Source Issue: https://github.com/arii/hrm/issues/2880

Seed varies: renames 'also' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH602_hrm_2895'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH602_hrm_2895'
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
                files[fpath] = files[fpath].replace('also', 'also' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH602_hrm_2895',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'arii/hrm',
                "pr_number": 2895,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/arii/hrm/pull/2895",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'components/HrTile.tsx': '// File: components/HrTile.tsx\n\'use client\'\nimport { HrTileProps } from \'@/types\'\nimport Box from \'@mui/material/Box\'\nimport CardContent from \'@mui/material/CardContent\'\nimport CircularProgress from \'@mui/material/CircularProgress\'\nimport Tooltip from \'@mui/material/Tooltip\'\nimport WifiOffIcon from \'@mui/icons-material/WifiOff\'\nimport { getHrZoneProps } from \'@/utils/visualization\'\nimport Typography from \'@mui/material/Typography\'\nimport { memo } from \'react\'\nimport StyledCard from \'./shared/StyledCard\'\nimport { useTheme } from \'@mui/material/styles\'\n\n// Define the style for the centered overlay\nconst overlayStyles = {\n  position: \'absolute\',\n  top: 0,\n  left: 0,\n  width: \'100%\',\n  height: \'100%\',\n  backgroundColor: \'rgba(0, 0, 0, 0.7)\', // Dark, semi-transparent overlay\n  display: \'flex\',\n  flexDirection: \'column\',\n  justifyContent: \'center\',\n  alignItems: \'center\',\n  zIndex: 10,\n  borderRadius: \'inherit\', // Match card border radius from StyledCard\n}\n\nconst HrTile = ({\n  name,\n  bpm,\n  percentMax,\n  calories = 0, // Default to 0 to prevent NaN\n  isConnected = true, // Default to connected\n  isAlerting = false,\n  alertMessage = \'Checking signal...\',\n}: HrTileProps) => {\n  const theme = useTheme()\n  const { backgroundColor, textColor } = getHrZoneProps(percentMax, 100)\n\n  const tooltipTitle = isAlerting\n    ? alertMessage\n    : !isConnected\n      ? \'Disconnected - Showing last known value\'\n      : `Name: ${name}, BPM: ${bpm}, Kcal: ${calories}, % Max HR: ${percentMax}%`\n\n  return (\n    <Tooltip title={tooltipTitle} arrow>\n      <StyledCard\n        data-testid="hr-tile-card"\n        role="region"\n        aria-label={`Heart rate monitor for ${name}: ${\n          isConnected ? `${bpm} beats per minute` : \'Disconnected\'\n        }, ${percentMax}% of maximum`}\n        sx={{\n          backgroundColor: backgroundColor,\n          color: textColor,\n          textAlign: \'center\',\n          minHeight: 180,\n          height: \'100%\',\n          display: \'flex\',\n          flexDirection: \'column\',\n          justifyContent: \'center\',\n          position: \'relative\',\n          opacity: isConnected ? 1 : 0.6,\n          transition: theme.transitions.create(\'opacity\', {\n            duration: theme.transitions.duration.short, // Approx 300ms\n          }),\n        }}\n      >\n        {/* --- Disconnected Icon --- */}\n        {!isConnected && (\n          <WifiOffIcon\n            sx={{\n              position: \'absolute\',\n              top: theme.spacing(1),\n              right: theme.spacing(1),\n              fontSize: \'1.5rem\',\n              color: theme.palette.warning.main,\n            }}\n          />\n        )}\n\n        {/* --- Alerting Overlay --- */}\n        {isAlerting && (\n          <Box sx={overlayStyles} data-testid="hr-tile-alert-overlay">\n            <CircularProgress size={30} sx={{ color: \'white\' }} />\n            <Typography\n              variant="caption"\n              sx={{ mt: 1, color: \'white\', textAlign: \'center\' }}\n            >\n              {alertMessage}\n            </Typography>\n          </Box>\n        )}\n\n        <Box aria-live="polite" aria-atomic="true">\n          <CardContent sx={{ p: 0 }}>\n            <Typography\n              data-testid="live-hr-percent"\n              sx={{\n                fontFamily: \'var(--font-roboto-mono), "Courier New", monospace\',\n                fontSize: { xs: \'5rem\', sm: \'6rem\', md: \'7rem\' },\n                fontWeight: 900,\n                lineHeight: 0.85,\n                my: 0.5,\n                animation: \'subtle-pulse 2s infinite ease-in-out\',\n                animationPlayState:\n                  bpm > 0 && !isAlerting && isConnected ? \'running\' : \'paused\',\n              }}\n            >\n              {percentMax}%\n            </Typography>\n            <Box\n              sx={{\n                display: \'flex\',\n                justifyContent: \'space-around\',\n                alignItems: \'center\',\n                mt: 1,\n              }}\n            >\n              {/* BPM Display */}\n              <Typography variant="h6" sx={{ fontWeight: 600 }}>\n                {bpm}{\' \'}\n                <Typography\n                  variant="caption"\n                  component="span"\n                  sx={{ opacity: 0.8 }}\n                >\n                  BPM\n                </Typography>\n              </Typography>\n\n              {/* Calorie Display */}\n              <Typography variant="h6" sx={{ fontWeight: 600 }}>\n                {Math.floor(calories)}{\' \'}\n                <Typography\n                  variant="caption"\n                  component="span"\n                  sx={{ opacity: 0.8 }}\n                >\n                  KCAL\n                </Typography>\n              </Typography>\n            </Box>\n            {name && !/^(user|new user)$/i.test(name) && (\n              <Typography\n                variant="subtitle1"\n                sx={{\n                  fontWeight: 700,\n                  fontSize: { xs: \'2rem\', sm: \'2.5rem\', md: \'3rem\' },\n                  letterSpacing: \'0.05em\',\n                  mt: 1,\n                  textOverflow: \'ellipsis\',\n                  whiteSpace: \'nowrap\',\n                  overflow: \'hidden\',\n                }}\n              >\n                {name}\n              </Typography>\n            )}\n          </CardContent>\n        </Box>\n      </StyledCard>\n    </Tooltip>\n  )\n}\n\n// Custom comparison function for React.memo\nconst arePropsEqual = (prevProps: HrTileProps, nextProps: HrTileProps) => {\n  return (\n    prevProps.name === nextProps.name &&\n    prevProps.bpm === nextProps.bpm &&\n    prevProps.percentMax === nextProps.percentMax &&\n    prevProps.calories === nextProps.calories &&\n    prevProps.isConnected === nextProps.isConnected &&\n    prevProps.isAlerting === nextProps.isAlerting &&\n    prevProps.alertMessage === nextProps.alertMessage\n  )\n}\n\nexport default memo(HrTile, arePropsEqual)\n',
            'tests/unit/components/HrTile.test.tsx': '/**\n * @jest-environment jsdom\n */\n// tests/unit/components/HrTile.test.tsx\nimport { jest } from \'@jest/globals\'\nimport HrTile from \'@/components/HrTile\'\nimport { render, screen } from \'@testing-library/react\'\nimport \'@testing-library/jest-dom\'\nimport { ZONE_COLORS } from \'@/utils/visualization\'\nimport theme from \'@/lib/theme\'\n\n// Mock the getHrZoneProps function to control the test cases\njest.mock(\'@/utils/visualization\', () => ({\n  ...jest.requireActual(\'@/utils/visualization\'),\n  getHrZoneProps: (percentMax: number) => {\n    let backgroundColor = ZONE_COLORS.grey\n    if (percentMax >= 90) {\n      backgroundColor = ZONE_COLORS.red\n    } else if (percentMax >= 80) {\n      backgroundColor = ZONE_COLORS.yellow\n    } else if (percentMax >= 70) {\n      backgroundColor = ZONE_COLORS.green\n    } else if (percentMax >= 60) {\n      backgroundColor = ZONE_COLORS.blue\n    }\n    const textColor = theme.palette.getContrastText(backgroundColor)\n    return {\n      backgroundColor,\n      textColor,\n      percentage: percentMax,\n    }\n  },\n}))\n\ndescribe(\'HrTile\', () => {\n  it(\'renders the correct background and text color for the Peak zone\', () => {\n    render(<HrTile name="Test" bpm={180} percentMax={95} />)\n    const card = screen.getByTestId(\'hr-tile-card\')\n    expect(card).toHaveStyle(`background-color: ${ZONE_COLORS.red}`)\n    expect(card).toHaveStyle(\n      `color: ${theme.palette.getContrastText(ZONE_COLORS.red)}`\n    )\n  })\n\n  it(\'renders the correct background and text color for the Cardio zone\', () => {\n    render(<HrTile name="Test" bpm={160} percentMax={85} />)\n    const card = screen.getByTestId(\'hr-tile-card\')\n    expect(card).toHaveStyle(`background-color: ${ZONE_COLORS.yellow}`)\n    expect(card).toHaveStyle(\n      `color: ${theme.palette.getContrastText(ZONE_COLORS.yellow)}`\n    )\n  })\n\n  it(\'renders the correct background and text color for the Fat Burn zone\', () => {\n    render(<HrTile name="Test" bpm={140} percentMax={75} />)\n    const card = screen.getByTestId(\'hr-tile-card\')\n    expect(card).toHaveStyle(`background-color: ${ZONE_COLORS.green}`)\n    expect(card).toHaveStyle(\n      `color: ${theme.palette.getContrastText(ZONE_COLORS.green)}`\n    )\n  })\n\n  it(\'renders the correct background and text color for the Warm-up zone\', () => {\n    render(<HrTile name="Test" bpm={120} percentMax={65} />)\n    const card = screen.getByTestId(\'hr-tile-card\')\n    expect(card).toHaveStyle(`background-color: ${ZONE_COLORS.blue}`)\n    expect(card).toHaveStyle(\n      `color: ${theme.palette.getContrastText(ZONE_COLORS.blue)}`\n    )\n  })\n\n  it(\'renders the correct background and text color for the low-intensity zone\', () => {\n    render(<HrTile name="Test" bpm={100} percentMax={55} />)\n    const card = screen.getByTestId(\'hr-tile-card\')\n    expect(card).toHaveStyle(`background-color: ${ZONE_COLORS.grey}`)\n    expect(card).toHaveStyle(\n      `color: ${theme.palette.getContrastText(ZONE_COLORS.grey)}`\n    )\n  })\n})\n',
            'tests/unit/utils/formatters.test.ts': "// File: tests/unit/utils/formatters.test.ts\nimport { formatDuration } from '@/utils/formatters'\n\ndescribe('formatDuration', () => {\n  it('should format milliseconds into MM:SS format', () => {\n    expect(formatDuration(60000)).toBe('1:00')\n    expect(formatDuration(90000)).toBe('1:30')\n    expect(formatDuration(125000)).toBe('2:05')\n    expect(formatDuration(0)).toBe('0:00')\n  })\n})\n",
            'utils/formatters.ts': "// File: utils/formatters.ts\n/**\n * Formats a duration in milliseconds to a MM:SS string.\n * @param ms The duration in milliseconds.\n * @returns A string in MM:SS format.\n */\nexport const formatDuration = (ms: number): string => {\n  const totalSeconds = Math.floor(ms / 1000)\n  const minutes = Math.floor(totalSeconds / 60)\n  const seconds = totalSeconds % 60\n  return `${minutes}:${seconds.toString().padStart(2, '0')}`\n}\n",
        }
