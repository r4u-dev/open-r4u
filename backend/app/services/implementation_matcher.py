"""Service for matching traces to implementations with placeholder extraction."""

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tasks import Implementation, Task


class ImplementationMatcher:
    """Matches prompts against templates with placeholder extraction."""

    def match_template(
        self,
        template: str,
        prompt: str,
    ) -> dict[str, Any] | None:
        """Match a prompt against a template with placeholders.

        Args:
            template: Template string with placeholders like {name}, {user_id}
            prompt: Actual prompt to match against the template

        Returns:
            Dict with 'match': True and 'variables': dict of extracted values,
            or None if no match

        """
        # If template equals prompt exactly, it's a match with no variables
        if template == prompt:
            return {"match": True, "variables": {}}

        # Extract placeholder names from template
        placeholder_pattern = r"\{([^}]+)\}"
        placeholders = re.findall(placeholder_pattern, template)

        if not placeholders:
            # No placeholders, so exact match already failed
            return None

        # Build regex pattern from template
        # Escape special regex characters except our placeholders
        pattern = re.escape(template)

        # Replace escaped placeholders with named capture groups
        # We need to match the escaped version: \{name\}
        for placeholder in placeholders:
            escaped_placeholder = re.escape(f"{{{placeholder}}}")
            # Use non-greedy match that captures any characters
            # For adjacent placeholders, we need to be careful
            pattern = pattern.replace(
                escaped_placeholder,
                f"(?P<{placeholder}>.*?)",
                1,  # Replace only first occurrence
            )

        # Handle adjacent placeholders by making the pattern work better
        # Convert remaining escaped braces if any
        pattern = pattern.replace(r"\{", "{").replace(r"\}", "}")

        # For the last placeholder or single placeholder, make it greedy
        # to consume remaining content
        if placeholders:
            last_placeholder = placeholders[-1]
            # Make the last capture group greedy instead of non-greedy
            pattern = pattern.replace(
                f"(?P<{last_placeholder}>.*?)",
                f"(?P<{last_placeholder}>.*)",
            )

        try:
            # Try to match
            regex = re.compile(f"^{pattern}$", re.DOTALL)
            match = regex.match(prompt)

            if match:
                variables = match.groupdict()
                return {"match": True, "variables": variables}

            return None

        except re.error:
            # If regex compilation fails, no match
            return None


def extract_system_prompt_from_trace(
    input_items: list[dict[str, Any]],
) -> str | None:
    """Extract the first message from trace input items.

    Args:
        input_items: List of input item dicts from a trace

    Returns:
        The content of the first message, or None if not found

    """
    for item in input_items:
        if item.get("type") == "message":
            content = item.get("content")
            if content:
                return content

    return None


async def find_matching_implementation(
    input_items: list[dict[str, Any]],
    model: str,
    project_id: int,
    session: AsyncSession,
) -> dict[str, Any] | None:
    """Find a matching implementation for the given trace data.

    Args:
        input_items: Input items from the trace
        model: Model name used in the trace
        project_id: Project ID for the trace
        session: Database session

    Returns:
        Dict with 'implementation_id' and 'variables' if match found,
        None otherwise

    """
    # Extract system prompt from trace
    system_prompt = extract_system_prompt_from_trace(input_items)

    if not system_prompt:
        return None

    # Query all implementations for this project and model
    query = (
        select(Implementation)
        .join(Task, Implementation.task_id == Task.id)
        .where(Task.project_id == project_id)
        .where(Implementation.model == model)
        .order_by(Implementation.id)  # Consistent ordering
    )

    result = await session.execute(query)
    implementations = result.scalars().all()

    # Try to match against each implementation
    matcher = ImplementationMatcher()

    for impl in implementations:
        match_result = matcher.match_template(impl.prompt, system_prompt)

        if match_result and match_result["match"]:
            return {
                "implementation_id": impl.id,
                "variables": match_result["variables"],
            }

    return None
