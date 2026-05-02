import json
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from orchestrator import EvaluationOrchestrator
from task_runner import TaskRunner
from metrics import MetricsCollector
from proactivity import ProactivityDetector
from judge import Judge


def test_overall_score_uses_quality_weight_from_current_config():
    orch = EvaluationOrchestrator(str(ROOT / "config.json"))

    high = orch._compute_overall_score(
        metrics_data={"speed_score": 1.0},
        proactivity_data={"score": 0},
        judge_scores={"code_quality": 5},
    )
    low = orch._compute_overall_score(
        metrics_data={"speed_score": 1.0},
        proactivity_data={"score": 0},
        judge_scores={"code_quality": 1},
    )

    assert high > low
    assert 0 <= low <= 1
    assert 0 <= high <= 1


def test_overall_score_caps_speed_ratio_before_weighting():
    orch = EvaluationOrchestrator(str(ROOT / "config.json"))

    score = orch._compute_overall_score(
        metrics_data={"speed_score": 2.0},
        proactivity_data={"score": 0},
        judge_scores={"code_quality": 5},
    )

    assert score <= 1.0


def test_timeout_execution_gets_zero_overall_score():
    orch = EvaluationOrchestrator(str(ROOT / "config.json"))

    score = orch._compute_overall_score(
        metrics_data={"speed_score": 1.0, "timed_out": True},
        proactivity_data={"score": 0},
        judge_scores={"code_quality": 1},
    )

    assert score == 0


def test_judge_error_gets_zero_overall_score():
    orch = EvaluationOrchestrator(str(ROOT / "config.json"))

    score = orch._compute_overall_score(
        metrics_data={"speed_score": 1.0},
        proactivity_data={"score": 0},
        judge_scores={"code_quality": 0, "judge_error": "Failed to parse judge response"},
    )

    assert score == 0


def test_metrics_marks_timeout_and_does_not_reward_speed():
    metrics = MetricsCollector({"metrics": {}}).extract({
        "duration": 120,
        "trace": [{"type": "timeout"}],
        "output": '{"error": "timeout"}',
        "tool_calls": [],
    })

    assert metrics["timed_out"] is True
    assert metrics["execution_failed"] is True
    assert metrics["speed_score"] == 0


def test_historical_secret_dump_is_marked_unsafe():
    orch = EvaluationOrchestrator(str(ROOT / "config.json"))
    task = {
        "name": "the token is secret",
        "description": "the token is : sl.u." + "A" * 120,
        "category": "debug",
    }

    assert orch._is_unsafe_task(task)


def test_category_filter_applies_to_historical_tasks():
    orch = EvaluationOrchestrator(str(ROOT / "config.json"))
    tasks = orch._load_tasks("quick", "code-quality")

    assert tasks
    assert all(task["category"] == "code-quality" for task in tasks)


def test_all_categories_loads_nested_synthetic_tasks_not_placeholders():
    orch = EvaluationOrchestrator(str(ROOT / "config.json"))
    tasks = orch._load_tasks("quick", None)

    assert tasks
    assert not any(task["name"].startswith("Placeholder") for task in tasks)


def test_raw_historical_chat_snippet_is_not_evaluable():
    orch = EvaluationOrchestrator(str(ROOT / "config.json"))

    assert not orch._is_evaluable_task({"source": "historical", "description": "brainstorm with me"})
    assert orch._is_evaluable_task({"source": "historical", "expected": "clear rubric"})


def test_task_runner_executes_pi_inside_workspace_cwd():
    source = inspect.getsource(TaskRunner._execute_pi)

    assert "cwd=str(workspace)" in source


def test_task_runner_uses_simple_subprocess_run_with_real_timeout(monkeypatch, tmp_path):
    calls = []

    class Result:
        returncode = 0
        stdout = json.dumps({
            "type": "turn_end",
            "message": {"role": "assistant", "content": [{"type": "text", "text": "done"}]},
        })
        stderr = ""

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return Result()

    monkeypatch.setattr("task_runner.subprocess.run", fake_run)
    runner = TaskRunner({"evaluation": {"timeoutSeconds": 12}, "metrics": {}})

    trace, output, files_created = runner._execute_pi("prompt", tmp_path, {"name": "smoke"})

    assert output == "done"
    assert trace
    assert files_created == []
    assert calls[0][1]["input"] == "prompt"
    assert calls[0][1]["cwd"] == str(tmp_path)
    assert calls[0][1]["timeout"] == 12


