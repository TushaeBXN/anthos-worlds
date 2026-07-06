import json
import random

import pytest

import anthos_worlds as aw
from anthos_worlds.oracle import oracle_agent


def test_seven_worlds_registered():
    assert len(aw.ALL_ENVS) == 7
    assert set(aw.env_names()) == {"terminal", "shop", "email", "calendar",
                                   "quest", "warehouse", "helpdesk"}


def test_oracle_solves_every_canonical_task():
    report = aw.run_bench(oracle_agent())
    assert len(report.episodes) == 14  # 7 worlds x 2 canonical tasks
    failures = [(e.env, e.task.id, e.reward) for e in report.episodes if not e.success]
    assert not failures, f"oracle failed: {failures}"
    assert report.overall_reward == 1.0


def test_oracle_solves_generated_variants_across_seeds():
    # torture test: 7 worlds x 10 variants x 3 seeds = 210 generated tasks
    for seed in (1, 2, 3):
        report = aw.run_bench(oracle_agent(), variants=10, seed=seed)
        assert len(report.episodes) == 7 * (2 + 10)
        failures = [(e.env, e.task.id, e.task.instruction, e.reward)
                    for e in report.episodes if not e.success]
        assert not failures, f"seed {seed}: oracle failed {failures[:3]}"


def test_variants_are_deterministic_per_seed():
    def signature(seed):
        return [(e.task.id, e.task.instruction)
                for e in aw.run_bench(oracle_agent(), variants=5, seed=seed).episodes]
    assert signature(42) == signature(42)
    assert signature(42) != signature(43)


def test_variants_reproducible_across_env_subsets():
    full = aw.run_bench(oracle_agent(), variants=3, seed=7)
    quest_only = aw.run_bench(oracle_agent(), envs=["quest"], variants=3, seed=7)
    full_quest = [e.task.instruction for e in full.episodes if e.env == "quest"]
    sub_quest = [e.task.instruction for e in quest_only.episodes]
    assert full_quest == sub_quest


def test_generated_tasks_are_valid_task_objects():
    for name in aw.env_names():
        env = aw.make(name)
        rng = random.Random(0)
        for _ in range(5):
            task = env.generate(rng)
            assert task.id.startswith(f"{name}.gen")
            assert task.instruction and task.max_steps > 0
            plan = env.solve(task)
            assert plan and len(plan) <= task.max_steps, \
                f"{name}: solver plan ({len(plan)} steps) exceeds max_steps"


def test_random_agent_runs_and_scores_low():
    report = aw.run_bench(aw.RandomAgent(seed=7))
    assert len(report.episodes) == 14
    assert 0.0 <= report.overall_reward < 1.0
    assert "AnthosWorlds Bench" in report.table()


def test_episode_respects_max_steps():
    env = aw.make("quest")
    task = env.tasks()[0]

    class Stuck(aw.Agent):
        name = "stuck"
        def act(self, env, task, episode):
            return "look"

    episode = aw.run_episode(env, task, Stuck())
    assert len(episode.steps) == task.max_steps
    assert not episode.success


def test_calendar_rejects_conflicts():
    env = aw.make("calendar")
    env.reset(env.tasks()[0])
    result = env.step("book tuesday 10 1 sync")  # offsite runs 9-12
    assert "conflict" in result.observation
    assert env.step("done").reward == 0.0


def test_warehouse_walls_and_grab_rules():
    env = aw.make("warehouse")
    env.reset(env.tasks()[0])
    assert "no crate here" in env.step("grab").observation
    for _ in range(5):
        result = env.step("north")
    assert "wall" in result.observation


def test_terminal_partial_credit():
    env = aw.make("terminal")
    env.reset(env.tasks()[1])  # cleanup: move notes + delete tmp.log
    env.step("rm /tmp.log")
    assert env.step("done").reward == pytest.approx(0.5)


def test_traces_and_sft_export(tmp_path):
    traces = tmp_path / "traces.jsonl"
    sft = tmp_path / "sft.jsonl"
    report = aw.run_bench(oracle_agent(), traces_path=str(traces))
    n = aw.export_sft(report.episodes, str(sft))
    assert n == 14

    raw = [json.loads(line) for line in traces.read_text().splitlines()]
    assert len(raw) == 14 and all(r["success"] for r in raw)

    sample = json.loads(sft.read_text().splitlines()[0])["messages"]
    assert sample[0]["role"] == "system"
    roles = [m["role"] for m in sample[1:]]
    assert roles[::2] == ["user"] * (len(roles) // 2 + len(roles) % 2)
    assert roles[1::2] == ["assistant"] * (len(roles) // 2)


def test_llm_agent_builds_alternating_transcript():
    seen = {}

    def fake_complete(messages):
        seen["messages"] = messages
        return "```\nlook\n```"  # agent must strip fencing

    agent = aw.LLMAgent(fake_complete, name="fake")
    env = aw.make("quest")
    task = env.tasks()[0]
    episode = aw.run_episode(env, task, agent)

    assert all(s.action == "look" for s in episode.steps)
    msgs = seen["messages"]
    assert msgs[0]["role"] == "system" and task.instruction in msgs[0]["content"]
    assert msgs[1]["role"] == "user"
    assert [m["role"] for m in msgs[1:]][-1] == "user"
    assert all(a["role"] != b["role"] for a, b in zip(msgs[1:], msgs[2:]))
