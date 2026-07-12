# 🤖 Repo Blog Agent

A multi-agent AI pipeline that fetches a GitHub repository's README and metadata, then generates a fact-checked blog post introducing the project — fully automated.

## What It Does

Three AI agents work sequentially:

1. **Technical Analyst** — Reads the repo's README, description, and metadata (fetched live via the GitHub API). Extracts what the project does, its tech stack, a notable technical detail, and any limitations — using only the source material, no outside knowledge.
2. **Content Writer** — Takes the analysis and writes a ~350-word blog post introducing the project to a developer audience, using only facts from the analysis.
3. **Fact Checker** — Cross-checks every claim in the blog post against the technical analysis and README. Flags anything invented, unsupported, or altered (including subtly changed numbers), and returns a PASS/FLAGGED verdict.

No hallucinated facts. The fact-checker has been stress-tested against fabricated claims (invented features, invented stats, and subtly altered numbers) and consistently catches them — see `test_fact_checker.py` and `test_fact_checker_extended.py`.

## Tech Stack

- [CrewAI](https://github.com/crewAIInc/crewAI) — multi-agent orchestration framework
- [Groq](https://groq.com/) — LLM inference (llama-3.3-70b-versatile)
- GitHub REST API — live repo metadata and README fetching
- Python 3.11

## Project Structure

```
crew-blog-agent/
├── repo_blog_agent.py              # Main pipeline — fetches repo, runs 3-agent crew
├── test_fact_checker.py            # Stress test: blunt fabricated claims
├── test_fact_checker_extended.py   # Stress test: subtle number distortion + consistency
├── .env                             # API keys (not committed)
└── README.md
```

## Setup

**1. Clone and create virtual environment**
```
git clone https://github.com/anuragtiwari73219-byte/crew-blog-agent
cd crew-blog-agent
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # Mac/Linux
```

**2. Install dependencies**
```
pip install -r requirements.txt
```

**3. Add API keys**

Create a `.env` file:
```
GROQ_API_KEY=your_groq_key_here
GITHUB_TOKEN=your_github_token_here   # optional, but recommended (60/hr -> 5000/hr)
```
Get keys from:
- Groq: https://console.groq.com
- GitHub: https://github.com/settings/tokens

**4. Run**
```
python repo_blog_agent.py --repo owner/repo-name
```
Example:
```
python repo_blog_agent.py --repo anuragtiwari73219-byte/ai-email-triage-agent
```

## How It Works

```
--repo owner/repo-name
      ↓
Fetch README + metadata (GitHub API)
      ↓
Technical Analyst
  → Extracts: what it does, tech stack, notable detail, limitations
  → Strictly from README/metadata — no outside knowledge
      ↓
Content Writer
  → Writes ~350-word blog post using only the analyst's output
      ↓
Fact Checker
  → Lists every claim in the blog post
  → Marks each SUPPORTED (cites source) or UNSUPPORTED/INVENTED
  → Final verdict: PASS or FLAGGED
      ↓
Final blog post + verification report printed to terminal
```

## Fact-Checker Validation

Because a fact-checker that never flags anything isn't a real safeguard, it was stress-tested separately from the main pipeline:

- **`test_fact_checker.py`** — Feeds the checker a blog post with 3 blunt fabricated claims (invented user counts, invented features, a fabricated feature that directly contradicts a stated limitation). Result: all 3 caught, correctly FLAGGED.
- **`test_fact_checker_extended.py`** — Two further checks:
  - Subtle distortion: a real accuracy stat quietly changed (93%→99%, 9→12 categories). Result: caught, correctly FLAGGED.
  - Consistency: same fabricated-claims test run 3x. Result: FLAGGED all 3 times, same claims named each time.

This is a small sample (4 runs across 2 fabrication styles), not a comprehensive audit — but it confirms the fact-checker does real verification rather than rubber-stamping every post as PASS.

## Bugs Fixed During Development

**1. Groq rejects CrewAI's cache_breakpoint field**
CrewAI 1.14.x injects a `cache_breakpoint` property into system messages for Anthropic's prompt caching feature. Groq's API rejects this field with a 400 invalid_request_error.

Fix applied in `repo_blog_agent.py`:
```python
import crewai.llms.cache as _crewai_cache
_crewai_cache.mark_cache_breakpoint = lambda msg: msg
```
This monkey-patches the function to return the message unchanged, stripping the unsupported field before it reaches Groq's API. Tracked in CrewAI GitHub Issue #5886 (crewAIInc/crewAI#5886).

**2. Groq's llama-3.3-70b-versatile intermittently fails tool calls**
Known upstream Groq issue — the model occasionally returns a malformed function-call string instead of valid JSON, causing a `tool_use_failed` error. Intermittent (same prompt can succeed or fail across runs). Mitigated with `temperature=0` and a retry wrapper around `crew.kickoff()`.

**3. GitHub API description/README mismatches**
When a repo's GitHub description hasn't been updated to match its README (e.g. after a tech-stack migration), the analyst agent can pull stale/conflicting info. Worth double-checking the target repo's description is current before running.

## What I'd Add Next

- Save blog output + fact-check report to a `.md` file automatically
- Broaden fact-checker stress tests beyond number/feature fabrication (e.g. wrong attribution, misleading paraphrase)
- Batch mode — generate posts for multiple repos in one run