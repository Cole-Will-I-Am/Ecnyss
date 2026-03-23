#!/usr/bin/env python3
"""Semantic validator for Ecnyss - validates code quality beyond syntax.

Prevents execution of degenerate outputs like cycle 38's 'one line' failure.
Checks semantic validity, minimum complexity, and content quality before execution.
"""
import ast
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional


class SemanticValidator:
    """Validates code files for semantic quality and completeness.
    
    Catches degenerate outputs that pass JSON validation but are
    functionally useless (e.g., 'one line' files, placeholders).
    """
    
    def __init__(self, min_lines: int = 5, min_functions: int = 0):
        self.min_lines = min_lines
        self.min_functions = min_functions
        self.placeholder_patterns = [
            r'^one line$',
            r'^todo$',
            r'^fixme$',
            r'^placeholder$',
            r'^xxx$',
            r'^hack$',
            r'^why$',
            r'\bTODO\b',
            r'\bFIXME\b',
            r'\bXXX\b',
        ]
    
    def validate_file(self, content: str, filepath: str) -> Tuple[bool, List[str]]:
        """Validate a file's content for semantic quality.
        
        Returns:
            (is_valid, list_of_error_messages)
        """
        errors = []
        
        # Check 1: Not empty
        if not content or not content.strip():
            return False, ["File is empty"]
        
        # Check 2: Minimum line count (non-empty lines)
        non_empty_lines = [l for l in content.split('\n') if l.strip()]
        if len(non_empty_lines) < self.min_lines:
            errors.append(f"Only {len(non_empty_lines)} non-empty lines (min {self.min_lines})")
        
        # Check 3: No placeholder text
        content_lower = content.lower().strip()
        for pattern in self.placeholder_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                errors.append(f"Contains placeholder/degenerate text matching: {pattern}")
                break
        
        # Check 4: Python-specific validation
        if filepath.endswith('.py'):
            py_valid, py_errors = self._validate_python(content)
            errors.extend(py_errors)
        
        return len(errors) == 0, errors
    
    def _validate_python(self, content: str) -> Tuple[bool, List[str]]:
        """Validate Python-specific semantics."""
        errors = []
        
        # Check syntax
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return False, [f"Python syntax error: {e}"]
        
        # Check for meaningful constructs
        has_function = any(isinstance(node, ast.FunctionDef) for node in ast.walk(tree))
        has_class = any(isinstance(node, ast.ClassDef) for node in ast.walk(tree))
        has_import = any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(tree))
        has_docstring = isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant) if tree.body else False
        
        # Must have at least one of: function, class, or import (not just expressions)
        if not (has_function or has_class or has_import):
            errors.append("No functions, classes, or imports found (likely not real code)")
        
        # Check for docstring on modules with functions/classes
        if (has_function or has_class) and not has_docstring:
            errors.append("Missing module docstring")
        
        return len(errors) == 0, errors
    
    def validate_plan(self, plan: Dict[str, Any]) -> Tuple[bool, Dict[str, List[str]]]:
        """Validate all files in an evolution plan.
        
        Returns:
            (all_valid, {filepath: [errors]})
        """
        all_valid = True
        file_errors = {}
        
        for file_entry in plan.get('files', []):
            path = file_entry.get('path', '')
            content = file_entry.get('content', '')
            
            valid, errors = self.validate_file(content, path)
            if not valid:
                all_valid = False
                file_errors[path] = errors
        
        return all_valid, file_errors
    
    def check_degeneration(self, content: str, context: str = "") -> Tuple[bool, str]:
        """Quick check for obvious degeneration patterns.
        
        Returns:
            (is_degenerate, reason)
        """
        content_stripped = content.strip()
        
        # Single word/line checks
        if '\n' not in content_stripped and len(content_stripped.split()) <= 2:
            return True, f"Single line with <=2 words: '{content_stripped[:50]}'"
        
        # Repeated character patterns (e.g., "aaaaaa")
        if len(set(content_stripped)) <= 3 and len(content_stripped) > 10:
            return True, "Repetitive character pattern"
        
        # Very short with no alphanumeric
        if len(content_stripped) < 20 and not any(c.isalnum() for c in content_stripped):
            return True, "Very short with no alphanumeric content"
        
        return False, ""


if __name__ == "__main__":
    validator = SemanticValidator()
    
    # Test 1: Valid Python file
    valid_code = '''#!/usr/bin/env python3
"""Valid module for testing."""
import os

def hello():
    """Say hello."""
    print("Hello")
'''
    result, errors = validator.validate_file(valid_code, "test.py")
    print(f"Valid code: {result}, errors: {errors}")
    
    # Test 2: Cycle 38 style degenerate output
    degenerate = "one line"
    result, errors = validator.validate_file(degenerate, "bad.py")
    print(f"Degenerate: {result}, errors: {errors}")
    
    # Test 3: Placeholder reasoning
    placeholder = "TODO: implement this"
    result, errors = validator.validate_file(placeholder, "placeholder.py")
    print(f"Placeholder: {result}, errors: {errors}")
    
    # Test 4: Empty content
    result, errors = validator.validate_file("", "empty.py")
    print(f"Empty: {result}, errors: {errors}")
