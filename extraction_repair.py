#!/usr/bin/env python3
"""Extraction repair module for Ecnyss - handles malformed JSON from decision engine.

Provides robust JSON extraction with automatic repair of common syntax errors.
Prevents 'extract_failed' errors from halting autonomous evolution (cycle 28).
"""
import json
import re
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path


class ExtractionRepair:
    """Repairs malformed JSON extraction from model outputs."""
    
    def __init__(self):
        self.repair_stats = {
            "total_attempts": 0,
            "successful_repairs": 0,
            "failed_repairs": 0,
            "repair_types": {}
        }
    
    def extract_and_repair(self, text: str) -> Tuple[Optional[Dict], List[str]]:
        """Extract JSON from text with automatic repair attempts.
        
        Returns:
            Tuple of (parsed_dict or None, list of repair attempts made)
        """
        self.repair_stats["total_attempts"] += 1
        repairs_attempted = []
        
        # Strategy 1: Direct extraction
        result = self._try_parse(text)
        if result:
            return result, repairs_attempted
        
        # Strategy 2: Extract from markdown code blocks
        repairs_attempted.append("markdown_extraction")
        markdown_json = self._extract_from_markdown(text)
        if markdown_json:
            result = self._try_parse(markdown_json)
            if result:
                self._record_repair("markdown_extraction")
                return result, repairs_attempted
        
        # Strategy 3: Fix trailing commas
        repairs_attempted.append("trailing_comma_fix")
        fixed = self._fix_trailing_commas(text)
        result = self._try_parse(fixed)
        if result:
            self._record_repair("trailing_comma_fix")
            return result, repairs_attempted
        
        # Strategy 4: Fix unclosed brackets
        repairs_attempted.append("unclosed_bracket_fix")
        fixed = self._fix_unclosed_brackets(text)
        result = self._try_parse(fixed)
        if result:
            self._record_repair("unclosed_bracket_fix")
            return result, repairs_attempted
        
        # Strategy 5: Extract JSON-like structure with regex
        repairs_attempted.append("regex_extraction")
        extracted = self._extract_json_like(text)
        if extracted:
            result = self._try_parse(extracted)
            if result:
                self._record_repair("regex_extraction")
                return result, repairs_attempted
        
        self.repair_stats["failed_repairs"] += 1
        return None, repairs_attempted
    
    def _try_parse(self, text: str) -> Optional[Dict]:
        """Attempt to parse text as JSON."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    
    def _extract_from_markdown(self, text: str) -> Optional[str]:
        """Extract JSON content from markdown code blocks."""
        patterns = [
            r'\s*(.*?)',
            r'\s*(.*?)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                return matches[-1].strip()
        return None
    
    def _fix_trailing_commas(self, text: str) -> str:
        """Remove trailing commas before closing brackets."""
        text = re.sub(r',(\s*[}\]])', r'\1', text)
        return text
    
    def _fix_unclosed_brackets(self, text: str) -> str:
        """Attempt to close unopened brackets."""
        open_braces = text.count('{')
        close_braces = text.count('}')
        open_brackets = text.count('[')
        close_brackets = text.count(']')
        
        fixed = text.strip()
        if open_braces > close_braces:
            fixed += '}' * (open_braces - close_braces)
        if open_brackets > close_brackets:
            fixed += ']' * (open_brackets - close_brackets)
        
        return fixed
    
    def _extract_json_like(self, text: str) -> Optional[str]:
        """Extract text that looks like JSON using regex."""
        match = re.search(r'(\{.*\})', text, re.DOTALL)
        if match:
            return match.group(1)
        return None
    
    def _record_repair(self, repair_type: str):
        """Record successful repair."""
        self.repair_stats["successful_repairs"] += 1
        self.repair_stats["repair_types"][repair_type] = \
            self.repair_stats["repair_types"].get(repair_type, 0) + 1
    
    def get_fallback_plan(self, error_context: str = "") -> Dict[str, Any]:
        """Generate a minimal safe plan when extraction completely fails."""
        return {
            "action": "create",
            "files": [{
                "path": "extraction_log.md",
                "content": f"# Extraction Failure Log\n\nError: {error_context}\nTimestamp: auto-generated\n"
            }],
            "summary": "Log extraction failure and continue",
            "reasoning": "Decision engine output could not be parsed. Logging for analysis to prevent cycle halt."
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get repair statistics."""
        return self.repair_stats.copy()


if __name__ == "__main__":
    repair = ExtractionRepair()
    
    # Test 1: Trailing comma
    malformed1 = '{"action": "create", "files": [],}'
    result, repairs = repair.extract_and_repair(malformed1)
    print(f"Test 1 (trailing comma): {'PASS' if result else 'FAIL'}")
    
    # Test 2: Markdown wrapped
    malformed2 = 'Some text\n\n{"action": "modify", "files": []}\n\nMore text'
    result, repairs = repair.extract_and_repair(malformed2)
    print(f"Test 2 (markdown): {'PASS' if result else 'FAIL'}")
    
    # Test 3: Unclosed brace
    malformed3 = '{"action": "create", "files": ['
    result, repairs = repair.extract_and_repair(malformed3)
    print(f"Test 3 (unclosed): {'PASS' if result else 'FAIL'}")
    
    print(f"\nStats: {repair.get_stats()}")