import os
import re
import argparse
from datetime import datetime

import requests
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM

import crewai.llms.cache as _crewai_cache
_crewai_cache.mark_cache_breakpoint = lambda msg: msg

load_dotenv()

llm = LLM(
    model="groq/llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY")
)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # optional, but strongly recommended (60/hr -> 5000/hr)


def parse_repo(repo_arg: str) -> str:
    """Accepts 'owner/repo' or a full GitHub URL, returns 'owner/repo'."""
    repo_arg = repo_arg.strip().rstrip("/")
    match = re.search(r"github\.com/([^/]+/[^/]+)", repo_arg)
    if match:
        return match.group(1).replace(".git", "")
    if "/" in repo_arg:
        return repo_arg
    raise ValueError(f"Could not parse a valid owner/repo from: {repo_arg}")


def fetch_repo_data(owner_repo: str) -> dict:
    """Fetches README content + basic repo metadata from GitHub API."""
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    meta_resp = requests.get(f"https://api.github.com/repos/{owner_repo}", headers=headers)
    if meta_resp.status_code == 403:
        raise RuntimeError(
            "GitHub API rate limit hit (60/hr without a token). "
            "Set GITHUB_TOKEN in .env to raise this to 5000/hr."
        )
    if meta_resp.status_code == 404:
        raise RuntimeError(f"Repo '{owner_repo}' not found or is private.")
    meta_resp.raise_for_status()
    meta = meta_resp.json()

    readme_headers = dict(headers)
    readme_headers["Accept"] = "application/vnd.github.raw+json"
    readme_resp = requests.get(f"https://api.github.com/repos/{owner_repo}/readme", headers=readme_headers)
    readme_text = readme_resp.text if readme_resp.status_code == 200 else ""

    if not readme_text:
        raise RuntimeError(f"No README found for '{owner_repo}' — nothing to summarize.")

    return {
        "name": meta.get("name", owner_repo),
        "description": meta.get("description") or "",
        "language": meta.get("language") or "",
        "topics": meta.get("topics", []),
        "stars": meta.get("stargazers_count", 0),
        "readme": readme_text[:6000],  # cap to keep prompt size reasonable
    }


# ---- Agents ----

analyst = Agent(
    role="Technical Analyst",
    goal="Extract the real, verifiable technical substance of a GitHub project from its README — "
         "what it does, what problem it solves, what stack it uses, and what's genuinely notable about it",
    backstory="You are a careful technical reviewer. You only report what is explicitly stated in the "
              "README and repo metadata provided to you. You never invent features, numbers, or claims "
              "that aren't in the source material. If the README is vague about something, you say so "
              "rather than filling in a guess.",
    llm=llm,
    verbose=True
)

writer = Agent(
    role="Content Writer",
    goal="Turn the technical analysis into an engaging blog post for a developer audience",
    backstory="You are a skilled technical writer. You take the analyst's verified points and turn them "
              "into a clear, engaging blog post. You never add claims the analyst didn't provide.",
    llm=llm,
    verbose=True
)

fact_checker = Agent(
    role="Fact Checker",
    goal="Verify every claim in the blog post traces back to the technical analysis or the original README",
    backstory="You are a strict editor. You compare the blog post line by line against the analyst's "
              "report and the raw README. Any claim not traceable to the source material gets flagged. "
              "You never let an invented feature or number pass silently.",
    llm=llm,
    verbose=True
)


def build_tasks(repo_data: dict):
    source_block = f"""
Repo name: {repo_data['name']}
Description: {repo_data['description']}
Primary language: {repo_data['language']}
Topics: {', '.join(repo_data['topics']) if repo_data['topics'] else 'none listed'}
Stars: {repo_data['stars']}

README content:
{repo_data['readme']}
"""

    analysis_task = Task(
        description=f"""Analyze this GitHub repository using ONLY the information below. Do not search
the web or use outside knowledge about the project — work strictly from this source material.

{source_block}

Extract:
1. What the project does (in plain terms)
2. What problem it solves and for whom
3. The tech stack, with each piece attributed to where it appears in the README
4. One genuinely notable technical detail (a real design decision, bug fix, or architecture choice
   mentioned in the README) — not a generic summary
5. Any limitations the README itself admits to""",
        expected_output="A structured technical analysis with the 5 points above, each one directly "
                        "traceable to a specific part of the README or metadata provided.",
        agent=analyst
    )

    write_task = Task(
        description="Using the technical analysis, write a 350-word blog post introducing this project "
                    "to a developer audience. Use only the facts from the analysis — do not add features, "
                    "numbers, or claims that weren't in it. Include the notable technical detail as a "
                    "highlight, and mention the limitation honestly rather than omitting it.",
        expected_output="A complete ~350-word blog post in markdown format, using only facts from the "
                        "technical analysis, including the standout detail and an honest limitation.",
        agent=writer,
        context=[analysis_task]
    )

    check_task = Task(
        description="List every factual claim in the blog post. For each one, state whether it is "
                    "directly supported by the technical analysis / README (cite which part) or whether "
                    "it is unsupported / invented. Finish with a verdict: PASS if all claims are sourced, "
                    "or FLAGGED if any are not, listing exactly which claims failed.",
        expected_output="A verification report listing each claim with supported/unsupported status, "
                        "followed by a final PASS or FLAGGED verdict.",
        agent=fact_checker,
        context=[analysis_task, write_task]
    )

    return [analysis_task, write_task, check_task]


