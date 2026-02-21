"""Tests for markdown parsers in openclawpack.state.parser."""

from pathlib import Path

from openclawpack.state.parser import (
    extract_section,
    parse_checkbox_items,
    parse_config_json,
    parse_project_md,
    parse_requirements_md,
    parse_roadmap_md,
    parse_state_md,
    parse_table_rows,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_MD = """\
# Top Level

Some intro text.

## Section One

Content of section one.

More content here.

## Section Two

Content of section two.

### Subsection

Nested content.

## Section Three

Final section.
"""

SAMPLE_TABLE = """\
| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 1/3 | In Progress | - |
| 2. Core Commands | 0/3 | Not started | - |
"""

SAMPLE_CHECKBOXES = """\
- [x] **PKG-01**: First item completed
- [ ] **PKG-02**: Second item pending
- [X] **PKG-03**: Third item completed (uppercase X)
- [ ] **PKG-04**: Fourth item pending
"""


# ---------------------------------------------------------------------------
# extract_section tests
# ---------------------------------------------------------------------------


class TestExtractSection:
    def test_known_header(self):
        result = extract_section(SAMPLE_MD, "Section One")
        assert result is not None
        assert "Content of section one." in result
        assert "More content here." in result

    def test_missing_header(self):
        result = extract_section(SAMPLE_MD, "Nonexistent")
        assert result is None

    def test_last_section(self):
        result = extract_section(SAMPLE_MD, "Section Three")
        assert result is not None
        assert "Final section." in result

    def test_nested_header_level3(self):
        result = extract_section(SAMPLE_MD, "Subsection", level=3)
        assert result is not None
        assert "Nested content." in result

    def test_does_not_bleed_into_next_section(self):
        result = extract_section(SAMPLE_MD, "Section One")
        assert result is not None
        assert "Content of section two." not in result


# ---------------------------------------------------------------------------
# parse_checkbox_items tests
# ---------------------------------------------------------------------------


class TestParseCheckboxItems:
    def test_mixed_items(self):
        items = parse_checkbox_items(SAMPLE_CHECKBOXES)
        assert len(items) == 4
        assert items[0] == (True, "**PKG-01**: First item completed")
        assert items[1] == (False, "**PKG-02**: Second item pending")
        assert items[2] == (True, "**PKG-03**: Third item completed (uppercase X)")
        assert items[3] == (False, "**PKG-04**: Fourth item pending")

    def test_empty_input(self):
        items = parse_checkbox_items("")
        assert items == []


# ---------------------------------------------------------------------------
# parse_table_rows tests
# ---------------------------------------------------------------------------


class TestParseTableRows:
    def test_simple_table(self):
        rows = parse_table_rows(SAMPLE_TABLE)
        assert len(rows) == 2
        assert rows[0]["Phase"] == "1. Foundation"
        assert rows[0]["Plans Complete"] == "1/3"
        assert rows[0]["Status"] == "In Progress"
        assert rows[1]["Phase"] == "2. Core Commands"

    def test_empty_input(self):
        rows = parse_table_rows("")
        assert rows == []

    def test_no_data_rows(self):
        table = "| A | B |\n|---|---|\n"
        rows = parse_table_rows(table)
        assert rows == []


# ---------------------------------------------------------------------------
# parse_config_json tests
# ---------------------------------------------------------------------------


class TestParseConfigJson:
    def test_real_config(self):
        config = parse_config_json(
            '{"mode": "yolo", "depth": "standard", "parallelization": true}'
        )
        assert config.mode == "yolo"
        assert config.parallelization is True

    def test_extra_fields(self):
        config = parse_config_json('{"mode": "yolo", "workflow": {"research": true}}')
        assert config.mode == "yolo"


# ---------------------------------------------------------------------------
# parse_state_md tests
# ---------------------------------------------------------------------------


class TestParseStateMd:
    def test_empty_string_returns_defaults(self):
        state = parse_state_md("")
        assert state.current_phase == 0
        assert state.current_phase_name == "unknown"
        assert state.plans_complete == 0
        assert state.plans_total == 0
        assert state.blockers == []
        assert state.decisions == []

    def test_realistic_content(self):
        content = """\
# Project State

## Current Position

Phase: 1 of 5 (Foundation)
Plan: 1 of 3 in current phase
Status: Executing
Last activity: 2026-02-21 -- Completed 01-01-PLAN.md

Progress: [##--------] 9%

## Accumulated Context

### Decisions

- [Roadmap]: Some decision made
- [01-01]: Another decision

### Blockers/Concerns

- Claude Agent SDK is alpha
- GSD question mapping undocumented
"""
        state = parse_state_md(content)
        assert state.current_phase == 1
        assert state.current_phase_name == "Foundation"
        assert state.plans_complete == 1
        assert state.plans_total == 3
        assert state.last_activity == "2026-02-21 -- Completed 01-01-PLAN.md"
        assert len(state.blockers) == 2
        assert "Claude Agent SDK is alpha" in state.blockers[0]
        assert len(state.decisions) == 2

    def test_actual_project_state(self):
        """Parse the real STATE.md from this project."""
        state_path = Path(".planning/STATE.md")
        if state_path.exists():
            state = parse_state_md(state_path.read_text())
            assert state.current_phase >= 1
            assert state.current_phase_name != "unknown"


# ---------------------------------------------------------------------------
# parse_roadmap_md tests
# ---------------------------------------------------------------------------


class TestParseRoadmapMd:
    def test_empty_string(self):
        roadmap = parse_roadmap_md("")
        assert roadmap.phases == []
        assert roadmap.overview is None

    def test_realistic_content(self):
        content = """\
# Roadmap: TestProject

## Overview

This project has three phases.

## Phase Details

### Phase 1: Foundation
**Goal**: Build the base
**Requirements**: PKG-01, PKG-02
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md -- Package skeleton
- [ ] 01-02-PLAN.md -- State parser
- [ ] 01-03-PLAN.md -- Transport layer

### Phase 2: Commands
**Goal**: Build CLI commands
**Requirements**: CMD-01, CMD-02
**Plans**: 2 plans

Plans:
- [ ] 02-01-PLAN.md -- New project command
- [ ] 02-02-PLAN.md -- Plan phase command

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 1/3 | In Progress | - |
| 2. Commands | 0/2 | Not started | - |
"""
        roadmap = parse_roadmap_md(content)
        assert roadmap.overview is not None
        assert "three phases" in roadmap.overview
        assert len(roadmap.phases) == 2
        assert roadmap.phases[0].number == 1
        assert roadmap.phases[0].name == "Foundation"
        assert roadmap.phases[0].goal == "Build the base"
        assert "PKG-01" in roadmap.phases[0].requirements
        assert roadmap.phases[0].plans_total == 3
        assert roadmap.phases[0].plans_complete == 1
        assert roadmap.phases[0].status == "In Progress"
        assert roadmap.phases[1].plans_total == 2
        assert roadmap.phases[1].plans_complete == 0


# ---------------------------------------------------------------------------
# parse_requirements_md tests
# ---------------------------------------------------------------------------


class TestParseRequirementsMd:
    def test_empty_string(self):
        reqs = parse_requirements_md("")
        assert reqs == []

    def test_realistic_content(self):
        content = """\
# Requirements: TestProject

## v1 Requirements

### Transport

- [ ] **TRNS-01**: Spawn subprocess
- [ ] **TRNS-02**: Timeout handling

### Packaging

- [x] **PKG-01**: pip installable
- [x] **PKG-02**: Python 3.10+

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| TRNS-01 | Phase 1 | Pending |
| TRNS-02 | Phase 1 | Pending |
| PKG-01 | Phase 1 | Complete |
| PKG-02 | Phase 1 | Complete |
"""
        reqs = parse_requirements_md(content)
        assert len(reqs) == 4
        # Check a pending requirement
        trns01 = next(r for r in reqs if r.id == "TRNS-01")
        assert trns01.completed is False
        assert trns01.phase == 1
        assert trns01.description == "Spawn subprocess"
        # Check a completed requirement
        pkg01 = next(r for r in reqs if r.id == "PKG-01")
        assert pkg01.completed is True
        assert pkg01.phase == 1


# ---------------------------------------------------------------------------
# parse_project_md tests
# ---------------------------------------------------------------------------


class TestParseProjectMd:
    def test_empty_string(self):
        info = parse_project_md("")
        assert info.name == "unknown"
        assert info.description == "unknown"

    def test_realistic_content(self):
        content = """\
# OpenClawPack

## What This Is

A Python middleware layer for AI agents.

## Core Value

An AI agent can go from idea to project.

## Constraints

- **Runtime**: Python 3.10+
- **Dependency**: Requires Claude Code CLI
"""
        info = parse_project_md(content)
        assert info.name == "OpenClawPack"
        assert "Python middleware" in info.description
        assert info.core_value is not None
        assert "AI agent" in info.core_value
        assert len(info.constraints) == 2
        assert "Python 3.10+" in info.constraints[0]
