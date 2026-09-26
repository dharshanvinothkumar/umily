"""
Umily — Gemini API Client

Wrapper for Google Gemini API calls.
Handles prompt construction, JSON response parsing, retries, and fallback generation.
"""

import json
import re
from typing import Any, Dict, Optional
from loguru import logger

from app.config import settings
from app.ai.prompts import SYSTEM_PROMPT, build_user_prompt

# Try importing google.generativeai safely
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class GeminiClient:
    """Client for interacting with Google's Gemini API."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None) -> None:
        raw_key = api_key or settings.GEMINI_API_KEY
        self.api_key = raw_key.strip() if raw_key else ""
        self.model_name = model_name or settings.GEMINI_MODEL
        self._is_configured = False
        self.model = None

        if GENAI_AVAILABLE and self.api_key and self.api_key != "your_gemini_api_key_here":
            try:
                genai.configure(api_key=self.api_key)
                
                # Attempt to configure model with system instruction and JSON output mode if available
                generation_config = {"response_mime_type": "application/json"}
                try:
                    self.model = genai.GenerativeModel(
                        model_name=self.model_name,
                        system_instruction=SYSTEM_PROMPT,
                        generation_config=generation_config,
                    )
                except Exception:
                    # Fallback for models or older SDK versions that don't support response_mime_type in init
                    self.model = genai.GenerativeModel(
                        model_name=self.model_name,
                        system_instruction=SYSTEM_PROMPT,
                    )

                self._is_configured = True
                logger.info(f"GeminiClient initialized with model: {self.model_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize GeminiClient: {e}")
        else:
            if not GENAI_AVAILABLE:
                logger.info("google-generativeai package not installed. GeminiClient running in fallback mode.")
            else:
                logger.info("Gemini API key not configured. GeminiClient running in fallback mode.")

    @property
    def is_configured(self) -> bool:
        return self._is_configured

    def generate_plan(self, command: str) -> Dict[str, Any]:
        """
        Generate a structured action plan JSON for a given user command.
        Uses Gemini API if configured; otherwise returns a sensible fallback plan.
        """
        if not self._is_configured or self.model is None:
            logger.info(f"Generating fallback plan for command: {command!r}")
            return self._generate_fallback_plan(command)

        prompt = build_user_prompt(command)
        for attempt in range(1, settings.MAX_RETRIES + 1):
            try:
                logger.info(f"Sending prompt to Gemini (attempt {attempt}/{settings.MAX_RETRIES})...")
                response = self.model.generate_content(prompt)

                # Safely extract text response
                raw_text = self._extract_response_text(response)
                if not raw_text:
                    raise ValueError("Gemini returned empty or blocked text payload")

                # Extract and parse JSON
                plan_data = self._parse_json_payload(raw_text)

                # Validate expected schema structure
                if not isinstance(plan_data, dict) or "steps" not in plan_data:
                    raise ValueError("Parsed response JSON missing 'steps' field")

                logger.info("Successfully generated action plan via Gemini")
                return plan_data

            except Exception as e:
                logger.error(f"Gemini API attempt {attempt} failed: {e}")
                if attempt == settings.MAX_RETRIES:
                    logger.warning("Max retries reached. Falling back to structured fallback plan.")
                    return self._generate_fallback_plan(command)

        return self._generate_fallback_plan(command)

    def _extract_response_text(self, response: Any) -> str:
        """Safely extract raw text from Gemini response object."""
        try:
            if hasattr(response, "text") and response.text:
                return response.text.strip()
        except (ValueError, AttributeError):
            pass

        # Check candidates if .text accessor fails
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                parts_text = [p.text for p in candidate.content.parts if hasattr(p, "text")]
                if parts_text:
                    return "".join(parts_text).strip()

        return ""

    def _parse_json_payload(self, text: str) -> Dict[str, Any]:
        """Extract and parse JSON payload from response text."""
        text = text.strip()

        # 1. Try direct JSON parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. Try extracting from markdown code block ```json ... ```
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if fence_match:
            try:
                return json.loads(fence_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 3. Try finding first '{' and last '}'
        brace_match = re.search(r"(\{[\s\S]*\})", text)
        if brace_match:
            try:
                return json.loads(brace_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not parse valid JSON from text: {text[:100]}...")

    def _clean_json_response(self, text: str) -> str:
        """Backward compatible helper method to strip markdown code fence blocks if present."""
        text = text.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            return match.group(1).strip()
        return text

    def _generate_fallback_plan(self, command: str) -> Dict[str, Any]:
        """Generate a deterministic fallback action plan when Gemini is unavailable."""
        cmd_lower = command.lower()

        if "leetcode" in cmd_lower:
            return {
                "summary": f"Fallback Plan: Open LeetCode and inspect problem for '{command}'",
                "steps": [
                    {
                        "step_id": 1,
                        "tool": "browser",
                        "action": "navigate",
                        "resource_type": "website",
                        "resource_name": "LeetCode",
                        "parameters": {"url": "https://leetcode.com/problemset/all/"},
                        "description": "Navigate to LeetCode problemset",
                        "requires_confirmation": False
                    }
                ]
            }
        elif "browser" in cmd_lower or "http" in cmd_lower or "www." in cmd_lower:
            return {
                "summary": f"Fallback Plan: Browser action for '{command}'",
                "steps": [
                    {
                        "step_id": 1,
                        "tool": "browser",
                        "action": "navigate",
                        "resource_type": "website",
                        "resource_name": "Web Browser",
                        "parameters": {"query": command},
                        "description": "Navigate browser for command",
                        "requires_confirmation": False
                    }
                ]
            }
        else:
            return {
                "summary": f"Fallback Plan: System process for '{command}'",
                "steps": [
                    {
                        "step_id": 1,
                        "tool": "desktop",
                        "action": "execute_command",
                        "resource_type": "tool",
                        "resource_name": "System Command",
                        "parameters": {"command": command},
                        "description": f"Process command: '{command}'",
                        "requires_confirmation": False
                    }
                ]
            }
