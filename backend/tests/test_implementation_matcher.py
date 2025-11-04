"""Tests for implementation matching with placeholder extraction."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.projects import Project
from app.models.tasks import Implementation, Task
from app.services.implementation_matcher import (
    ImplementationMatcher,
    extract_system_prompt_from_trace,
    find_matching_implementation,
)


@pytest_asyncio.fixture
async def project(test_session: AsyncSession) -> Project:
    """Create a test project."""
    project = Project(name="Test Project")
    test_session.add(project)
    await test_session.flush()
    return project


@pytest_asyncio.fixture
async def task(test_session: AsyncSession, project: Project) -> Task:
    """Create a test task."""
    task = Task(name="Test Task", description="Test task", project_id=project.id)
    test_session.add(task)
    await test_session.flush()
    return task


class TestImplementationMatcher:
    """Test the implementation matcher service."""

    def test_match_exact_prompt_no_placeholders(self):
        """Test matching with exact prompt and no placeholders."""
        template = "You are a helpful assistant."
        prompt = "You are a helpful assistant."

        matcher = ImplementationMatcher()
        result = matcher.match_template(template, prompt)

        assert result is not None
        assert result["match"] is True
        assert result["variables"] == {}

    def test_match_with_single_placeholder(self):
        """Test matching with a single placeholder."""
        template = "Hello, {{name}}! How can I help you?"
        prompt = "Hello, John! How can I help you?"

        matcher = ImplementationMatcher()
        result = matcher.match_template(template, prompt)

        assert result is not None
        assert result["match"] is True
        assert result["variables"] == {"name": "John"}

    def test_match_with_multiple_placeholders(self):
        """Test matching with multiple placeholders."""
        template = "This is {{title}} {{name}}, age {{age}}. Be nice to them."
        prompt = "This is Mr. Smith, age 45. Be nice to them."

        matcher = ImplementationMatcher()
        result = matcher.match_template(template, prompt)

        assert result is not None
        assert result["match"] is True
        assert result["variables"] == {
            "title": "Mr.",
            "name": "Smith",
            "age": "45",
        }

    def test_no_match_different_structure(self):
        """Test that different prompt structures don't match."""
        template = "You are a helpful assistant."
        prompt = "You are a mean robot."

        matcher = ImplementationMatcher()
        result = matcher.match_template(template, prompt)

        assert result is None

    def test_no_match_with_placeholder_mismatch(self):
        """Test that mismatched placeholders don't match."""
        template = "Hello, {{name}}! Welcome to {{place}}."
        prompt = "Hello, John!"

        matcher = ImplementationMatcher()
        result = matcher.match_template(template, prompt)

        assert result is None

    def test_match_with_special_characters(self):
        """Test matching with special characters in prompt."""
        template = "User email: {{email}}. Process their request."
        prompt = "User email: john.doe@example.com. Process their request."

        matcher = ImplementationMatcher()
        result = matcher.match_template(template, prompt)

        assert result is not None
        assert result["match"] is True
        assert result["variables"] == {"email": "john.doe@example.com"}

    def test_match_with_multiline_prompt(self):
        """Test matching with multiline prompts."""
        template = """You are {{role}}.
User: {{name}}
Task: {{task}}"""
        prompt = """You are a senior developer.
User: Alice
Task: Review code"""

        matcher = ImplementationMatcher()
        result = matcher.match_template(template, prompt)

        assert result is not None
        assert result["match"] is True
        assert result["variables"] == {
            "role": "a senior developer",
            "name": "Alice",
            "task": "Review code",
        }

    def test_match_empty_placeholder_value(self):
        """Test matching when placeholder value is empty."""
        template = "Hello{{greeting}}!"
        prompt = "Hello!"

        matcher = ImplementationMatcher()
        result = matcher.match_template(template, prompt)

        # This could match with empty value
        assert result is not None
        assert result["match"] is True
        assert result["variables"] == {"greeting": ""}

    def test_match_placeholder_with_whitespace(self):
        """Test matching placeholders that contain whitespace."""
        template = "Dear {{name}},"
        prompt = "Dear John Smith,"

        matcher = ImplementationMatcher()
        result = matcher.match_template(template, prompt)

        assert result is not None
        assert result["match"] is True
        assert result["variables"] == {"name": "John Smith"}

    def test_match_adjacent_placeholders(self):
        """Test matching when placeholders are adjacent."""
        template = "{{first}}{{second}}"
        prompt = "HelloWorld"

        matcher = ImplementationMatcher()
        result = matcher.match_template(template, prompt)

        # This is ambiguous - could be "Hello"+"World" or "H"+"elloWorld" etc.
        # Implementation should handle this reasonably
        assert result is not None
        assert result["match"] is True

    def test_match_with_numbers_in_values(self):
        """Test matching with numeric values."""
        template = "Transaction amount: ${{amount}} for account {{account_id}}"
        prompt = "Transaction amount: $150.50 for account 12345"

        matcher = ImplementationMatcher()
        result = matcher.match_template(template, prompt)

        assert result is not None
        assert result["match"] is True
        assert result["variables"] == {
            "amount": "150.50",
            "account_id": "12345",
        }


