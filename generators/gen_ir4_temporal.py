"""
Parameterized generator for IR4: Temporal Priority QA.

Each seed produces:
  - A domain (policy_portal, knowledge_base, regulatory_archive, product_docs)
  - 4-6 corpus documents, each with a date + status header
  - Temporal priority rules (most recent supersedes older on same topic)
  - "Founding documents" that are always authoritative regardless of date
  - "Draft" status docs that never supersede "approved" ones
  - Same-topic contradictions at different dates / different statuses
  - 6-10 questions requiring correct application of temporal + status priority
  - workspace/answer.json (blank template)
  - expected.json with correct answers keyed to priority-winning doc

TNI Pattern B (Hidden Spec Rules): The spec defines explicit temporal priority
rules. The brief vaguely says "answer questions using provided documents."
Agents must read the spec carefully to determine which document wins for each
topic, respecting:
  1. Founding docs always authoritative (regardless of date)
  2. Approved > Draft regardless of date
  3. Most recent approved doc supersedes older approved docs on same topic
"""
from __future__ import annotations

import json
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom, NamePool, PROJECT_NAMES

# ── Domain configurations ────────────────────────────────────────────────────

DOMAINS = [
    {
        "id": "policy_portal",
        "label": "Corporate Policy Portal",
        "org": "Arcturus Financial Group",
        "context": "internal policy management system",
        "topics": ["data_retention", "access_control", "expense_limits", "remote_work", "security_requirements"],
        "founding_topic": "data_retention",   # oldest founding doc – always wins
    },
    {
        "id": "knowledge_base",
        "label": "Engineering Knowledge Base",
        "org": "Stellar Systems Inc.",
        "context": "internal technical knowledge base",
        "topics": ["api_versioning", "deployment_process", "code_review", "incident_response", "on_call_rotation"],
        "founding_topic": "api_versioning",
    },
    {
        "id": "regulatory_archive",
        "label": "Regulatory Compliance Archive",
        "org": "Meridian Health Authority",
        "context": "regulatory document archive",
        "topics": ["data_privacy", "audit_frequency", "breach_notification", "vendor_approval", "retention_period"],
        "founding_topic": "data_privacy",
    },
    {
        "id": "product_docs",
        "label": "Product Documentation Hub",
        "org": "Nexus Software Ltd.",
        "context": "product documentation system",
        "topics": ["pricing_model", "feature_flags", "sla_targets", "support_tiers", "deprecation_policy"],
        "founding_topic": "pricing_model",
    },
]

# ── Fact pools per topic ──────────────────────────────────────────────────────

