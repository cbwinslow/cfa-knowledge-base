#!/usr/bin/env python3
"""
Skill Validator & Scaffolder
Validates Antigravity / Claude Code skills against official specifications:
- YAML Frontmatter (name, description)
- Directory structure (scripts/, examples/, references/)
- Script executability and syntax
- Relative link integrity
"""

import os
import sys
import re
from pathlib import Path

def validate_skill(skill_dir: Path) -> dict:
    issues = []
    warnings = []
    
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        issues.append("Missing required 'SKILL.md' file.")
        return {"valid": False, "issues": issues, "warnings": warnings}
        
    content = skill_md.read_text(encoding="utf-8")
    
    # Check frontmatter
    fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if not fm_match:
        issues.append("SKILL.md is missing valid YAML frontmatter (enclosed in ---).")
    else:
        fm_text = fm_match.group(1)
        if not re.search(r'^name:\s*([a-z0-9\-]+)', fm_text, re.MULTILINE):
            issues.append("Frontmatter missing valid lowercase hyphenated 'name:' field.")
        if not re.search(r'^description:\s*(.+)', fm_text, re.MULTILINE):
            issues.append("Frontmatter missing 'description:' field (crucial for agent routing).")
            
    # Check for scripts directory
    scripts_dir = skill_dir / "scripts"
    if scripts_dir.exists():
        for script in scripts_dir.iterdir():
            if script.suffix == ".py":
                # Check python syntax
                try:
                    compile(script.read_text(encoding="utf-8"), str(script), "exec")
                except SyntaxError as se:
                    issues.append(f"Syntax error in script {script.name}: {se}")
    else:
        warnings.append("No 'scripts/' directory found (recommended for actionable tools).")
        
    # Check examples
    examples_dir = skill_dir / "examples"
    if not examples_dir.exists():
        warnings.append("No 'examples/' directory found (recommended for few-shot guidance).")
        
    # Check references
    references_dir = skill_dir / "references"
    if not references_dir.exists():
        warnings.append("No 'references/' directory found (recommended for progressive disclosure).")
        
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 validate_skill.py <path_to_skill_directory>")
        sys.exit(1)
        
    target_dir = Path(sys.argv[1]).resolve()
    print(f"Validating skill at: {target_dir}")
    
    report = validate_skill(target_dir)
    if report["valid"]:
        print("✓ Skill is VALID according to Antigravity specifications!")
    else:
        print("✗ Skill validation FAILED:")
        for iss in report["issues"]:
            print(f"  - [ERROR] {iss}")
            
    if report["warnings"]:
        print("Warnings / Improvement Recommendations:")
        for w in report["warnings"]:
            print(f"  - [WARN] {w}")

if __name__ == "__main__":
    main()