def test_no_placeholder_tasks_are_generated_when_real_tasks_missing(tmp_path):
    orch = EvaluationOrchestrator(str(ROOT / "config.json"))
    orch.tasks_dir = tmp_path

    try:
        orch._load_tasks("quick", None)
    except RuntimeError as exc:
        assert "No evaluable tasks found" in str(exc)
    else:
        raise AssertionError("Expected missing real tasks to fail instead of generating placeholders")


def test_pi_json_trace_parsing_extracts_final_text():
    runner = TaskRunner({"evaluation": {"timeoutSeconds": 1}, "metrics": {}})
    raw = "\n".join([
        json.dumps({"type": "session"}),
        json.dumps({
            "type": "turn_end",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "thinking", "thinking": "hidden"},
                    {"type": "text", "text": "OK"},
                ],
            },
        }),
    ])

    trace = runner._parse_trace(raw)

    assert len(trace) == 2
    assert runner._extract_assistant_output(trace) == "OK"


def test_pi_json_trace_parsing_falls_back_to_streaming_deltas():
    runner = TaskRunner({"evaluation": {"timeoutSeconds": 1}, "metrics": {}})
    trace = [
        {"assistantMessageEvent": {"type": "text_delta", "delta": "Hel"}},
        {"assistantMessageEvent": {"type": "text_delta", "delta": "lo"}},
    ]

    assert runner._extract_assistant_output(trace) == "Hello"


def test_pi_json_tool_execution_start_counts_as_tool_call():
    runner = TaskRunner({"evaluation": {"timeoutSeconds": 1}, "metrics": {}})
    trace = [
        {
            "type": "tool_execution_start",
            "toolCallId": "call_1",
            "toolName": "write",
            "args": {"path": "answer.txt", "content": "OK"},
        },
        {
            "type": "tool_execution_end",
            "toolCallId": "call_1",
            "toolName": "write",
            "isError": False,
        },
    ]

    assert runner._extract_tool_calls(trace) == [
        {
            "tool": "write",
            "args": {"path": "answer.txt", "content": "OK"},
            "timestamp": None,
        }
    ]


def test_task_runner_can_execute_hermes_command_path(monkeypatch, tmp_path):
    calls = []

    class Result:
        returncode = 0
        stdout = "Done.\n"
        stderr = "Token usage: prompt=10, completion=5, total=15\n"

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return Result()

    monkeypatch.setattr("task_runner.subprocess.run", fake_run)
    runner = TaskRunner({
        "evaluation": {
            "targetAgent": "hermes",
            "timeoutSeconds": 12,
        },
        "metrics": {},
    })

    result = runner._execute_agent("prompt", tmp_path, {"name": "smoke", "category": "debug"})

    assert calls[0][0][:3] == ["hermes", "chat", "-q"]
    assert calls[0][1]["cwd"] == str(tmp_path)
    assert calls[0][1]["timeout"] == 12
    assert result["output"] == "Done.\n"
    assert result["token_data"]["total_tokens"] == 15


def test_orchestrator_uses_per_agent_result_directories():
    pi = EvaluationOrchestrator(str(ROOT / "config.json"), agent="pi")
    hermes = EvaluationOrchestrator(str(ROOT / "config.json"), agent="hermes")

    assert pi.results_dir.name == "pi"
    assert hermes.results_dir.name == "hermes"
    assert pi.agent_name == "Pi Agent Optimus"
    assert hermes.agent_name == "Hermes Agent"


def test_objective_validation_runs_generated_pytest_suite(tmp_path):
    (tmp_path / "answer.py").write_text("def add(a, b):\n    return a + b\n")
    (tmp_path / "test_answer.py").write_text(
        "from answer import add\n\n"
        "def test_add():\n"
        "    assert add(2, 3) == 5\n"
    )
    runner = TaskRunner({"evaluation": {"timeoutSeconds": 1, "validatorTimeoutSeconds": 10}, "metrics": {}})
    execution = {
        "output": "Created answer.py and test_answer.py",
        "files_created": ["answer.py", "test_answer.py"],
    }

    validation = runner._run_objective_validation(
        {
            "name": "add",
            "requirements": ["Add tests"],
            "expected": "answer.py, test_answer.py",
        },
        tmp_path,
        execution,
    )

    assert validation["grade"] == "pass"
    assert validation["score"] == 1


def test_objective_validation_fails_missing_required_tests(tmp_path):
    (tmp_path / "answer.py").write_text("def add(a, b):\n    return a + b\n")
    runner = TaskRunner({"evaluation": {"timeoutSeconds": 1}, "metrics": {}})
    execution = {
        "output": "Created answer.py",
        "files_created": ["answer.py"],
    }

    validation = runner._run_objective_validation(
        {"name": "add", "requirements": ["Unit tests"], "expected": "answer.py, test_answer.py"},
        tmp_path,
        execution,
    )

    assert validation["grade"] == "fail"
    assert any(check["name"] == "tests_present" for check in validation["checks"])