def build_revision_task(analysis_task, write_task, check_task):
    """Only run this if check_task's verdict was FLAGGED. Sends the
    fact-checker's specific failed claims back to the writer to fix."""
    return Task(
        description="The fact-checker FLAGGED some claims in your blog post as unsupported. Rewrite the "
                    "blog post, removing or correcting exactly the claims the fact-checker listed as "
                    "unsupported. Keep everything else the same. Do not introduce any new claims that "
                    "aren't in the technical analysis.",
        expected_output="A revised ~350-word blog post in markdown format with the flagged claims "
                        "removed or corrected, and no new unsupported claims added.",
        agent=writer,
        context=[analysis_task, write_task, check_task]
    )


def generate_blog_post(owner_repo: str, log=print) -> dict:
    """Core pipeline, reusable from CLI or a web app. Returns a dict with
    keys: blog_post, check_report, flagged, repo_data, filename."""
    owner_repo = parse_repo(owner_repo)
    log(f"Fetching README + metadata for {owner_repo}...")
    repo_data = fetch_repo_data(owner_repo)
    log(f"Fetched. README length: {len(repo_data['readme'])} chars.")

    tasks = build_tasks(repo_data)
    crew = Crew(
        agents=[analyst, writer, fact_checker],
        tasks=tasks,
        process=Process.sequential,
        verbose=True
    )

    result = crew.kickoff()
    result_text = str(result)

    log("\n\n=== FINAL BLOG POST + FACT-CHECK REPORT ===\n")
    log(result_text)

    analysis_task, write_task, check_task = tasks

    # Gate on the fact-checker's verdict instead of saving blindly.
    # Look at the check_task's own output specifically (not the whole
    # crew result, which also contains the analysis and blog text and
    # could coincidentally contain the word "FLAGGED" elsewhere).
    check_output = str(check_task.output).upper() if check_task.output else result_text.upper()
    flagged = "FLAGGED" in check_output

    # crew.kickoff() only returns the LAST task's output (the fact-check
    # report), not the blog post itself. Build the saved file from the
    # actual blog post (write_task.output) plus the fact-check report,
    # so the output file always contains the post, not just the report.
    blog_post_text = str(write_task.output) if write_task.output else ""
    check_report_text = str(check_task.output) if check_task.output else result_text

    if flagged:
        log("\n⚠️  Fact-check FLAGGED unsupported claims — sending back to writer for revision...")

        revision_task = build_revision_task(analysis_task, write_task, check_task)
        recheck_task = Task(
            description="List every factual claim in the REVISED blog post. For each one, state whether "
                        "it is directly supported by the technical analysis / README (cite which part) or "
                        "whether it is unsupported / invented. Finish with a verdict: PASS if all claims "
                        "are sourced, or FLAGGED if any are not, listing exactly which claims failed.",
            expected_output="A verification report listing each claim with supported/unsupported status, "
                            "followed by a final PASS or FLAGGED verdict.",
            agent=fact_checker,
            context=[analysis_task, revision_task]
        )

        revision_crew = Crew(
            agents=[writer, fact_checker],
            tasks=[revision_task, recheck_task],
            process=Process.sequential,
            verbose=True
        )
        revision_result = revision_crew.kickoff()

        recheck_output = str(recheck_task.output).upper() if recheck_task.output else str(revision_result).upper()
        still_flagged = "FLAGGED" in recheck_output

        log("\n\n=== REVISED BLOG POST + RE-CHECK REPORT ===\n")
        log(str(revision_result))

        if still_flagged:
            log("\n⚠️  Still FLAGGED after one revision attempt — needs manual review.")
            flagged = True
        else:
            log("\n✅ Revision fixed the flagged claims — fact-check now PASSES.")
            flagged = False

        # After revision, the blog post is revision_task's output, and
        # the fact-check report is recheck_task's output.
        blog_post_text = str(revision_task.output) if revision_task.output else ""
        check_report_text = str(recheck_task.output) if recheck_task.output else str(revision_result)
    else:
        log("\n✅ Fact-check PASSED — all claims traced to source material.")

    result_text = (
        "# Blog Post\n\n" + blog_post_text +
        "\n\n---\n\n# Fact-Check Report\n\n" + check_report_text
    )

    os.makedirs("output", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = repo_data["name"].replace("/", "_")
    suffix = "_FLAGGED" if flagged else ""
    filename = f"output/{safe_name}_{timestamp}{suffix}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(result_text)

    log(f"\nSaved to {filename}")

    return {
        "owner_repo": owner_repo,
        "repo_data": repo_data,
        "blog_post": blog_post_text,
        "check_report": check_report_text,
        "flagged": flagged,
        "full_markdown": result_text,
        "filename": filename,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate a fact-checked blog post from a GitHub repo's README")
    parser.add_argument("--repo", type=str, required=True,
                        help="GitHub repo as 'owner/repo' or a full URL")
    args = parser.parse_args()
    generate_blog_post(args.repo)


if __name__ == "__main__":
    main()