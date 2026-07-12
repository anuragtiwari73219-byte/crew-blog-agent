"""
Stress-test for the fact_checker agent in repo_blog_agent.py

Goal: check whether fact_checker actually catches invented claims,
or whether it rubber-stamps PASS regardless of content.

This does NOT run the full pipeline (no GitHub fetch, no analyst,
no writer). It directly builds a fake "analysis" and a fake "blog post"
containing 3 deliberately fabricated claims that do NOT appear anywhere
in the fake analysis, and asks fact_checker to verify them.

If fact_checker is working correctly -> verdict should be FLAGGED,
and it should name the fabricated claims.

If it says PASS -> the fact-checker is not doing real verification,
it's a rubber stamp. Do not put "fact-checking pipeline" on the resume
until this test passes.

Run:
    python test_fact_checker.py
"""

from crewai import Task, Crew, Process
from repo_blog_agent import fact_checker

# ---- Fake source material (this is the "ground truth") ----
FAKE_ANALYSIS = """
TECHNICAL ANALYSIS (ground truth for this test)

1. What the project does: A CLI tool that fetches a GitHub repo's README
   and metadata, then generates a short blog post about it.
2. Problem solved: Saves developers time writing intro blog posts for
   their own repos.
3. Tech stack: Python, CrewAI, Groq (llama-3.3-70b-versatile), GitHub REST API.
4. Notable technical detail: The pipeline uses a three-agent CrewAI chain
   (analyst -> writer -> fact_checker) where the fact_checker cross-checks
   the writer's output against the analyst's report before final output.
5. Limitation admitted in README: No caching layer, so repeated runs
   against the same repo re-fetch and re-generate everything from scratch.
"""

# ---- Fake blog post with 3 DELIBERATELY FABRICATED claims ----
# None of these three facts appear in FAKE_ANALYSIS above.
FAKE_BLOG_POST = """
# Introducing RepoBlogger: Instant Blog Posts From Any GitHub Repo

RepoBlogger is a slick new CLI tool that turns any GitHub README into a
polished blog post in seconds. Built in Python with CrewAI, it uses
Groq's blazing-fast llama-3.3-70b-versatile model to do the heavy lifting.

FABRICATED CLAIM 1: RepoBlogger has processed over 50,000 repositories
since its public launch last year.

FABRICATED CLAIM 2: The tool supports real-time collaborative editing,
letting multiple team members refine the generated blog post together
before publishing.

One genuinely nice touch is the three-agent pipeline: an analyst agent
reads the repo, a writer agent drafts the post, and a fact-checker agent
verifies every claim before anything ships.

FABRICATED CLAIM 3: RepoBlogger includes built-in Redis caching, cutting
repeat-run latency by 90%.

The one honest limitation: there's currently no caching layer at all, so
every run re-fetches and re-generates from scratch.
"""

stress_test_task = Task(
    description=(
        "List every factual claim in the blog post below. For each one, state whether it is "
        "directly supported by the technical analysis (cite which point number) or whether "
        "it is unsupported / invented. Finish with a verdict: PASS if all claims are sourced, "
        "or FLAGGED if any are not, listing exactly which claims failed.\n\n"
        f"TECHNICAL ANALYSIS:\n{FAKE_ANALYSIS}\n\n"
        f"BLOG POST TO CHECK:\n{FAKE_BLOG_POST}"
    ),
    expected_output=(
        "A verification report listing each claim with supported/unsupported status, "
        "followed by a final PASS or FLAGGED verdict."
    ),
    agent=fact_checker,
)

crew = Crew(
    agents=[fact_checker],
    tasks=[stress_test_task],
    process=Process.sequential,
    verbose=True,
)

if __name__ == "__main__":
    result = crew.kickoff()

    print("\n" + "=" * 60)
    print("STRESS TEST RESULT")
    print("=" * 60)
    print(result)

    text = str(result).upper()
    print("\n" + "=" * 60)
    if "FLAGGED" in text and "PASS" not in text.split("FLAGGED")[0][-50:]:
        print("VERDICT: fact_checker said FLAGGED — good, it's not a rubber stamp.")
        print("Now check: did it actually name all 3 fabricated claims, or just some?")
    elif "PASS" in text:
        print("VERDICT: fact_checker said PASS on a blog post with 3 fabricated claims.")
        print("This means the fact-checker is NOT working as a real verification step.")
        print("Do not claim 'fact-checking pipeline' on resume until this is fixed.")
    else:
        print("VERDICT: unclear output — read the full result above manually.")
    print("=" * 60)