class TestExtractSystemPrompt:
    """Test first message extraction from traces."""

    def test_extract_first_message_from_system_role(self):
        """Test extracting first message when it's a system message."""
        input_items = [
            {"type": "message", "role": "system", "content": "You are helpful."},
            {"type": "message", "role": "user", "content": "Hello!"},
        ]

        prompt = extract_system_prompt_from_trace(input_items)

        assert prompt == "You are helpful."

    def test_extract_first_message_from_user_role(self):
        """Test extracting first message when it's a user message."""
        input_items = [
            {"type": "message", "role": "user", "content": "Hello!"},
            {"type": "message", "role": "assistant", "content": "Hi there!"},
        ]

        prompt = extract_system_prompt_from_trace(input_items)

        assert prompt == "Hello!"

    def test_extract_first_message_regardless_of_role(self):
        """Test that the first message is extracted regardless of role."""
        input_items = [
            {"type": "message", "role": "assistant", "content": "First message."},
            {"type": "message", "role": "system", "content": "Second message."},
            {"type": "message", "role": "user", "content": "Third message."},
        ]

        prompt = extract_system_prompt_from_trace(input_items)

        assert prompt == "First message."

    def test_extract_with_no_messages(self):
        """Test when there are no messages."""
        input_items = []

        prompt = extract_system_prompt_from_trace(input_items)

        assert prompt is None

    def test_extract_with_empty_content(self):
        """Test extracting when content is empty or None."""
        input_items = [
            {"type": "message", "role": "system", "content": None},
            {"type": "message", "role": "user", "content": "Second message."},
        ]

        prompt = extract_system_prompt_from_trace(input_items)

        assert prompt == "Second message."


