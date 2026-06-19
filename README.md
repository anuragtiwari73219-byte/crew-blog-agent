# 🤖 CrewAI Blog Agent

A multi-agent AI pipeline that researches a topic using real-time web search and writes a data-backed blog post — fully automated.

## What It Does

Two AI agents work sequentially:

1. **Research Analyst** — Runs multiple Google searches using Serper API, finds real statistics, named sources, and current data
2. **Content Writer** — Takes the research and writes a structured, 400-word blog post in markdown format

No hallucinated facts. No generic filler. The researcher is forced to cite sources and find specific data points before the writer touches anything.

## Tech Stack

- [CrewAI](https://github.com/crewAIInc/crewAI) — multi-agent orchestration framework
- [Groq](https://groq.com/) — LLM inference (llama-3.3-70b-versatile)
- [Serper](https://serper.dev/) — real-time Google Search API (default)
- [Tavily](https://tavily.com/) — AI-optimized search API (optional)
- Python 3.11

## Project Structure

crew-blog-agent/

├── blog_crew.py      # Main pipeline — agents, tasks, crew definition

├── .env              # API keys (not committed)

└── README.md

## Setup

**1. Clone and create virtual environment**

git clone <your-repo-url>

cd crew-blog-agent

python -m venv venv

venv\Scripts\activate      # Windows

source venv/bin/activate   # Mac/Linux

**2. Install dependencies**

**3. Add API keys**

Create a .env file:

GROQ_API_KEY=your_groq_key_here

SERPER_API_KEY=your_serper_key_here

TAVILY_API_KEY=your_tavily_key_here   # required only when using Tavily

SEARCH_PROVIDER=serper                # 'serper' (default) or 'tavily'

Get keys from:

- Groq: https://console.groq.com
- Serper: https://serper.dev (2500 free searches/month)
- Tavily: https://app.tavily.com (1000 free API credits/month)

**4. Run**

## How It Works

User sets topic

↓

Research Analyst

→ Search 1: recent statistics

→ Search 2: companies using agentic AI

→ Search 3: expert reports

→ Output: 5 sourced key points with real URLs

↓

Content Writer

→ Takes research output as context

→ Writes 400-word blog post in markdown with real clickable citations

↓

Final blog post printed to terminal

## Bugs Fixed During Development

**1. Groq rejects CrewAI's cache_breakpoint field**
CrewAI 1.14.x injects a `cache_breakpoint` property into system messages for Anthropic's prompt caching feature. Groq's API rejects this field with a 400 invalid_request_error.

Fix applied in blog_crew.py:
```python
import crewai.llms.cache as _crewai_cache
_crewai_cache.mark_cache_breakpoint = lambda msg: msg
```
This monkey-patches the function to return the message unchanged, stripping the unsupported field before it reaches Groq's API. Tracked in CrewAI GitHub Issue #5886 (crewAIInc/crewAI#5886).

**2. Groq's llama-3.3-70b-versatile intermittently fails tool calls**
This is a known upstream Groq issue — the model occasionally returns a malformed function-call string instead of valid JSON, causing a `tool_use_failed` error. It's intermittent (same prompt can succeed or fail across runs). Mitigated with `temperature=0` and a 3-attempt automatic retry wrapper around `crew.kickoff()`.

**3. Fake citations**
Early versions had the writer agent invent placeholder citations like `[¹](#sourcename)` instead of real links. Fixed by forcing the researcher to capture exact URLs and the writer to use real markdown links — with a rule to avoid citing the same source multiple times in one paragraph.

## Example Output

Research output (sourced):
- 92% of IT jobs will see high/moderate transformation due to AI — [CIO](https://www.cio.com/article/3485322/92-of-it-jobs-will-be-transformed-by-ai.html)
- By 2027, 80% of engineers will need to upskill due to GenAI — [CMU Bootcamps](https://bootcamps.cs.cmu.edu/blog/will-ai-replace-software-engineers-reality-check)
- Agentic AI treats AI as an active participant in development, not just a coding tool — [David Lozzi](https://davidlozzi.com/2025/08/20/the-reality-behind-the-buzz-the-current-state-of-agentic-engineering-in-2025/)

Final blog post: markdown-formatted, ~400 words, with real clickable source links (no fake citations, no repeated links)

## What I'd Add Next

- Save blog output to a .md file automatically
- Add a third agent: fact-checker that rejects unsourced or low-credibility (forum/social media) sources
- Support for multiple topics via CLI argument (`python blog_crew.py --topic "..."`)
- Switch to OpenAI or Claude when cache_breakpoint bug is patched upstream