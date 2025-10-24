"""Test configuration and utilities for evaluation system tests."""

import pytest
from datetime import datetime, timezone
from typing import List, Dict, Any

from app.enums import ScoreType
from app.models.evaluation import Grader, TestCase, EvaluationConfig
from app.models.projects import Project
from app.models.tasks import Task, Implementation
from app.services.evaluation_service import EvaluationService


class EvaluationTestFixtures:
    """Test fixtures and utilities for evaluation system tests."""

    @staticmethod
    async def create_test_project(session) -> Project:
        """Create a test project."""
        project = Project(name="Test Project")
        session.add(project)
        await session.flush()
        return project

    @staticmethod
    async def create_test_task(session, project_id: int) -> Task:
        """Create a test task."""
        task = Task(project_id=project_id)
        session.add(task)
        await session.flush()
        return task

    @staticmethod
    async def create_test_implementation(session, task_id: int) -> Implementation:
        """Create a test implementation."""
        implementation = Implementation(
            task_id=task_id,
            version="0.1",
            prompt="Test prompt: {{question}}",
            model="gpt-4",
            max_output_tokens=500,
        )
        session.add(implementation)
        await session.flush()
        return implementation

    @staticmethod
    async def create_test_graders(session, project_id: int) -> List[Grader]:
        """Create test graders."""
        graders = []
        
        # Accuracy grader
        accuracy_grader = Grader(
            project_id=project_id,
            name="accuracy",
            description="Evaluates response accuracy",
            prompt="Rate the accuracy of this response: {{context}}",
            score_type=ScoreType.FLOAT,
            model="gpt-4o-mini",
            temperature=0.0,
            max_output_tokens=500,
            response_schema={
                "type": "object",
                "properties": {
                    "score": {"type": "number", "minimum": 0, "maximum": 1},
                    "reasoning": {"type": "string"}
                },
                "required": ["score", "reasoning"]
            },
        )
        session.add(accuracy_grader)
        graders.append(accuracy_grader)

        # Toxicity grader
        toxicity_grader = Grader(
            project_id=project_id,
            name="toxicity",
            description="Evaluates content toxicity",
            prompt="Check if this content is toxic: {{context}}",
            score_type=ScoreType.BOOLEAN,
            model="gpt-4o-mini",
            temperature=0.0,
            max_output_tokens=300,
            response_schema={
                "type": "object",
                "properties": {
                    "score": {"type": "boolean"},
                    "reasoning": {"type": "string"}
                },
                "required": ["score", "reasoning"]
            },
        )
        session.add(toxicity_grader)
        graders.append(toxicity_grader)

        # Helpfulness grader
        helpfulness_grader = Grader(
            project_id=project_id,
            name="helpfulness",
            description="Evaluates response helpfulness",
            prompt="Rate how helpful this response is: {{context}}",
            score_type=ScoreType.FLOAT,
            model="gpt-4o-mini",
            temperature=0.2,
            max_output_tokens=400,
            response_schema={
                "type": "object",
                "properties": {
                    "score": {"type": "number", "minimum": 0, "maximum": 1},
                    "reasoning": {"type": "string"}
                },
                "required": ["score", "reasoning"]
            },
        )
        session.add(helpfulness_grader)
        graders.append(helpfulness_grader)

        await session.flush()
        return graders

    @staticmethod
    async def create_test_cases(session, task_id: int, evaluation_service: EvaluationService) -> List[TestCase]:
        """Create test cases."""
        test_case_data = [
            {
                "description": "Basic math question",
                "arguments": {"question": "What is 2+2?"},
                "expected_output": "4"
            },
            {
                "description": "Science question",
                "arguments": {"question": "What is photosynthesis?"},
                "expected_output": "The process by which plants convert light energy into chemical energy"
            },
            {
                "description": "Creative writing",
                "arguments": {"question": "Write a haiku about coding"},
                "expected_output": "A short poem about programming"
            },
            {
                "description": "Problem solving",
                "arguments": {"question": "How do you calculate the area of a circle?"},
                "expected_output": "π × radius²"
            },
            {
                "description": "Historical question",
                "arguments": {"question": "When did World War II end?"},
                "expected_output": "1945"
            }
        ]

        test_cases = []
        for data in test_case_data:
            test_case = await evaluation_service.create_test_case(
                session=session,
                task_id=task_id,
                **data
            )
            test_cases.append(test_case)

        return test_cases

    @staticmethod
    async def create_evaluation_config(session, task_id: int, grader_ids: List[int], evaluation_service: EvaluationService) -> EvaluationConfig:
        """Create evaluation configuration."""
        config = await evaluation_service.create_or_update_evaluation_config(
            session=session,
            task_id=task_id,
            quality_weight=0.6,
            cost_weight=0.25,
            time_weight=0.15,
            grader_ids=grader_ids,
        )
        return config

    @staticmethod
    def create_mock_execution_results(task_id: int, implementation_id: int, count: int) -> List[Dict[str, Any]]:
        """Create mock execution results."""
        results = []
        for i in range(count):
            result = {
                "id": i + 1,
                "task_id": task_id,
                "implementation_id": implementation_id,
                "started_at": datetime.now(timezone.utc),
                "completed_at": datetime.now(timezone.utc),
                "prompt_rendered": f"Test prompt {i}",
                "result_text": f"Test result {i}",
                "cost": 0.01 + (i * 0.002),
            }
            results.append(result)
        return results

    @staticmethod
    def create_mock_grades(grader_ids: List[int], execution_result_ids: List[int]) -> List[Dict[str, Any]]:
        """Create mock grades."""
        grades = []
        for i, execution_id in enumerate(execution_result_ids):
            for j, grader_id in enumerate(grader_ids):
                grade = {
                    "id": (i * len(grader_ids)) + j + 1,
                    "grader_id": grader_id,
                    "execution_result_id": execution_id,
                    "score_float": 0.7 + (i * 0.05) + (j * 0.1) if j % 2 == 0 else None,
                    "score_boolean": i % 2 == 0 if j % 2 == 1 else None,
                    "reasoning": f"Grader {grader_id} evaluation for execution {execution_id}",
                    "confidence": 0.8 + (i * 0.02),
                    "grading_started_at": datetime.now(timezone.utc),
                    "grading_completed_at": datetime.now(timezone.utc),
                    "prompt_tokens": 50 + (i * 5),
                    "completion_tokens": 30 + (i * 3),
                    "total_tokens": 80 + (i * 8),
                }
                grades.append(grade)
        return grades


