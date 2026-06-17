import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import SerperDevTool

import crewai.llms.cache as _crewai_cache
_crewai_cache.mark_cache_breakpoint = lambda msg: msg

load_dotenv()

llm = LLM(
    model="groq/llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY")
)

search_tool = SerperDevTool()

researcher = Agent(
    role="Research Analyst",
    goal="Find specific, data-backed facts about the given topic using real-time web search",
    backstory="You are a meticulous researcher who never writes anything without a source. You always run multiple searches and only report specific facts, numbers, and named sources.",
    tools=[search_tool],
    llm=llm,
    verbose=True
)

writer = Agent(
    role="Content Writer",
    goal="Write a clear, engaging blog post based on research",
    backstory="You are a skilled writer who turns research into a well-structured, readable blog post. You always use the specific facts and sources provided by the researcher.",
    llm=llm,
    verbose=True
)

topic = "Why agentic AI is changing software engineering jobs"

research_task = Task(
    description=f"""Search the web on this topic: {topic}

    You MUST run at least 3 searches:
    Search 1: recent statistics about AI replacing software engineering jobs
    Search 2: specific companies using agentic AI for coding in 2024-2025
    Search 3: expert reports or predictions about software engineers and agentic AI

    For every point you write, mention WHERE you found it (source name).
    Do not write anything without a specific fact or source behind it.""",
    expected_output="5 key points. Each point must have: a specific fact or number, the source it came from, and 2 sentence explanation. No vague generic points allowed.",
    agent=researcher
)

write_task = Task(
    description=f"Using the research, write a 400-word blog post on: {topic}. Use the specific facts and sources from the research. Make it engaging with a clear intro, body, and conclusion.",
    expected_output="A complete 400-word blog post in markdown format that includes specific facts, numbers, and source mentions from the research.",
    agent=writer,
    context=[research_task]
)

crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, write_task],
    process=Process.sequential,
    verbose=True
)

result = crew.kickoff()

print("\n\n=== FINAL BLOG POST ===\n")
print(result)