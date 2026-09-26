"""
Umily — LeetCode Specialized Agent

Specialized workflow for automation of LeetCode tasks:
- Searching problems
- Navigating to problem pages
- Solution generation assistance
"""

from typing import Any, Dict
from loguru import logger

from app.agent.schemas import ActionPlan, ActionStep


class LeetCodeAgent:
    """Specialized workflow helper for LeetCode tasks."""

    def build_leetcode_plan(self, problem_query: str, language: str = "python") -> ActionPlan:
        """Create a structured multi-step action plan for solving a LeetCode problem."""
        logger.info(f"Building LeetCode plan for '{problem_query}' in {language}")
        
        target_url = f"https://leetcode.com/problemset/all/?search={problem_query}"

        steps = [
            ActionStep(
                step_id=1,
                tool="browser",
                action="navigate",
                resource_type="website",
                resource_name="LeetCode",
                parameters={"url": target_url},
                description=f"Navigate to LeetCode search for '{problem_query}'",
                requires_confirmation=False,
            ),
            ActionStep(
                step_id=2,
                tool="browser",
                action="click",
                resource_type="website",
                resource_name="LeetCode",
                parameters={"selector": "a.group\\/title"},
                description=f"Click on the top problem result for '{problem_query}'",
                requires_confirmation=False,
            ),
            ActionStep(
                step_id=3,
                tool="browser",
                action="get_content",
                resource_type="website",
                resource_name="LeetCode",
                parameters={"selector": "div[data-track-load='description_content']"},
                description="Extract problem statement and constraints",
                requires_confirmation=False,
            ),
            ActionStep(
                step_id=4,
                tool="desktop",
                action="notify",
                resource_type="tool",
                resource_name="LeetCode Assistant",
                parameters={
                    "title": "LeetCode Task",
                    "message": f"LeetCode problem '{problem_query}' loaded.",
                },
                description="Notify user of problem status",
                requires_confirmation=False,
            )
        ]

        return ActionPlan(
            summary=f"LeetCode Agent Plan for '{problem_query}'",
            steps=steps,
        )
