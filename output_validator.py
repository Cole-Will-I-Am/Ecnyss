#!/usr/bin/env python3
"""Output validator for Ecnyss - prevents JSON parsing failures.

Validates that code outputs meet the strict JSON-only requirement.
This addresses the root cause of cycles 6-8 failures (json_failed).
"""
import json
import re
from typing import Tuple, Optional, List

class OutputValidator:
    """Validates Ecnyss outputs meet strict formatting requirements."""
    
    MAX_FILES = 3
    ALLOWED_ACTIONS = ["create", "modify", "delete", "refactor"]
    
    @staticmethod
    def validate_json_only(text: str) -> Tuple[bool, Optional[str]]:
        """Check if text is valid JSON with no extra content."""
        text = text.strip()
        
        # Check for markdown code blocks (common error)
        if text.startswith('') or text.endswith(''):
            return False, "Contains markdown code blocks"
        
        # Check for explanatory text before/after JSON
        lines = text.split('\n')
        if len(lines) > 1:
            # Multi-line should be valid JSON object
            try:
                json.loads(text)
                return True, None
            except json.JSONDecodeError as e:
                return False, f"Invalid JSON: {e}"
        
        # Single line must be valid JSON
        try:
            json.loads(text)
            return True, None
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}"
    
    @staticmethod
    def validate_plan_structure(plan: dict) -> Tuple[bool, List[str]]:
        """Validate the structure of an evolution plan."""
        errors = []
        
        # Required fields
        if 'action' not in plan:
            errors.append("Missing 'action' field")
        elif plan['action'] not in OutputValidator.ALLOWED_ACTIONS:
            errors.append(f"Invalid action: {plan['action']}")
        
        if 'files' not in plan:
            errors.append("Missing 'files' field")
        elif not isinstance(plan['files'], list):
            errors.append("'files' must be a list")
        elif len(plan['files']) > OutputValidator.MAX_FILES:
            errors.append(f"Too many files: {len(plan['files'])} > {OutputValidator.MAX_FILES}")
        
        if 'summary' not in plan:
            errors.append("Missing 'summary' field")
        
        if 'reasoning' not in plan:
            errors.append("Missing 'reasoning' field")
        
        # Validate file entries
        for i, file_entry in enumerate(plan.get('files', [])):
            if not isinstance(file_entry, dict):
                errors.append(f"File entry {i} is not an object")
                continue
            if 'path' not in file_entry:
                errors.append(f"File entry {i} missing 'path'")
            if 'content' not in file_entry:
                errors.append(f"File entry {i} missing 'content'")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def sanitize_output(text: str) -> str:
        """Attempt to extract JSON from text with extra content."""
        # Look for JSON object pattern
        text = text.strip()
        
        # Remove common prefixes
        prefixes = [
            r'^\s*',
            r'^\s*',
            r'^[^{]*',
        ]
        
        for prefix in prefixes:
            text = re.sub(prefix, '', text, flags=re.MULTILINE)
        
        # Remove common suffixes  
        suffixes = [
            r'\s*$',
            r'[^}]*$',
        ]
        
        for suffix in suffixes:
            text = re.sub(suffix, '', text, flags=re.MULTILINE)
        
        return text.strip()

if __name__ == "__main__":
    # Test validation
    validator = OutputValidator()
    
    # Test valid JSON
    valid = '{"action": "create", "files": [], "summary": "test", "reasoning": "test"}'
    ok, err = validator.validate_json_only(valid)
    print(f"Valid JSON test: {ok} (error: {err})")
    
    # Test invalid (markdown wrapped)
    invalid = "\n{\"action\": \"create\"}\n"
    ok, err = validator.validate_json_only(invalid)
    print(f"Invalid JSON test: {ok} (error: {err})")
    
    # Test structure validation
    plan = {
        "action": "create",
        "files": [{"path": "test.py", "content": "# test"}],
        "summary": "Test file",
        "reasoning": "Testing validator"
    }
    ok, errors = validator.validate_plan_structure(plan)
    print(f"Structure validation: {ok} (errors: {errors})")