# Each entry: (label, unit, values_list)
# values_list has at least 3 entries so old/mid/new can differ
TOPIC_FACTS = {
    # policy_portal
    "data_retention": {
        "question_tpl": "What is the mandatory data retention period specified for {org}?",
        "unit": "years",
        "values": ["5 years", "7 years", "10 years"],
        "founding_override": True,    # founding doc rule applies to this topic
    },
    "access_control": {
        "question_tpl": "What authentication method is required for remote access at {org}?",
        "unit": "",
        "values": ["username/password", "multi-factor authentication (MFA)", "hardware token + MFA"],
        "founding_override": False,
    },
    "expense_limits": {
        "question_tpl": "What is the per-diem expense limit for business travel at {org}?",
        "unit": "USD/day",
        "values": ["$150/day", "$200/day", "$250/day"],
        "founding_override": False,
    },
    "remote_work": {
        "question_tpl": "How many days per week are employees permitted to work remotely at {org}?",
        "unit": "days/week",
        "values": ["1 day per week", "2 days per week", "3 days per week"],
        "founding_override": False,
    },
    "security_requirements": {
        "question_tpl": "What is the minimum password length required by {org} security policy?",
        "unit": "characters",
        "values": ["8 characters", "12 characters", "16 characters"],
        "founding_override": False,
    },
    # knowledge_base
    "api_versioning": {
        "question_tpl": "What API versioning scheme is mandated in the {org} engineering standards?",
        "unit": "",
        "values": ["date-based versioning (YYYY-MM-DD)", "semantic versioning (SemVer)", "URI path versioning (v1, v2)"],
        "founding_override": True,
    },
    "deployment_process": {
        "question_tpl": "How many approvals are required before a production deployment at {org}?",
        "unit": "approvals",
        "values": ["1 approval", "2 approvals", "3 approvals"],
        "founding_override": False,
    },
    "code_review": {
        "question_tpl": "What is the minimum number of reviewers required for a code review at {org}?",
        "unit": "reviewers",
        "values": ["1 reviewer", "2 reviewers", "3 reviewers"],
        "founding_override": False,
    },
    "incident_response": {
        "question_tpl": "What is the maximum response time for a P1 incident at {org}?",
        "unit": "minutes",
        "values": ["30 minutes", "15 minutes", "5 minutes"],
        "founding_override": False,
    },
    "on_call_rotation": {
        "question_tpl": "How long is each on-call rotation shift at {org}?",
        "unit": "",
        "values": ["1 week", "2 weeks", "3 days"],
        "founding_override": False,
    },
    # regulatory_archive
    "data_privacy": {
        "question_tpl": "What data privacy standard is {org} required to comply with?",
        "unit": "",
        "values": ["HIPAA", "HIPAA + GDPR", "HIPAA + GDPR + SOC 2"],
        "founding_override": True,
    },
    "audit_frequency": {
        "question_tpl": "How frequently must internal audits be conducted at {org}?",
        "unit": "",
        "values": ["annually", "semi-annually", "quarterly"],
        "founding_override": False,
    },
    "breach_notification": {
        "question_tpl": "Within how many hours must {org} notify regulators of a data breach?",
        "unit": "hours",
        "values": ["72 hours", "48 hours", "24 hours"],
        "founding_override": False,
    },
    "vendor_approval": {
        "question_tpl": "How many compliance checks are required before a new vendor is approved at {org}?",
        "unit": "checks",
        "values": ["2 checks", "3 checks", "5 checks"],
        "founding_override": False,
    },
    "retention_period": {
        "question_tpl": "What is the minimum record retention period mandated for {org}?",
        "unit": "years",
        "values": ["3 years", "5 years", "7 years"],
        "founding_override": False,
    },
    # product_docs
    "pricing_model": {
        "question_tpl": "What pricing model does {org} use for its standard tier?",
        "unit": "",
        "values": ["per-seat licensing", "usage-based billing", "flat-rate subscription"],
        "founding_override": True,
    },
    "feature_flags": {
        "question_tpl": "What system does {org} use to manage feature flags?",
        "unit": "",
        "values": ["LaunchDarkly", "Unleash", "ConfigCat"],
        "founding_override": False,
    },
    "sla_targets": {
        "question_tpl": "What is the uptime SLA target for the {org} production environment?",
        "unit": "",
        "values": ["99.5%", "99.9%", "99.95%"],
        "founding_override": False,
    },
    "support_tiers": {
        "question_tpl": "How many support tiers does {org} offer to customers?",
        "unit": "tiers",
        "values": ["2 tiers", "3 tiers", "4 tiers"],
        "founding_override": False,
    },
    "deprecation_policy": {
        "question_tpl": "What is the minimum notice period {org} must give before deprecating a feature?",
        "unit": "",
        "values": ["3 months", "6 months", "12 months"],
        "founding_override": False,
    },
}

# ── Date pools ────────────────────────────────────────────────────────────────

# Dates in ascending order — indices: 0=oldest, 1=mid-old, 2=mid, 3=recent, 4=newest
DATE_POOLS = [
    ["2019-03-15", "2020-11-01", "2022-06-20", "2023-09-10", "2024-07-01"],
    ["2018-07-22", "2020-04-30", "2021-12-05", "2023-02-14", "2024-11-20"],
    ["2020-01-10", "2021-08-17", "2022-10-25", "2023-11-30", "2025-01-08"],
    ["2019-05-03", "2021-03-28", "2022-07-14", "2024-01-19", "2025-03-22"],
    ["2017-09-01", "2019-06-15", "2021-04-11", "2023-05-07", "2024-08-31"],
]

ORG_SUFFIXES = ["Corporation", "Group", "Authority", "Ltd.", "Inc.", "Foundation"]


