import os
import time
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import SerperDevTool

import crewai.llms.cache as _crewai_cache
_crewai_cache.mark_cache_breakpoint = lambda msg: msg

load_dotenv()

llm = LLM(
    model="groq/llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0
)

search_tool = SerperDevTool()

researcher = Agent(
    role="Research Analyst",
    goal="Find key facts and angles on a given topic using real-time web search",
    backstory="You are a meticulous researcher who gathers accurate, up-to-date information from the web before any content is written. You always verify facts using search rather than relying on memory.",
    tools=[search_tool],
    llm=llm,
    verbose=True
)

writer = Agent(
    role="Content Writer",
    goal="Write a clear, engaging blog post based on research",
    backstory="You are a skilled writer who turns research into a well-structured, readable blog post. You always use the specific facts, numbers, and source URLs provided by the researcher — never placeholder citations.",
    llm=llm,
    verbose=True
)

topic = "How small businesses can use AI agents to automate customer support"

research_task = Task(
    description=f"""Search the web on this topic: {topic}

    You MUST run at least 3 searches:
    Search 1: recent statistics about AI replacing software engineering jobs
    Search 2: specific companies using agentic AI for coding in 2024-2025
    Search 3: expert reports or predictions about software engineers and agentic AI

    For every point you write, include the EXACT source URL from the search results (not just the name).
    Format each point as: Fact — Source Name (full URL)
    Do not write anything without a specific fact, source name, AND URL behind it.""",
    expected_output="A list of 5 key points, each with a fact, source name, and the exact source URL.",
    agent=researcher
)

write_task = Task(
    description=f"""Using the research, write a 400-word blog post on: {topic}

    Use the specific facts and sources from the research. Make it engaging with a clear intro, body, and conclusion.

    CRITICAL: Every citation must be a real markdown link using the exact URL provided by the researcher.
    Format: [Source Name](https://actual-url-from-research)
    Do NOT write fake anchors like [¹](#sourcename). Do NOT omit URLs. If a URL is missing for a fact, drop that fact instead of citing it without a link.

    Important: If multiple items (e.g., company names) all come from the SAME source/URL, cite that source only ONCE for the whole sentence — do not repeat the same link 3-4 times for each item.""",
    expected_output="A complete 400-word blog post in markdown format with real clickable source links, not placeholder anchors, and no repeated/stuffed citations.",
    agent=writer,
    context=[research_task]
)

crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, write_task],
    process=Process.sequential,
    verbose=True
)

max_attempts = 3
result = None
for attempt in range(1, max_attempts + 1):
    try:
        result = crew.kickoff()
        break
    except Exception as e:
        print(f"\n⚠️  Attempt {attempt} failed: {e}")
        if attempt < max_attempts:
            print("Retrying in 5 seconds...\n")
            time.sleep(5)
        else:
            print("\n❌ All attempts failed.")
            raise

print("\n\n=== FINAL BLOG POST ===\n")
print(result)