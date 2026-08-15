---
name: skill-creator
description: Framework and validator for authoring robust, complete Antigravity and Claude Code skills following official progressive disclosure guidelines.
---

# Skill Creator & Validator Skill

Use this skill whenever you need to create, scaffold, or validate custom skills.

## Official Skill Structure

Every complete skill must follow this architecture:
```text
skills/<skill_name>/
├── SKILL.md          # Required: YAML frontmatter (name, description) + step-by-step workflow
├── scripts/          # Executable Python or Bash helpers with error handling
├── examples/         # Sample inputs, outputs, and few-shot templates
└── references/       # In-depth documentation, formulas, and progressive disclosure manuals
```

## How to Validate an Existing Skill

Run the validation suite:
```bash
python3 /home/cbwinslow/.agents/skills/skill-creator/scripts/validate_skill.py <path_to_skill_folder>
```