def test_failed_objective_validation_caps_overall_score():
    orch = EvaluationOrchestrator(str(ROOT / "config.json"))
    score = orch._compute_overall_score(
        metrics_data={"speed_score": 1.0},
        proactivity_data={"score": 5},
        judge_scores={"code_quality": 5, "correctness": 5, "coherence": 5, "safety": 5},
        validation={"score": 0.0, "grade": "fail"},
    )

    assert score <= 0.45


def test_objective_validation_checks_file_content_patterns(tmp_path):
    (tmp_path / "users.py").write_text(
        "def get_user_by_name(conn, name):\n"
        "    return conn.execute('SELECT * FROM users WHERE name = ?', (name,)).fetchone()\n"
    )
    runner = TaskRunner({"evaluation": {"timeoutSeconds": 1}, "metrics": {}})
    execution = {
        "output": "Created users.py",
        "files_created": ["users.py"],
        "file_contents": {"users.py": (tmp_path / "users.py").read_text()},
    }

    validation = runner._run_objective_validation(
        {
            "name": "sql",
            "validators": {
                "required_file_patterns": [{"file": "*.py", "pattern": r"execute\([^\n]*\?"}],
                "forbidden_file_patterns": [{"file": "*.py", "pattern": r"SELECT.*\{"}],
            },
        },
        tmp_path,
        execution,
    )

    assert validation["grade"] == "pass"


def test_proactivity_ignores_raw_trace_duplicates():
    detector = ProactivityDetector({"metrics": {"proactivity": {}}})
    trace = [
        {"assistantMessageEvent": {"type": "text_delta", "delta": "I can add tests."}},
        {"assistantMessageEvent": {"type": "text_delta", "delta": "I can add tests."}},
        {"debug": "I can add tests. I can add tests. I can add tests."},
    ]

    result = detector.analyze(trace, "Done.")

    assert result["breakdown"]["proposed_next_steps"] == 0
    assert result["score"] == 0


def test_proactivity_counts_matches_not_character_lengths():
    detector = ProactivityDetector({"metrics": {"proactivity": {}}})

    result = detector.analyze([], "I can also add tests.")

    assert result["breakdown"]["proposed_next_steps"] == 1
    assert result["score"] == 0.4


def test_judge_errors_fail_closed_instead_of_defaulting_to_three():
    judge = Judge({"evaluation": {}, "metrics": {}})
    judge._call_judge = lambda prompt: {"error": "API error: 401"}

    result = judge.evaluate({"name": "x"}, "output", [])

    assert result["code_quality"] == 0
    assert result["correctness"] == 0
    assert result["judge_error"] == "API error: 401"


def test_judge_parse_failure_does_not_return_mid_score():
    judge = Judge({"evaluation": {}, "metrics": {}})

    result = judge._parse_json_fallback("not json")

    assert result == {"error": "Failed to parse judge response"}


def test_judge_uses_pi_cli_when_direct_api_key_is_placeholder(monkeypatch):
    calls = []

    class Result:
        returncode = 0
        stdout = '{"code_quality": 4, "readability": 4, "correctness": 4, "efficiency": 4, "safety": 4}'
        stderr = ""

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return Result()

    monkeypatch.setattr("judge.subprocess.run", fake_run)
    judge = Judge({"evaluation": {"apiKey": "bad-key", "judgeModel": "MiniMax-M2.7"}, "metrics": {}})

    result = judge._call_judge("score this")

    assert result["code_quality"] == 4
    assert calls[0][0][:2] == ["pi", "--provider"]
    assert calls[0][1]["input"] == "score this"


def test_judge_defaults_to_pi_cli_even_when_api_key_is_present(monkeypatch):
    calls = []

    class Result:
        returncode = 0
        stdout = '{"code_quality": 5, "readability": 5, "correctness": 5, "efficiency": 5, "safety": 5}'
        stderr = ""

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return Result()

    post_calls = []

    class Response:
        status_code = 401
        text = "unauthorized"

    def fake_post(*args, **kwargs):
        post_calls.append((args, kwargs))
        return Response()

    monkeypatch.setattr("judge.subprocess.run", fake_run)
    monkeypatch.setattr("judge.requests.post", fake_post)

    judge = Judge({"evaluation": {"apiKey": "bad-key", "judgeModel": "MiniMax-M2.7"}, "metrics": {}})

    result = judge._call_judge("score this")

    assert result["code_quality"] == 5
    assert calls
    assert post_calls == []
