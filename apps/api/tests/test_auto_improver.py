import uuid
import pytest
from unittest.mock import MagicMock, patch

from app.pipeline.auto_improver import auto_improve, _judge_output, _weakest_module


class TestJudgeOutput:
    def test_returns_structured_judgment(self):
        router = MagicMock()
        router.complete.return_value = MagicMock(text='{"quality": 4, "weakest_module": "context", "fix_instruction": "Add audience specifics"}')
        result = _judge_output(prompt="Do X", output="generic output", router=router)
        assert result["quality"] == 4
        assert result["weakest_module"] == "context"
        assert "fix_instruction" in result

    def test_handles_bad_json(self):
        router = MagicMock()
        router.complete.return_value = MagicMock(text="not json")
        result = _judge_output(prompt="Do X", output="output", router=router)
        assert result["quality"] == 5
        assert result["weakest_module"] is None

    def test_quality_clamped_to_1_10(self):
        router = MagicMock()
        router.complete.return_value = MagicMock(text='{"quality": 99, "weakest_module": "role", "fix_instruction": "x"}')
        result = _judge_output(prompt="p", output="o", router=router)
        assert result["quality"] == 10


class TestWeakestModule:
    def test_finds_lowest_score_dimension(self):
        dims = {"clarity": 9, "completeness": 8, "richness": 3, "actionability": 7, "goal_align": 8, "ai_perf": 7}
        assert _weakest_module(dims) == "richness"

    def test_returns_first_on_tie(self):
        dims = {"clarity": 5, "completeness": 5, "richness": 5, "actionability": 5, "goal_align": 5, "ai_perf": 5}
        result = _weakest_module(dims)
        assert result in dims


class TestAutoImprove:
    def test_skips_rewrite_when_score_high(self):
        db = MagicMock()
        router = MagicMock()
        version_id = uuid.uuid4()

        mock_version = MagicMock()
        mock_version.id = version_id
        mock_version.content = "A very good prompt"
        mock_version.modules_json = {"role": "Expert", "objective": "Do X"}
        mock_version.score_json = {
            "composite": 90.0,
            "dimensions": {"clarity": 9, "completeness": 9, "richness": 9, "actionability": 9, "goal_align": 9, "ai_perf": 9},
            "suggestions": [],
        }
        mock_version.prompt_id = uuid.uuid4()
        db.get.return_value = mock_version

        result_version, score, rewritten = auto_improve(version_id, router, db)
        assert rewritten is None
        router.complete.assert_not_called()

    def test_rewrites_weakest_module_when_score_low(self):
        db = MagicMock()
        router = MagicMock()
        version_id = uuid.uuid4()
        prompt_id = uuid.uuid4()

        mock_version = MagicMock()
        mock_version.id = version_id
        mock_version.content = "A weak prompt"
        mock_version.modules_json = {"role": "Expert", "context": "vague"}
        mock_version.score_json = {
            "composite": 55.0,
            "dimensions": {"clarity": 7, "completeness": 6, "richness": 2, "actionability": 7, "goal_align": 6, "ai_perf": 5},
            "suggestions": ["Add more context"],
        }
        mock_version.prompt_id = prompt_id
        db.get.return_value = mock_version

        router.complete.side_effect = [
            MagicMock(text="generic output"),  # run
            MagicMock(text='{"quality": 4, "weakest_module": "context", "fix_instruction": "Add target audience and brand voice"}'),  # judge
            MagicMock(text="Improved context text here"),  # rewrite
        ]

        with patch("app.pipeline.auto_improver.edit_module") as mock_edit:
            mock_new_version = MagicMock()
            mock_new_version.id = uuid.uuid4()
            mock_new_version.content = "Improved prompt"
            mock_edit.return_value = (mock_new_version, MagicMock(composite=75.0, dimensions={}, suggestions=[], scored=True))

            result_version, score_result, rewritten = auto_improve(version_id, router, db)

        assert rewritten == "context"
        mock_edit.assert_called_once()
        call_kwargs = mock_edit.call_args
        assert call_kwargs.kwargs["module_name"] == "context"
