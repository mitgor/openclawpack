"""Markdown section extraction and file-specific parsers for .planning/ files."""

from __future__ import annotations

import json
import re

from openclawpack.state.models import (
    PhaseInfo,
    ProjectConfig,
    ProjectInfo,
    ProjectState,
    RequirementInfo,
    RoadmapInfo,
)


def extract_section(content: str, header: str, level: int = 2) -> str | None:
    """Extract markdown content under a heading.

    Args:
        content: Full markdown text.
        header: The heading text to find (e.g. "Current Position").
        level: The heading level (number of ``#`` characters).

    Returns:
        The text under that heading, or ``None`` if not found.
    """
    prefix = "#" * level
    # Match the target heading, capture everything until a same-or-higher-level heading or end
    pattern = (
        rf"^{re.escape(prefix)}\s+{re.escape(header)}\s*\n"
        rf"(.*?)"
        rf"(?=^#{{1,{level}}}\s|\Z)"
    )
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def parse_checkbox_items(section: str) -> list[tuple[bool, str]]:
    """Parse ``- [ ]`` and ``- [x]`` lines from a markdown section.

    Returns:
        List of ``(checked, text)`` tuples.
    """
    results: list[tuple[bool, str]] = []
    for match in re.finditer(r"^-\s+\[([ xX])\]\s+(.+)$", section, re.MULTILINE):
        checked = match.group(1).lower() == "x"
        text = match.group(2).strip()
        results.append((checked, text))
    return results


def parse_table_rows(section: str) -> list[dict[str, str]]:
    """Parse a markdown table into a list of dicts using the header row for keys.

    Handles standard GFM tables with ``|`` delimiters and a separator row.
    """
    lines = [line.strip() for line in section.strip().splitlines() if line.strip()]

    # Need at least header + separator + one data row
    if len(lines) < 3:
        return []

    # Find header row (first line with pipes)
    header_line = None
    header_idx = -1
    for i, line in enumerate(lines):
        if "|" in line:
            header_line = line
            header_idx = i
            break

    if header_line is None:
        return []

    headers = [h.strip() for h in header_line.strip("|").split("|")]

    # Skip separator row (header_idx + 1), process data rows
    rows: list[dict[str, str]] = []
    for line in lines[header_idx + 2 :]:
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        row = {}
        for j, header in enumerate(headers):
            row[header] = cells[j] if j < len(cells) else ""
        rows.append(row)

    return rows


# ---------------------------------------------------------------------------
# File-specific parsers
# ---------------------------------------------------------------------------


def parse_config_json(content: str) -> ProjectConfig:
    """Parse config.json content into a ProjectConfig model."""
    data = json.loads(content)
    return ProjectConfig.model_validate(data)


def parse_state_md(content: str) -> ProjectState:
    """Parse STATE.md content into a ProjectState model.

    Extracts current phase, plan counts, blockers, and decisions from
    the markdown structure maintained by GSD.
    """
    if not content or not content.strip():
        return ProjectState(
            current_phase=0,
            current_phase_name="unknown",
        )

    # --- Current Position section ---
    position = extract_section(content, "Current Position")

    current_phase = 0
    current_phase_name = "unknown"
    plans_complete = 0
    plans_total = 0
    last_activity = None

    if position:
        # "Phase: 1 of 5 (Foundation)"
        phase_match = re.search(
            r"Phase:\s*(\d+)\s+of\s+\d+\s*(?:\(([^)]+)\))?", position
        )
        if phase_match:
            current_phase = int(phase_match.group(1))
            current_phase_name = (phase_match.group(2) or "unknown").strip()

        # "Plan: 1 of 3 in current phase"
        plan_match = re.search(r"Plan:\s*(\d+)\s+of\s+(\d+)", position)
        if plan_match:
            plans_complete = int(plan_match.group(1))
            plans_total = int(plan_match.group(2))

        # "Last activity: 2026-02-21 -- Completed 01-01-PLAN.md"
        activity_match = re.search(r"Last activity:\s*(.+)", position)
        if activity_match:
            last_activity = activity_match.group(1).strip()

    # --- Blockers ---
    blockers: list[str] = []
    blockers_section = extract_section(content, "Blockers/Concerns", level=3)
    if blockers_section:
        for line in blockers_section.splitlines():
            line = line.strip()
            if line.startswith("- ") and line != "- None yet.":
                blockers.append(line[2:].strip())

    # --- Decisions ---
    decisions: list[str] = []
    decisions_section = extract_section(content, "Decisions", level=3)
    if decisions_section:
        for line in decisions_section.splitlines():
            line = line.strip()
            if line.startswith("- "):
                decisions.append(line[2:].strip())

    return ProjectState(
        current_phase=current_phase,
        current_phase_name=current_phase_name,
        plans_complete=plans_complete,
        plans_total=plans_total,
        last_activity=last_activity,
        blockers=blockers,
        decisions=decisions,
    )