class TestFindMatchingImplementation:
    """Test finding matching implementation for a trace."""

    @pytest.mark.asyncio
    async def test_find_matching_implementation_exact_match(
        self,
        test_session: AsyncSession,
        task: Task,
    ):
        """Test finding an exact match."""
        # Create an implementation
        impl = Implementation(
            task_id=task.id,
            prompt="You are a helpful assistant.",
            model="gpt-4",
            max_output_tokens=1000,
        )
        test_session.add(impl)
        await test_session.flush()

        # Create input items for trace
        input_items = [
            {
                "type": "message",
                "role": "system",
                "content": "You are a helpful assistant.",
            },
            {"type": "message", "role": "user", "content": "Hello!"},
        ]

        result = await find_matching_implementation(
            input_items=input_items,
            model="gpt-4",
            project_id=task.project_id,
            session=test_session,
        )

        assert result is not None
        assert result["implementation_id"] == impl.id
        assert result["variables"] == {}

    @pytest.mark.asyncio
    async def test_find_matching_implementation_with_placeholders(
        self,
        test_session: AsyncSession,
        task: Task,
    ):
        """Test finding a match with placeholder extraction."""
        # Create an implementation with placeholders
        impl = Implementation(
            task_id=task.id,
            prompt="Hello, {{name}}! You are user #{{user_id}}.",
            model="gpt-4",
            max_output_tokens=1000,
        )
        test_session.add(impl)
        await test_session.flush()

        # Create input items for trace
        input_items = [
            {
                "type": "message",
                "role": "system",
                "content": "Hello, Alice! You are user #42.",
            },
            {"type": "message", "role": "user", "content": "Hi!"},
        ]

        result = await find_matching_implementation(
            input_items=input_items,
            model="gpt-4",
            project_id=task.project_id,
            session=test_session,
        )

        assert result is not None
        assert result["implementation_id"] == impl.id
        assert result["variables"] == {"name": "Alice", "user_id": "42"}

    @pytest.mark.asyncio
    async def test_no_match_different_model(
        self,
        test_session: AsyncSession,
        task: Task,
    ):
        """Test that different models don't match."""
        # Create an implementation
        impl = Implementation(
            task_id=task.id,
            prompt="You are a helpful assistant.",
            model="gpt-4",
            max_output_tokens=1000,
        )
        test_session.add(impl)
        await test_session.flush()

        # Create input items for trace with different model
        input_items = [
            {
                "type": "message",
                "role": "system",
                "content": "You are a helpful assistant.",
            },
        ]

        result = await find_matching_implementation(
            input_items=input_items,
            model="gpt-3.5-turbo",  # Different model
            project_id=task.project_id,
            session=test_session,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_no_match_different_project(
        self,
        test_session: AsyncSession,
        task: Task,
        project: Project,
    ):
        """Test that implementations from different projects don't match."""
        # Create another project and task
        other_project = Project(name="Other Project")
        test_session.add(other_project)
        await test_session.flush()

        # Create an implementation
        impl = Implementation(
            task_id=task.id,
            prompt="You are a helpful assistant.",
            model="gpt-4",
            max_output_tokens=1000,
        )
        test_session.add(impl)
        await test_session.flush()

        # Try to match with different project
        input_items = [
            {
                "type": "message",
                "role": "system",
                "content": "You are a helpful assistant.",
            },
        ]

        result = await find_matching_implementation(
            input_items=input_items,
            model="gpt-4",
            project_id=other_project.id,  # Different project
            session=test_session,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_match_first_when_multiple_implementations_match(
        self,
        test_session: AsyncSession,
        task: Task,
    ):
        """Test that the first created implementation is returned when multiple match."""
        # Create multiple implementations that would match
        impl1 = Implementation(
            task_id=task.id,
            prompt="You are a helpful assistant.",
            model="gpt-4",
            max_output_tokens=1000,
        )
        test_session.add(impl1)
        await test_session.flush()

        impl2 = Implementation(
            task_id=task.id,
            prompt="You are a helpful assistant.",
            model="gpt-4",
            max_output_tokens=1000,
        )
        test_session.add(impl2)
        await test_session.flush()

        # Create input items
        input_items = [
            {
                "type": "message",
                "role": "system",
                "content": "You are a helpful assistant.",
            },
        ]

        result = await find_matching_implementation(
            input_items=input_items,
            model="gpt-4",
            project_id=task.project_id,
            session=test_session,
        )

        assert result is not None
        # Should match the first one (by ID)
        assert result["implementation_id"] == impl1.id

    @pytest.mark.asyncio
    async def test_no_match_when_no_messages(
        self,
        test_session: AsyncSession,
        task: Task,
    ):
        """Test when trace has no messages at all."""
        # Create an implementation
        impl = Implementation(
            task_id=task.id,
            prompt="You are a helpful assistant.",
            model="gpt-4",
            max_output_tokens=1000,
        )
        test_session.add(impl)
        await test_session.flush()

        # Create input items without any messages
        input_items = []

        result = await find_matching_implementation(
            input_items=input_items,
            model="gpt-4",
            project_id=task.project_id,
            session=test_session,
        )

        assert result is None
