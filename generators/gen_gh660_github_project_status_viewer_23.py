"""
Parameterized generator for GH660_github-project-status-viewer_23.

Source PR:    https://github.com/kubrickcode/github-project-status-viewer/pull/23
Source Issue: https://github.com/kubrickcode/github-project-status-viewer/issues/18

Seed varies: renames 'badge' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH660_github-project-status-viewer_23'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH660_github-project-status-viewer_23'
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
                files[fpath] = files[fpath].replace('badge', 'badge' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH660_github-project-status-viewer_23',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'kubrickcode/github-project-status-viewer',
                "pr_number": 23,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/kubrickcode/github-project-status-viewer/pull/23",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'extension/public/manifest.json': '{\n  "manifest_version": 3,\n  "name": "GitHub Project Status Viewer",\n  "version": "2.0.0",\n  "description": "Display GitHub Projects status in issue lists",\n  "permissions": [\n    "identity",\n    "storage"\n  ],\n  "host_permissions": [\n    "https://api.github.com/*",\n    "https://github.com/*",\n    "https://github-project-status-viewer.vercel.app/*"\n  ],\n  "action": {\n    "default_popup": "popup.html",\n    "default_icon": {\n      "16": "logo.png",\n      "48": "logo.png",\n      "128": "logo.png"\n    }\n  },\n  "icons": {\n    "16": "logo.png",\n    "48": "logo.png",\n    "128": "logo.png"\n  },\n  "content_scripts": [\n    {\n      "matches": ["https://github.com/*/*/issues*"],\n      "js": ["content.js"],\n      "css": ["styles.css"],\n      "run_at": "document_end"\n    }\n  ],\n  "background": {\n    "service_worker": "background.js"\n  }\n}\n',
            'extension/src/content.ts': '(() => {\n  type IssueStatus = {\n    color: string | null;\n    number: number;\n    status: string | null;\n  };\n\n  type MessageRequest = {\n    issueNumbers: number[];\n    owner: string;\n    repo: string;\n    type: "GET_PROJECT_STATUS";\n  };\n\n  type MessageResponse = {\n    error?: string;\n    statuses?: IssueStatus[];\n  };\n\n  const GITHUB_ISSUES_URL_PATTERN =\n    /https:\\/\\/github\\.com\\/[^/]+\\/[^/]+\\/issues/;\n  const BADGE_CLASS = "project-status-badge";\n  const DEFAULT_BADGE_COLOR = "#6e7781";\n\n  const getIssueNumbers = (): number[] => {\n    const issueElements = document.querySelectorAll(\n      \'[data-testid="issue-pr-title-link"]\'\n    );\n\n    const numbers: number[] = [];\n\n    issueElements.forEach((element) => {\n      const href = element.getAttribute("href");\n      if (href) {\n        const match = href.match(/\\/issues\\/(\\d+)/);\n        if (match) {\n          const issueNumber = parseInt(match[1], 10);\n          numbers.push(issueNumber);\n        }\n      }\n    });\n\n    return numbers;\n  };\n\n  const calculateMaxBadgeWidth = (): number => {\n    const badges = document.querySelectorAll(`.${BADGE_CLASS}`);\n    if (badges.length === 0) return 0;\n\n    let maxWidth = 0;\n    badges.forEach((badge) => {\n      const width = (badge as HTMLElement).getBoundingClientRect().width;\n      if (width > maxWidth) {\n        maxWidth = width;\n      }\n    });\n\n    return maxWidth;\n  };\n\n  const updateBadgeWidths = () => {\n    const maxWidth = calculateMaxBadgeWidth();\n    if (maxWidth === 0) return;\n\n    const badges = document.querySelectorAll(`.${BADGE_CLASS}`);\n    badges.forEach((badge) => {\n      (badge as HTMLElement).style.minWidth = `${maxWidth}px`;\n    });\n  };\n\n  const addStatusBadge = (\n    issueNumber: number,\n    status: string,\n    color: string | null\n  ) => {\n    const issueLinks = document.querySelectorAll(\n      \'[data-testid="issue-pr-title-link"]\'\n    );\n\n    for (const link of Array.from(issueLinks)) {\n      const href = link.getAttribute("href");\n      if (!href?.includes(`/issues/${issueNumber}`)) continue;\n\n      const h3Element = link.closest("h3");\n      if (!h3Element) continue;\n\n      const container = h3Element.parentElement;\n      if (!container) continue;\n\n      if (container.querySelector(`.${BADGE_CLASS}`)) return;\n\n      const badge = document.createElement("span");\n      badge.className = BADGE_CLASS;\n      badge.textContent = status;\n      badge.style.setProperty("--status-color", color || DEFAULT_BADGE_COLOR);\n\n      container.insertBefore(badge, h3Element);\n      return;\n    }\n  };\n\n  const parseRepoInfo = () => {\n    const match = window.location.pathname.match(/^\\/([^/]+)\\/([^/]+)\\/issues/);\n    if (!match) return null;\n\n    return {\n      owner: match[1],\n      repo: match[2],\n    };\n  };\n\n  const updateIssueStatuses = async () => {\n    const repoInfo = parseRepoInfo();\n    if (!repoInfo) return;\n\n    const issueNumbers = getIssueNumbers();\n    if (issueNumbers.length === 0) return;\n\n    try {\n      const request: MessageRequest = {\n        issueNumbers,\n        owner: repoInfo.owner,\n        repo: repoInfo.repo,\n        type: "GET_PROJECT_STATUS",\n      };\n\n      const response: MessageResponse = await chrome.runtime.sendMessage(\n        request\n      );\n\n      if (response.error) return;\n\n      const statuses = response.statuses || [];\n\n      statuses.forEach(({ color, number, status }) => {\n        if (status) {\n          addStatusBadge(number, status, color);\n        }\n      });\n\n      requestAnimationFrame(() => {\n        updateBadgeWidths();\n      });\n    } catch (error) {\n      // Silent fail\n    }\n  };\n\n  const init = () => {\n    if (!window.location.href.match(GITHUB_ISSUES_URL_PATTERN)) return;\n\n    updateIssueStatuses();\n\n    const observer = new MutationObserver(() => {\n      updateIssueStatuses();\n    });\n\n    observer.observe(document.body, {\n      childList: true,\n      subtree: true,\n    });\n  };\n\n  init();\n})();\n',
        }