def parse_roadmap_md(content: str) -> RoadmapInfo:
    """Parse ROADMAP.md content into a RoadmapInfo model.

    Extracts the overview paragraph, phase details (goals, requirements,
    plan counts, status), from the markdown structure.
    """
    if not content or not content.strip():
        return RoadmapInfo()

    # --- Overview ---
    overview = extract_section(content, "Overview")

    # --- Phase Details ---
    phases: list[PhaseInfo] = []
    phase_details = extract_section(content, "Phase Details")
    if phase_details:
        # Find each ### Phase N: Name heading
        phase_pattern = re.compile(
            r"^###\s+Phase\s+(\d+):\s+([^\n]+)\n(.*?)(?=^###\s|\Z)",
            re.MULTILINE | re.DOTALL,
        )
        for match in phase_pattern.finditer(phase_details):
            number = int(match.group(1))
            name = match.group(2).strip()
            body = match.group(3)

            goal = None
            goal_match = re.search(r"\*\*Goal\*\*:\s*(.+)", body)
            if goal_match:
                goal = goal_match.group(1).strip()

            requirements: list[str] = []
            req_match = re.search(r"\*\*Requirements\*\*:\s*(.+)", body)
            if req_match:
                requirements = [
                    r.strip() for r in req_match.group(1).split(",") if r.strip()
                ]

            # Parse plan count from "**Plans**: N plans" or progress table
            plans_total = 0
            plans_complete = 0

            # Count plan list items (lines starting with "- [ ]" or "- [x]")
            plan_items = parse_checkbox_items(body)
            if plan_items:
                plans_total = len(plan_items)
                plans_complete = sum(1 for checked, _ in plan_items if checked)

            # Determine status from progress table or infer
            status = "Not started"
            if plans_complete > 0 and plans_complete >= plans_total:
                status = "Complete"
            elif plans_complete > 0:
                status = "In Progress"

            phases.append(
                PhaseInfo(
                    number=number,
                    name=name,
                    goal=goal,
                    requirements=requirements,
                    plans_complete=plans_complete,
                    plans_total=plans_total,
                    status=status,
                )
            )

    # --- Progress table (overrides inferred status with explicit values) ---
    progress_section = extract_section(content, "Progress")
    if progress_section:
        rows = parse_table_rows(progress_section)
        for row in rows:
            # Match phase by extracting number from "1. Foundation" format
            phase_col = row.get("Phase", "")
            num_match = re.match(r"(\d+)\.", phase_col)
            if num_match:
                phase_num = int(num_match.group(1))
                for phase in phases:
                    if phase.number == phase_num:
                        # Parse "1/3" format from "Plans Complete" column
                        plans_str = row.get("Plans Complete", "")
                        pc_match = re.match(r"(\d+)/(\d+)", plans_str)
                        if pc_match:
                            phase.plans_complete = int(pc_match.group(1))
                            phase.plans_total = int(pc_match.group(2))
                        status_val = row.get("Status", "").strip()
                        if status_val and status_val != "-":
                            phase.status = status_val
                        completed_val = row.get("Completed", "").strip()
                        if completed_val and completed_val != "-":
                            phase.completed_date = completed_val

    return RoadmapInfo(phases=phases, overview=overview)


def parse_requirements_md(content: str) -> list[RequirementInfo]:
    """Parse REQUIREMENTS.md content into a list of RequirementInfo models.

    Extracts checkbox items with bold requirement IDs, and cross-references
    the traceability table for phase assignments.
    """
    if not content or not content.strip():
        return []

    requirements: list[RequirementInfo] = []

    # Build phase lookup from traceability table
    phase_map: dict[str, int | None] = {}
    traceability = extract_section(content, "Traceability")
    if traceability:
        rows = parse_table_rows(traceability)
        for row in rows:
            req_id = row.get("Requirement", "").strip()
            phase_str = row.get("Phase", "").strip()
            phase_num = None
            p_match = re.search(r"(\d+)", phase_str)
            if p_match:
                phase_num = int(p_match.group(1))
            phase_map[req_id] = phase_num

    # Parse v1 requirements section for checkbox items with bold IDs
    v1_section = extract_section(content, "v1 Requirements")
    if v1_section:
        # Match: - [ ] **REQ-ID**: Description  or  - [x] **REQ-ID**: Description
        req_pattern = re.compile(
            r"^-\s+\[([ xX])\]\s+\*\*([A-Z]+-\d+)\*\*:\s*(.+)$", re.MULTILINE
        )
        for match in req_pattern.finditer(v1_section):
            checked = match.group(1).lower() == "x"
            req_id = match.group(2)
            description = match.group(3).strip()
            phase_num = phase_map.get(req_id)

            requirements.append(
                RequirementInfo(
                    id=req_id,
                    description=description,
                    phase=phase_num,
                    completed=checked,
                )
            )

    return requirements


def parse_project_md(content: str) -> ProjectInfo:
    """Parse PROJECT.md content into a ProjectInfo model.

    Extracts the project name from H1, description from "What This Is",
    core value, and constraints.
    """
    if not content or not content.strip():
        return ProjectInfo(name="unknown", description="unknown")

    # --- Name from H1 ---
    name = "unknown"
    h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if h1_match:
        name = h1_match.group(1).strip()

    # --- Description from "What This Is" ---
    description = "unknown"
    what_section = extract_section(content, "What This Is")
    if what_section:
        description = what_section.strip()

    # --- Core Value ---
    core_value = None
    cv_section = extract_section(content, "Core Value")
    if cv_section:
        core_value = cv_section.strip()

    # --- Constraints ---
    constraints: list[str] = []
    constraints_section = extract_section(content, "Constraints")
    if constraints_section:
        for line in constraints_section.splitlines():
            line = line.strip()
            if line.startswith("- **"):
                # Extract text after closing **: e.g. "- **Runtime**: Python 3.10+"
                c_match = re.match(r"-\s+\*\*[^*]+\*\*:\s*(.+)", line)
                if c_match:
                    constraints.append(c_match.group(1).strip())
                else:
                    constraints.append(line[2:].strip())
            elif line.startswith("- "):
                constraints.append(line[2:].strip())

    return ProjectInfo(
        name=name,
        description=description,
        core_value=core_value,
        constraints=constraints,
    )