class Generator(TaskGenerator):
    task_id = "IR4_temporal"
    domain = "information_retrieval"
    difficulty = "hard"
    languages = ["json"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        names = NamePool(seed + 13, count=40)

        # ── Pick domain ──────────────────────────────────────────────────────
        domain_cfg = rng.choice(DOMAINS)
        org = domain_cfg["org"]
        label = domain_cfg["label"]
        context = domain_cfg["context"]
        all_topics = domain_cfg["topics"]
        founding_topic = domain_cfg["founding_topic"]

        # ── Pick date pool ───────────────────────────────────────────────────
        dates = rng.choice(DATE_POOLS)
        # dates[0] = oldest ... dates[4] = newest

        # ── Assign authors ───────────────────────────────────────────────────
        authors = [names.next() for _ in range(6)]

        # ── Decide doc count (4-6 docs, clamped to available topics) ────────
        n_docs = min(rng.randint(4, 6), len(all_topics))
        topics_used = rng.sample(all_topics, n_docs)
        # Ensure the founding topic is always included
        if founding_topic not in topics_used:
            topics_used[-1] = founding_topic

        # ── Build per-doc configuration ──────────────────────────────────────
        # Each doc covers one primary topic.
        # We create some same-topic conflicts across 2 docs for 2 topics.
        # Conflict setup: pick 2 topics that will have a "competing" doc.
        non_founding_topics = [t for t in topics_used if t != founding_topic]
        conflict_count = min(2, len(non_founding_topics))
        conflict_topics = rng.sample(non_founding_topics, conflict_count)

        # Build doc list: primary docs + conflict docs
        doc_configs = []

        # Primary docs — one per topic, spread across dates
        date_slots = list(range(n_docs))
        rng.shuffle(date_slots)
        for i, topic in enumerate(topics_used):
            date_idx = date_slots[i % len(date_slots)]
            fact_pool = TOPIC_FACTS[topic]
            # Primary doc: use value index matching date_idx (clamped)
            val_idx = min(date_idx, len(fact_pool["values"]) - 1)
            is_founding = (topic == founding_topic)
            doc_configs.append({
                "doc_id": f"doc_{chr(65 + i)}.txt",
                "topic": topic,
                "date": dates[date_idx],
                "date_idx": date_idx,
                "status": "approved",
                "is_founding": is_founding,
                "value": fact_pool["values"][val_idx],
                "author": authors[i % len(authors)],
            })

        # Conflict docs — draft version of a conflict topic with a "newer" date
        extra_docs_start = n_docs
        for j, topic in enumerate(conflict_topics):
            fact_pool = TOPIC_FACTS[topic]
            # Pick a NEWER date than the primary doc for this topic
            primary_date_idx = next(
                d["date_idx"] for d in doc_configs if d["topic"] == topic
            )
            # Draft doc gets a more recent date but is draft → must NOT supersede approved
            new_date_idx = min(primary_date_idx + 1 + j, len(dates) - 1)
            newer_val_idx = min(new_date_idx, len(fact_pool["values"]) - 1)

            # Ensure the draft value differs from the approved value
            approved_val = next(d["value"] for d in doc_configs if d["topic"] == topic)
            draft_val = fact_pool["values"][newer_val_idx]
            if draft_val == approved_val:
                draft_val = fact_pool["values"][(newer_val_idx + 1) % len(fact_pool["values"])]

            doc_configs.append({
                "doc_id": f"doc_{chr(65 + extra_docs_start + j)}.txt",
                "topic": topic,
                "date": dates[new_date_idx],
                "date_idx": new_date_idx,
                "status": "draft",
                "is_founding": False,
                "value": draft_val,         # the WRONG answer agents must reject
                "author": authors[(extra_docs_start + j) % len(authors)],
            })

        # ── Build corpus docs ────────────────────────────────────────────────
        corpus_files: dict[str, str] = {}
        for dc in doc_configs:
            content = self._gen_doc(org, label, dc)
            corpus_files[dc["doc_id"]] = content

        doc_list = sorted(corpus_files.keys())

        # ── Build answer key ─────────────────────────────────────────────────
        # For each topic, determine the winning doc based on priority rules:
        #   1. Founding doc always wins (regardless of date)
        #   2. Approved > Draft (regardless of date)
        #   3. Most recent approved wins over older approved
        winning_docs: dict[str, dict] = {}  # topic -> winning doc_config
        for topic in topics_used:
            candidates = [d for d in doc_configs if d["topic"] == topic]
            # Apply rules
            winner = self._resolve_winner(candidates)
            winning_docs[topic] = winner

        # ── Build questions (6-10) ───────────────────────────────────────────
        n_questions = rng.randint(6, 10)
        all_questions = self._build_questions(
            org, topics_used, winning_docs, doc_configs, conflict_topics,
            founding_topic, dates,
        )
        rng.shuffle(all_questions)
        questions = all_questions[:n_questions]
        # Re-number
        for i, q in enumerate(questions):
            q["id"] = f"Q{i+1}"

        # ── Workspace blank template ─────────────────────────────────────────
        blank_answers = {
            "questions": [
                {"id": q["id"], "question": q["question"], "answer": ""}
                for q in questions
            ]
        }
        workspace_files = {
            "answer.json": json.dumps(blank_answers, indent=2) + "\n",
        }

        # ── Expected (grader-only) ───────────────────────────────────────────
        expected = {
            "domain": domain_cfg["id"],
            "org": org,
            "label": label,
            "founding_topic": founding_topic,
            "conflict_topics": conflict_topics,
            "priority_rules": {
                "founding_docs_always_authoritative": True,
                "approved_over_draft_regardless_of_date": True,
                "most_recent_approved_supersedes_older_approved": True,
            },
            "doc_configs": [
                {
                    "doc_id": dc["doc_id"],
                    "topic": dc["topic"],
                    "date": dc["date"],
                    "status": dc["status"],
                    "is_founding": dc["is_founding"],
                    "value": dc["value"],
                }
                for dc in doc_configs
            ],
            "winning_docs": {
                topic: {
                    "doc_id": wd["doc_id"],
                    "value": wd["value"],
                    "status": wd["status"],
                    "is_founding": wd["is_founding"],
                }
                for topic, wd in winning_docs.items()
            },
            "questions": [
                {
                    "id": q["id"],
                    "question": q["question"],
                    "answer": q["answer"],
                    "answer_variants": q.get("answer_variants", [q["answer"]]),
                    "authoritative_doc": q["authoritative_doc"],
                    "topic": q["topic"],
                    "rule_tested": q.get("rule_tested", "temporal"),
                }
                for q in questions
            ],
            "doc_list": doc_list,
        }

        spec_md = self._generate_spec(
            org, label, context, domain_cfg, questions, doc_list,
            doc_configs, conflict_topics, founding_topic,
        )
        brief_md = self._generate_brief(org, label, context)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
            corpus_files=corpus_files,
        )

    # ── Priority resolution ──────────────────────────────────────────────────

    def _resolve_winner(self, candidates: list[dict]) -> dict:
        """Apply temporal + status + founding priority rules to select winner."""
        if not candidates:
            raise ValueError("No candidates to resolve")
        if len(candidates) == 1:
            return candidates[0]

        # Rule 1: founding doc always wins
        founding = [c for c in candidates if c["is_founding"]]
        if founding:
            # Among founding docs, pick most recent (though usually only one)
            return max(founding, key=lambda d: d["date"])

        # Rule 2: approved > draft regardless of date
        approved = [c for c in candidates if c["status"] == "approved"]
        if approved:
            # Rule 3: among approved, most recent wins
            return max(approved, key=lambda d: d["date"])

        # All are draft: most recent draft wins (edge case)
        return max(candidates, key=lambda d: d["date"])

    # ── Document generator ───────────────────────────────────────────────────

    def _gen_doc(self, org: str, label: str, dc: dict) -> str:
        topic = dc["topic"]
        fact = TOPIC_FACTS[topic]
        doc_id = dc["doc_id"]
        date = dc["date"]
        status = dc["status"].upper()
        is_founding = dc["is_founding"]
        value = dc["value"]
        author = dc["author"]

        topic_label = topic.replace("_", " ").title()

        founding_notice = ""
        if is_founding:
            founding_notice = (
                f"\nFOUNDING DOCUMENT NOTICE\n"
                f"This is a Founding Document for the {topic_label} policy area.\n"
                f"Per governance rules, Founding Documents are always authoritative\n"
                f"and are not superseded by later documents, regardless of date.\n"
            )

        draft_notice = ""
        if status == "DRAFT":
            draft_notice = (
                f"\nDRAFT NOTICE\n"
                f"This document has DRAFT status. It has NOT been formally approved.\n"
                f"DRAFT documents do NOT supersede APPROVED documents on the same topic,\n"
                f"regardless of date. Do not rely on this document for authoritative values.\n"
            )

        lines = [
            f"DOCUMENT: {doc_id}",
            f"Organization: {org}",
            f"Document Set: {label}",
            f"Topic: {topic_label}",
            f"Date: {date}",
            f"Status: {status}",
            f"Author: {author}",
            f"",
        ]

        if founding_notice:
            lines += founding_notice.strip().splitlines()
            lines.append("")

        if draft_notice:
            lines += draft_notice.strip().splitlines()
            lines.append("")

        lines += [
            f"POLICY / SPECIFICATION",
            f"",
            f"Topic: {topic_label}",
            f"Effective Date: {date}",
            f"",
            f"Current Value: {value}",
            f"",
        ]

        # Add topic-specific body text
        body = self._topic_body(topic, value, org, date, status)
        lines += body.splitlines()
        lines += [
            f"",
            f"Document ID: {doc_id}",
            f"Supersession Note: See governance rules for supersession precedence.",
        ]

        return "\n".join(lines) + "\n"

    def _topic_body(self, topic: str, value: str, org: str, date: str, status: str) -> str:
        """Generate realistic body text for a topic."""
        bodies = {
            "data_retention": (
                f"All records and data artifacts produced or received by {org} in the course of\n"
                f"business operations must be retained for a minimum of {value}.\n"
                f"This applies to financial records, communications, and system logs.\n"
                f"Records may be destroyed only after the retention period expires and\n"
                f"following written authorization from the Data Governance Officer."
            ),
            "access_control": (
                f"All remote access to {org} internal systems must use {value}.\n"
                f"This requirement applies to employees, contractors, and third-party vendors.\n"
                f"Access requests must be submitted through the IT helpdesk portal.\n"
                f"Violations are subject to immediate access revocation."
            ),
            "expense_limits": (
                f"Employees travelling on behalf of {org} are reimbursed at a per-diem rate\n"
                f"of {value} for meals and incidentals.\n"
                f"Receipts are required for all individual expenses exceeding $25.\n"
                f"Claims must be submitted within 30 days of travel completion."
            ),
            "remote_work": (
                f"Eligible employees at {org} may work remotely for up to {value}.\n"
                f"Remote work days must be agreed with the employee's direct manager.\n"
                f"Employees must remain reachable during core business hours (9am-3pm local).\n"
                f"This policy is subject to role eligibility criteria."
            ),
            "security_requirements": (
                f"All {org} system accounts must use passwords of at least {value}.\n"
                f"Passwords must include uppercase, lowercase, digits, and special characters.\n"
                f"Passwords must be rotated every 90 days.\n"
                f"Reuse of the last 12 passwords is prohibited."
            ),
            "api_versioning": (
                f"All APIs published by {org} engineering teams must follow {value}.\n"
                f"API changes must be documented in the changelog before release.\n"
                f"Breaking changes require a deprecation period of at least 6 months.\n"
                f"Internal APIs are exempt from the deprecation notice requirement."
            ),
            "deployment_process": (
                f"Production deployments at {org} require {value} from senior engineers.\n"
                f"Approvals must be recorded in the deployment tracking system.\n"
                f"Emergency deployments (P1 incidents) may proceed with post-hoc approval\n"
                f"documented within 2 hours of the deployment."
            ),
            "code_review": (
                f"All code changes merged to the main branch at {org} require review by\n"
                f"at least {value}.\n"
                f"Reviewers must not be the author of the change.\n"
                f"Review comments must be addressed or explicitly rejected before merge."
            ),
            "incident_response": (
                f"The {org} on-call team must acknowledge and begin responding to a P1\n"
                f"(critical) incident within {value} of the alert firing.\n"
                f"A post-mortem must be published within 5 business days of resolution.\n"
                f"Incident response status must be communicated to stakeholders every 30 minutes."
            ),
            "on_call_rotation": (
                f"The {org} engineering on-call rotation operates on a {value} cycle.\n"
                f"Each rotation must have a primary and a secondary on-call engineer.\n"
                f"Engineers must not be scheduled for on-call during the first 90 days of joining.\n"
                f"Compensation for on-call shifts is defined in the compensation policy."
            ),
            "data_privacy": (
                f"{org} is required to comply with {value} for all personal data processing.\n"
                f"A Data Protection Officer (DPO) must be appointed and registered.\n"
                f"Privacy impact assessments are mandatory for new data-processing initiatives.\n"
                f"All staff must complete annual data privacy training."
            ),
            "audit_frequency": (
                f"Internal compliance audits at {org} must be conducted {value}.\n"
                f"Audit findings must be reported to the Board of Directors within 30 days.\n"
                f"Critical findings require a remediation plan within 15 business days.\n"
                f"External audits are scheduled per regulatory requirements."
            ),
            "breach_notification": (
                f"In the event of a confirmed data breach, {org} must notify the relevant\n"
                f"regulatory authority within {value} of detection.\n"
                f"Affected individuals must be notified within 72 hours unless law enforcement\n"
                f"requests a delay. Notification records must be retained for 5 years."
            ),
            "vendor_approval": (
                f"Before engaging any new vendor, {org} must complete {value} covering\n"
                f"security posture, financial stability, and compliance certifications.\n"
                f"Vendor approvals expire after 2 years and require re-assessment.\n"
                f"The Procurement team maintains the approved vendor registry."
            ),
            "retention_period": (
                f"All regulated records at {org} must be retained for a minimum of {value}.\n"
                f"Electronic records must be stored in tamper-evident systems.\n"
                f"Destruction of records before the retention period requires written approval\n"
                f"from the Chief Compliance Officer."
            ),
            "pricing_model": (
                f"{org} standard tier products are sold using {value}.\n"
                f"Pricing is reviewed annually by the Finance and Product committees.\n"
                f"Custom pricing arrangements require VP-level approval.\n"
                f"All pricing changes must be communicated to customers 30 days in advance."
            ),
            "feature_flags": (
                f"All feature flag management at {org} is handled through {value}.\n"
                f"Flags must be reviewed and cleaned up within 30 days of full rollout.\n"
                f"Feature flags for billing-related features require Finance team approval.\n"
                f"Flag configurations are audited quarterly."
            ),
            "sla_targets": (
                f"The {org} production environment is committed to an uptime SLA of {value}.\n"
                f"SLA breaches must be disclosed in the monthly service report.\n"
                f"Planned maintenance windows do not count against SLA measurement.\n"
                f"Customer credits for SLA breaches are defined in the customer agreement."
            ),
            "support_tiers": (
                f"{org} offers {value} to customers, differentiated by response time and\n"
                f"access to dedicated support engineers.\n"
                f"Tier eligibility is based on contract value and product edition.\n"
                f"Support tier changes take effect at the next renewal date."
            ),
            "deprecation_policy": (
                f"{org} must provide at least {value} of advance notice before deprecating\n"
                f"any generally available feature or API endpoint.\n"
                f"Deprecation notices must be published in the changelog and emailed to\n"
                f"all affected customers. Migration guides must accompany all deprecation notices."
            ),
        }
        return bodies.get(topic, f"Value: {value}\nThis specification is effective as of {date}.")

    # ── Question bank ────────────────────────────────────────────────────────

    def _build_questions(
        self,
        org: str,
        topics_used: list[str],
        winning_docs: dict[str, dict],
        doc_configs: list[dict],
        conflict_topics: list[str],
        founding_topic: str,
        dates: list[str],
    ) -> list[dict]:
        questions = []
        qnum = 1

        for topic in topics_used:
            fact = TOPIC_FACTS[topic]
            winner = winning_docs[topic]
            winning_value = winner["value"]
            winning_doc = winner["doc_id"]
            is_founding = winner["is_founding"]

            q_text = fact["question_tpl"].format(org=org)

            # All values that appear for this topic (for distractor awareness)
            all_values_for_topic = [
                d["value"] for d in doc_configs if d["topic"] == topic
            ]
            variants = [winning_value] + [
                v for v in all_values_for_topic if v != winning_value
            ]
            # For grading, only winning_value is correct
            answer_variants = [winning_value]

            # Determine what rule is being tested
            if is_founding:
                rule_tested = "founding_doc_always_authoritative"
            elif topic in conflict_topics:
                # Could be draft-vs-approved or temporal
                winner_status = winner["status"]
                losers = [d for d in doc_configs if d["topic"] == topic and d["doc_id"] != winning_doc]
                loser_statuses = [d["status"] for d in losers]
                if "draft" in loser_statuses:
                    rule_tested = "approved_over_draft"
                else:
                    rule_tested = "temporal_most_recent"
            else:
                rule_tested = "temporal_most_recent"

            questions.append({
                "id": f"Q{qnum}",
                "topic": topic,
                "question": q_text,
                "answer": winning_value,
                "answer_variants": answer_variants,
                "authoritative_doc": winning_doc,
                "rule_tested": rule_tested,
            })
            qnum += 1

        # ── Extra meta questions ─────────────────────────────────────────────

        # Q: Which doc is authoritative for founding topic?
        founding_winner = winning_docs[founding_topic]
        questions.append({
            "id": f"Q{qnum}",
            "topic": founding_topic,
            "question": f"Which document is the authoritative source for the {founding_topic.replace('_', ' ')} specification at {org}?",
            "answer": founding_winner["doc_id"],
            "answer_variants": [founding_winner["doc_id"], founding_winner["doc_id"].replace(".txt", "")],
            "authoritative_doc": founding_winner["doc_id"],
            "rule_tested": "founding_doc_always_authoritative",
        })
        qnum += 1

        # Q: For each conflict topic, why should the draft doc NOT be used?
        for topic in conflict_topics:
            draft_docs = [d for d in doc_configs if d["topic"] == topic and d["status"] == "draft"]
            if draft_docs:
                draft_doc = draft_docs[0]
                approved_docs = [d for d in doc_configs if d["topic"] == topic and d["status"] == "approved"]
                if approved_docs:
                    approved_doc = approved_docs[0]
                    questions.append({
                        "id": f"Q{qnum}",
                        "topic": topic,
                        "question": (
                            f"For the {topic.replace('_', ' ')} specification at {org}, "
                            f"{draft_doc['doc_id']} is dated {draft_doc['date']} while "
                            f"{approved_doc['doc_id']} is dated {approved_doc['date']}. "
                            f"Which document is authoritative and why?"
                        ),
                        "answer": (
                            f"{approved_doc['doc_id']} is authoritative because it has APPROVED status. "
                            f"DRAFT documents do not supersede APPROVED documents regardless of date."
                        ),
                        "answer_variants": [
                            approved_doc["doc_id"],
                            "approved",
                            "APPROVED",
                            f"{approved_doc['doc_id']} is authoritative",
                        ],
                        "authoritative_doc": approved_doc["doc_id"],
                        "rule_tested": "approved_over_draft",
                    })
                    qnum += 1

        # Q: General rule question about draft status
        questions.append({
            "id": f"Q{qnum}",
            "topic": "meta",
            "question": (
                f"According to the temporal priority rules for {org} documents, "
                f"can a DRAFT document dated 2024 supersede an APPROVED document dated 2020 "
                f"on the same topic?"
            ),
            "answer": "No. DRAFT documents cannot supersede APPROVED documents regardless of date.",
            "answer_variants": [
                "No",
                "no",
                "cannot supersede",
                "DRAFT cannot supersede APPROVED",
                "approved takes precedence",
                "Draft documents do not supersede approved",
            ],
            "authoritative_doc": "spec",
            "rule_tested": "approved_over_draft",
        })
        qnum += 1

        # Q: General rule question about founding docs
        questions.append({
            "id": f"Q{qnum}",
            "topic": "meta",
            "question": (
                f"If a newer document dated 2025 contradicts a Founding Document dated 2018 "
                f"on the same topic, which document is authoritative at {org}?"
            ),
            "answer": "The Founding Document is authoritative. Founding Documents are always authoritative regardless of date.",
            "answer_variants": [
                "Founding Document",
                "founding document",
                "the founding document",
                "Founding Documents are always authoritative",
                "founding doc",
            ],
            "authoritative_doc": "spec",
            "rule_tested": "founding_doc_always_authoritative",
        })
        qnum += 1

        return questions

    # ── Spec / Brief ──────────────────────────────────────────────────────────

    def _generate_spec(
        self,
        org: str,
        label: str,
        context: str,
        domain_cfg: dict,
        questions: list[dict],
        doc_list: list[str],
        doc_configs: list[dict],
        conflict_topics: list[str],
        founding_topic: str,
    ) -> str:
        q_lines = "\n".join(
            f"{i+1}. [{q['id']}] {q['question']}"
            for i, q in enumerate(questions)
        )
        doc_lines = "\n".join(f"- `{d}`" for d in doc_list)

        # Build doc metadata table
        doc_table_rows = []
        for dc in sorted(doc_configs, key=lambda d: d["doc_id"]):
            founding_flag = " (**FOUNDING**)" if dc["is_founding"] else ""
            doc_table_rows.append(
                f"| `{dc['doc_id']}` | {dc['topic'].replace('_', ' ')} | {dc['date']} "
                f"| {dc['status'].upper()}{founding_flag} |"
            )
        doc_table = "\n".join(doc_table_rows)

        founding_topic_label = founding_topic.replace("_", " ")

        return f"""# IR4: Temporal Priority QA

## Goal
Answer all questions using ONLY the provided offline corpus. No internet access.
Multiple documents cover the same topic with different dates and statuses.
You must apply the **Temporal Priority Rules** below to determine which document
is authoritative for each topic.

## Organisation
{org} — {label} ({context})

## Questions
{q_lines}

## Hard Requirements

1. Produce `answer.json` with answers to ALL questions:
   ```json
   {{
     "questions": [
       {{"id": "Q1", "question": "...", "answer": "<string>"}},
       ...
     ]
   }}
   ```
2. Apply the **Temporal Priority Rules** strictly — do not simply use the most
   recently dated document without checking its status and founding classification.
3. Leave no answer field blank.
4. For meta-rule questions, explain the rule, not just the answer.

## Temporal Priority Rules

The following rules determine which document is authoritative when documents
on the same topic conflict:

### Rule 1 — Founding Documents Are Always Authoritative
Certain documents are classified as **Founding Documents** (marked in the
document header). Founding Documents are **always authoritative** for their
topic, regardless of the date of any other document. A newer document NEVER
supersedes a Founding Document.

### Rule 2 — Approved Status Beats Draft Status (Regardless of Date)
A document with status **APPROVED** is always authoritative over a document
with status **DRAFT**, even if the DRAFT document is more recent. Draft
documents represent work-in-progress and have NOT been formally ratified.

### Rule 3 — Most Recent Approved Document Supersedes Older Approved Documents
When two or more **APPROVED** (non-founding) documents cover the same topic,
the document with the **most recent date** is authoritative.

### Priority Order (highest to lowest)
1. Founding Document (any date, any topic it covers)
2. Most recent APPROVED document
3. Older APPROVED documents
4. DRAFT documents (never authoritative when an APPROVED doc exists)

## Document Metadata

| Document | Topic | Date | Status |
|----------|-------|------|--------|
{doc_table}

**Founding Document topic**: `{founding_topic_label}`

## Corpus
Located at `corpus/` (relative to workspace):
{doc_lines}

## Warning
Some documents are dated more recently but have DRAFT status — they must NOT
override APPROVED documents on the same topic. The Founding Document for
`{founding_topic_label}` is always authoritative for that topic regardless of
what other documents say. Read the status and founding classification in each
document header before answering.
"""

    def _generate_brief(self, org: str, label: str, context: str) -> str:
        return f"""# IR4: Temporal Priority QA (Brief)

Read all documents in the corpus and answer the questions in `answer.json`.

Organisation: {org}
Subject: {label}

The corpus is in `corpus/` (relative to workspace).
Documents include metadata headers with date and status information.
Fill in each answer field in `answer.json`.
"""
