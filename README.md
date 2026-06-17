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
- [Serper](https://serper.dev/) — real-time Google Search API
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

    pip install crewai crewai-tools

**3. Add API keys**

Create a .env file:

    GROQ_API_KEY=your_groq_key_here
    SERPER_API_KEY=your_serper_key_here

Get keys from:
- Groq: https://console.groq.com
- Serper: https://serper.dev (2500 free searches/month)

**4. Run**

    python blog_crew.py

## How It Works

    User sets topic
          ↓
    Research Analyst
      → Search 1: recent statistics
      → Search 2: companies using agentic AI
      → Search 3: expert reports
      → Output: 5 sourced key points
          ↓
    Content Writer
      → Takes research output as context
      → Writes 400-word blog post in markdown
          ↓
    Final blog post printed to terminal

## Bug Fixed During Development

CrewAI 1.14.x injects a cache_breakpoint property into system messages for Anthropic's prompt caching feature. Groq's API rejects this field with a 400 invalid_request_error.

Fix applied in blog_crew.py:

    import crewai.llms.cache as _crewai_cache
    _crewai_cache.mark_cache_breakpoint = lambda msg: msg

This monkey-patches the function to return the message unchanged, stripping the unsupported field before it reaches Groq's API. Tracked in CrewAI GitHub Issue #5886 (https://github.com/crewAIInc/crewAI/issues/5886).

## Example Output

Research output (sourced):
- 80% of engineers will need to upskill by 2027 — Carnegie Mellon University
- 92% of IT jobs will see high/moderate AI transformation — AI-Enabled ICT Workforce Consortium
- AI can now handle entire implementation workflows — Anthropic 2026 Agentic Coding Trends Report

Final blog post: markdown-formatted, ~400 words, with inline source links

## What I'd Add Next

- Save blog output to a .md file automatically
- Add a third agent: fact-checker that rejects unsourced claims
- Support for multiple topics via CLI argument (python blog_crew.py --topic "...")
- Switch to OpenAI or Claude when cache_breakpoint bug is patched upstream