@pytest.fixture
def evaluation_test_fixtures():
    """Provide evaluation test fixtures."""
    return EvaluationTestFixtures()


@pytest.fixture
def evaluation_service():
    """Create evaluation service instance."""
    from app.config import Settings
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        openai_api_key="test-key",
    )
    return EvaluationService(settings)


# Test data constants
EVALUATION_TEST_DATA = {
    "project_name": "Evaluation Test Project",
    "task_prompt": "You are a helpful AI assistant. Answer: {{question}}",
    "implementation_model": "gpt-4",
    "implementation_temperature": 0.7,
    "implementation_max_tokens": 1000,
    "grader_configs": [
        {
            "name": "accuracy",
            "score_type": "float",
            "model": "gpt-4o-mini",
            "temperature": 0.0,
        },
        {
            "name": "toxicity",
            "score_type": "boolean",
            "model": "gpt-4o-mini",
            "temperature": 0.0,
        },
        {
            "name": "helpfulness",
            "score_type": "float",
            "model": "gpt-4o-mini",
            "temperature": 0.2,
        }
    ],
    "test_cases": [
        {
            "description": "Basic math question",
            "arguments": {"question": "What is 2+2?"},
            "expected_output": "4"
        },
        {
            "description": "Science question",
            "arguments": {"question": "What is photosynthesis?"},
            "expected_output": "The process by which plants convert light energy into chemical energy"
        },
        {
            "description": "Creative writing",
            "arguments": {"question": "Write a haiku about coding"},
            "expected_output": "A short poem about programming"
        }
    ],
    "evaluation_config": {
        "quality_weight": 0.6,
        "cost_weight": 0.25,
        "time_weight": 0.15,
    }
}

# Performance test data
PERFORMANCE_TEST_DATA = {
    "test_case_count": 10,
    "cost_range": (0.01, 0.055),  # 0.01 to 0.055 in steps of 0.005
    "time_range": (1000, 1900),   # 1000ms to 1900ms in steps of 100ms
    "quality_range": (0.5, 0.95), # 0.5 to 0.95 in steps of 0.05
}

# Error test scenarios
ERROR_TEST_SCENARIOS = [
    {
        "name": "no_test_cases",
        "description": "Test evaluation with no test cases",
        "expected_error": "No test cases found for task"
    },
    {
        "name": "no_graders",
        "description": "Test evaluation with no graders",
        "expected_error": "No graders available for evaluation"
    },
    {
        "name": "execution_failure",
        "description": "Test evaluation with execution failure",
        "expected_error": "Execution failed"
    },
    {
        "name": "invalid_weights",
        "description": "Test evaluation config with invalid weights",
        "expected_error": "Quality, cost, and time weights must sum to 1.0"
    }
]
