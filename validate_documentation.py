#!/usr/bin/env python3
"""
Documentation Validation Script
Validates code references, internal links, and Mermaid diagrams in documentation.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple, Set

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def check_file_exists(filepath: str) -> bool:
    """Check if a file exists in the workspace."""
    return Path(filepath).exists()

def extract_code_references(content: str) -> List[str]:
    """Extract all code file references from markdown content."""
    # Pattern: `app/path/to/file.py`
    pattern = r'`(app/[a-zA-Z0-9_/]+\.(?:py|yaml|json))`'
    matches = re.findall(pattern, content)
    
    # Also check for references in comments
    comment_pattern = r'# File: (app/[a-zA-Z0-9_/]+\.(?:py|yaml|json))'
    matches.extend(re.findall(comment_pattern, content))
    
    return list(set(matches))

def extract_internal_links(content: str, current_file: str) -> List[Tuple[str, str]]:
    """Extract all internal markdown links."""
    # Pattern: [text](path.md) or [text](../path.md)
    pattern = r'\[([^\]]+)\]\(([^)]+\.md)\)'
    matches = re.findall(pattern, content)
    return [(text, link) for text, link in matches]

def extract_mermaid_diagrams(content: str) -> List[str]:
    """Extract all Mermaid diagram blocks."""
    pattern = r'```mermaid\n(.*?)```'
    matches = re.findall(pattern, content, re.DOTALL)
    return matches

def validate_mermaid_syntax(diagram: str) -> Tuple[bool, str]:
    """Basic validation of Mermaid diagram syntax."""
    diagram = diagram.strip()
    
    # Check for valid diagram types
    valid_types = ['graph', 'flowchart', 'sequenceDiagram', 'classDiagram', 
                   'stateDiagram', 'erDiagram', 'journey', 'gantt', 'pie']
    
    first_line = diagram.split('\n')[0].strip()
    has_valid_type = any(first_line.startswith(t) for t in valid_types)
    
    if not has_valid_type:
        return False, f"Invalid diagram type: {first_line}"
    
    # Check for balanced brackets
    open_brackets = diagram.count('[') + diagram.count('(') + diagram.count('{')
    close_brackets = diagram.count(']') + diagram.count(')') + diagram.count('}')
    
    if open_brackets != close_brackets:
        return False, "Unbalanced brackets"
    
    return True, "OK"

def resolve_link_path(current_file: str, link: str) -> str:
    """Resolve relative link path to absolute path."""
    current_dir = Path(current_file).parent
    
    if link.startswith('../'):
        # Go up one directory
        resolved = current_dir.parent / link[3:]
    else:
        # Same directory
        resolved = current_dir / link
    
    return str(resolved)

def main():
    """Main validation function."""
    print("=" * 80)
    print("Documentation Validation Report")
    print("=" * 80)
    print()
    
    # Find all documentation files
    docs_dir = Path("docs")
    doc_files = list(docs_dir.glob("*.md"))
    doc_files.append(Path("SKILLS.md"))
    
    total_issues = 0
    
    # 1. Validate code references
    print("1. VALIDATING CODE REFERENCES")
    print("-" * 80)
    
    all_code_refs = set()
    missing_files = []
    
    for doc_file in doc_files:
        content = doc_file.read_text()
        code_refs = extract_code_references(content)
        
        for ref in code_refs:
            all_code_refs.add(ref)
            if not check_file_exists(ref):
                missing_files.append((doc_file.name, ref))
    
    if missing_files:
        print(f"{RED}✗ Found {len(missing_files)} missing file references:{RESET}")
        for doc, ref in missing_files:
            print(f"  - {doc}: {ref}")
        total_issues += len(missing_files)
    else:
        print(f"{GREEN}✓ All {len(all_code_refs)} code references are valid{RESET}")
    
    print()
    
    # 2. Validate internal links
    print("2. VALIDATING INTERNAL LINKS")
    print("-" * 80)
    
    broken_links = []
    
    for doc_file in doc_files:
        content = doc_file.read_text()
        links = extract_internal_links(content, str(doc_file))
        
        for text, link in links:
            resolved_path = resolve_link_path(str(doc_file), link)
            if not check_file_exists(resolved_path):
                broken_links.append((doc_file.name, text, link, resolved_path))
    
    if broken_links:
        print(f"{RED}✗ Found {len(broken_links)} broken internal links:{RESET}")
        for doc, text, link, resolved in broken_links:
            print(f"  - {doc}: [{text}]({link}) -> {resolved}")
        total_issues += len(broken_links)
    else:
        print(f"{GREEN}✓ All internal links are valid{RESET}")
    
    print()
    
    # 3. Validate Mermaid diagrams
    print("3. VALIDATING MERMAID DIAGRAMS")
    print("-" * 80)
    
    invalid_diagrams = []
    total_diagrams = 0
    
    for doc_file in doc_files:
        content = doc_file.read_text()
        diagrams = extract_mermaid_diagrams(content)
        total_diagrams += len(diagrams)
        
        for i, diagram in enumerate(diagrams, 1):
            is_valid, error = validate_mermaid_syntax(diagram)
            if not is_valid:
                invalid_diagrams.append((doc_file.name, i, error))
    
    if invalid_diagrams:
        print(f"{RED}✗ Found {len(invalid_diagrams)} invalid Mermaid diagrams:{RESET}")
        for doc, num, error in invalid_diagrams:
            print(f"  - {doc} (diagram #{num}): {error}")
        total_issues += len(invalid_diagrams)
    else:
        print(f"{GREEN}✓ All {total_diagrams} Mermaid diagrams have valid syntax{RESET}")
    
    print()
    
    # 4. Check for consistent terminology
    print("4. CHECKING TERMINOLOGY CONSISTENCY")
    print("-" * 80)
    
    # Key terms from glossary
    glossary_terms = {
        "LangGraph": ["langgraph", "lang-graph", "lang graph"],
        "Artifact": ["artefact"],
        "Character Variant": ["character-variant", "charactervariant"],
        "Grammar ID": ["grammar-id", "grammarid", "grammar_id"],
        "Style Preset": ["style-preset", "stylepreset"],
    }
    
    terminology_issues = []
    
    for doc_file in doc_files:
        content = doc_file.read_text().lower()
        
        for correct_term, variants in glossary_terms.items():
            for variant in variants:
                if variant in content:
                    terminology_issues.append((doc_file.name, variant, correct_term))
    
    if terminology_issues:
        print(f"{YELLOW}⚠ Found {len(terminology_issues)} potential terminology inconsistencies:{RESET}")
        for doc, variant, correct in terminology_issues:
            print(f"  - {doc}: '{variant}' (should be '{correct}')")
        # Don't count as critical issues
    else:
        print(f"{GREEN}✓ Terminology is consistent{RESET}")
    
    print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if total_issues == 0:
        print(f"{GREEN}✓ All validation checks passed!{RESET}")
        print(f"  - {len(all_code_refs)} code references validated")
        print(f"  - {sum(len(extract_internal_links(f.read_text(), str(f))) for f in doc_files)} internal links validated")
        print(f"  - {total_diagrams} Mermaid diagrams validated")
        return 0
    else:
        print(f"{RED}✗ Found {total_issues} critical issues that need to be fixed{RESET}")
        return 1

if __name__ == "__main__":
    exit(main())
