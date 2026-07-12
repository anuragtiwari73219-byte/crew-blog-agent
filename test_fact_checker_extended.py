"""
Extended stress-test for fact_checker (repo_blog_agent.py).

Covers two gaps the first test (test_fact_checker.py) didn't:

1. SUBTLE DISTORTION: instead of inventing a whole new feature, this
   takes a REAL fact from the analysis and quietly changes a number/word.
   This is much harder to catch than "RepoBlogger has 50,000 users"
   because the claim LOOKS like it belongs.

2. CONSISTENCY: runs the same blunt-fabrication check 3 times and
   compares verdicts. LLMs are non-deterministic — a single FLAGGED
   run proves it CAN catch fabrication, not that it RELIABLY does.

Run:
    python test_fact_checker_extended.py
"""

from crewai import Task, Crew, Process
from repo_blog_agent import fact_checker

# ---------------------------------------------------------------------
# TEST A: Subtle distortion
# ---------------------------------------------------------------------
ANALYSIS_A = """
TECHNICAL ANALYSIS (ground truth)

1. What the project does: An email triage agent that classifies incoming
   Gmail messages by urgency and topic using an LLM.
2. Tech stack: FastAPI, Gmail OAuth 2.0, Groq (llama-3.3-70b-versatile).
3. Evaluation results (from eval_triage.py on a 93-email labeled test set,
   after excluding rate-limit failures): ~97% urgency accuracy,
   ~93% topic accuracy across 9 categories.
4. Deployment: Render, with token refresh handled via /tmp/token.json
   due to /etc/secrets/ being read-only.
"""

# Claim below quietly changes 93% -> 99% and 9 categories -> 12 categories.
# Both numbers are close enough to the real ones to look plausible,
# and the sentence structure mimics a legitimate summary.
BLOG_A = """
# AI Email Triage Agent

This project classifies incoming Gmail messages by urgency and topic
using Groq's llama-3.3-70b-versatile model, served through FastAPI with
Gmail OAuth 2.0 integration.

On the evaluation set, the agent hit 97% urgency accuracy and 99% topic
accuracy across 12 categories. It's deployed on Render, with a workaround
for read-only secret mounts that writes refreshed tokens to /tmp/token.json.
"""

task_a = Task(
    description=(
        "List every factual claim in the blog post below. For each one, state whether it is "
        "directly supported by the technical analysis (cite which point number) or whether "
        "it is unsupported / invented — including cases where a number or detail has been "
        "subtly changed from the source. Finish with a verdict: PASS if all claims are sourced, "
        "or FLAGGED if any are not, listing exactly which claims failed.\n\n"
        f"TECHNICAL ANALYSIS:\n{ANALYSIS_A}\n\nBLOG POST TO CHECK:\n{BLOG_A}"
    ),
    expected_output=(
        "A verification report listing each claim with supported/unsupported status, "
        "followed by a final PASS or FLAGGED verdict."
    ),
    agent=fact_checker,
)

# ---------------------------------------------------------------------
# TEST B setup: same blunt fabrication as before, run 3x for consistency
# ---------------------------------------------------------------------
ANALYSIS_B = """
TECHNICAL ANALYSIS (ground truth)

1. What the project does: A CLI tool that fetches a GitHub repo's README
   and generates a short blog post about it.
2. Tech stack: Python, CrewAI, Groq (llama-3.3-70b-versatile).
3. Limitation: no caching layer — every run re-fetches from scratch.
"""

BLOG_B = """
# RepoBlogger

RepoBlogger turns any GitHub README into a blog post using CrewAI and
Groq. It includes built-in Redis caching, cutting repeat-run latency by
90%, and has processed over 50,000 repositories since launch.
"""


def make_task_b():
    # New Task object each run — CrewAI Task state shouldn't be reused across kickoffs
    return Task(
        description=(
            "List every factual claim in the blog post below. For each one, state whether it is "
            "directly supported by the technical analysis (cite which point number) or whether "
            "it is unsupported / invented. Finish with a verdict: PASS if all claims are sourced, "
            "or FLAGGED if any are not, listing exactly which claims failed.\n\n"
            f"TECHNICAL ANALYSIS:\n{ANALYSIS_B}\n\nBLOG POST TO CHECK:\n{BLOG_B}"
        ),
        expected_output=(
            "A verification report listing each claim with supported/unsupported status, "
            "followed by a final PASS or FLAGGED verdict."
        ),
        agent=fact_checker,
    )


def run_single(task, label):
    crew = Crew(agents=[fact_checker], tasks=[task], process=Process.sequential, verbose=False)
    result = str(crew.kickoff())
    verdict = "FLAGGED" if "FLAGGED" in result.upper() else ("PASS" if "PASS" in result.upper() else "UNCLEAR")
    print(f"\n--- {label} ---")
    print(result)
    print(f"[{label} verdict: {verdict}]")
    return verdict


if __name__ == "__main__":
    print("=" * 60)
    print("TEST A: Subtle number distortion (93%->99%, 9->12 categories)")
    print("=" * 60)
    verdict_a = run_single(task_a, "TEST A")

    print("\n" + "=" * 60)
    print("TEST B: Blunt fabrication, repeated 3x for consistency")
    print("=" * 60)
    verdicts_b = [run_single(make_task_b(), f"TEST B run {i+1}") for i in range(3)]

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Test A (subtle distortion) verdict : {verdict_a}")
    print(f"  -> Correct answer should be FLAGGED (99% and 12 categories are both wrong).")
    print(f"Test B (blunt, 3 runs) verdicts     : {verdicts_b}")
    print(f"  -> All 3 should be FLAGGED for the checker to be considered reliable.")
    print("=" * 60)
    if verdict_a != "FLAGGED":
        print("WARNING: fact_checker missed a subtle number distortion. It likely only")
        print("catches claims with NO textual overlap, not claims that misstate real numbers.")
    if len(set(verdicts_b)) > 1:
        print("WARNING: inconsistent verdicts across identical runs — fact_checker is not reliable,")
        print("it's probabilistic. Don't claim it as a dependable safeguard without caveats.")