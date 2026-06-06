import os
import sys
import asyncio
import readline
import glob
import re
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv
load_dotenv()

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

def c(text, code):
    return f"\033[{code}m{text}\033[0m"

async def thinking_animation():
    text = "AI is thinking"
    while True:
        sys.stdout.write("\r\033[K")
        for char in text:
            sys.stdout.write(c(char, "90"))
            sys.stdout.flush()
            await asyncio.sleep(0.05)
        for _ in range(3):
            sys.stdout.write(c(".", "90"))
            sys.stdout.flush()
            await asyncio.sleep(0.3)
        await asyncio.sleep(0.5)

@tool
def Read(file_path: str, start_line: Optional[int] = 1, end_line: Optional[int] = None) -> str:
    """Reads a file from the disk. You can optionally specify start and end lines."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if end_line is None:
                end_line = len(lines)
            content = "".join(lines[start_line-1:end_line])
            return content
    except Exception as e:
        return f"Error reading file {file_path}: {e}"

@tool
def Glob(pattern: str) -> List[str]:
    """Finds files matching a glob pattern."""
    try:
        return glob.glob(pattern, recursive=True)
    except Exception as e:
        return [f"Error running glob with pattern {pattern}: {e}"]

@tool
def Grep(pattern: str, file_pattern: str = "*") -> str:
    """Searches for a pattern in files matching file_pattern."""
    results = []
    try:
        files = glob.glob(file_pattern, recursive=True)
        regex = re.compile(pattern)
        for file_path in files:
            if os.path.isfile(file_path):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for i, line in enumerate(f, 1):
                        if regex.search(line):
                            results.append(f"{file_path}:{i}:{line.strip()}")
        return "\n".join(results) if results else "No matches found."
    except Exception as e:
        return f"Error running grep: {e}"

def print_header(user_query, model_name):
    title = f"LinkedIn Connection Finder ({model_name})"
    q_line = f"Query: \"{user_query}\""
    width = max(len(title), len(q_line)) + 4
    print(c(f"\n╭{'─' * width}╮", "90"))
    print(c(f"│  {title:<{width - 2}}│", "90"))
    print(c(f"│  {q_line:<{width - 2}}│", "90"))
    print(c(f"╰{'─' * width}╯", "90"))
    print()

class AgentManager:
    def __init__(self, model_choice: str):
        self.tools = [Read, Glob, Grep]
        self.memory = MemorySaver()
        self.config = {"configurable": {"thread_id": "1"}}
        
        if model_choice == "1":
            self.model_name = "Claude"
            self.llm = ChatAnthropic(model="claude-3-5-sonnet-latest", temperature=0)
        else:
            self.model_name = "Gemini"
            # Mid-2026 environment: using gemini-2.5-flash
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_CLOUD_API_KEY")
            self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0, google_api_key=api_key)
            
        self.agent = create_react_agent(self.llm, self.tools, checkpointer=self.memory)

    async def run_query(self, prompt: str):
        spinner = asyncio.create_task(thinking_animation())
        seen_text = False
        
        # Use astream_events to get granular updates
        async for event in self.agent.astream_events(
            {"messages": [HumanMessage(content=prompt)]},
            self.config,
            version="v2"
        ):
            kind = event["event"]
            
            if kind == "on_chat_model_stream":
                if not spinner.done():
                    spinner.cancel()
                    sys.stdout.write("\r\033[K")
                    sys.stdout.flush()
                
                content = event["data"]["chunk"].content
                if content:
                    if isinstance(content, list):
                        # Some models return list of content blocks
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                print(block["text"], end="", flush=True)
                    else:
                        print(content, end="", flush=True)
                    seen_text = True

            elif kind == "on_tool_start":
                if not spinner.done():
                    spinner.cancel()
                    sys.stdout.write("\r\033[K")
                    sys.stdout.flush()
                
                tool_name = event["name"]
                tool_input = event["data"].get("input", {})
                print(f"\n  → {c(tool_name, '36')} ({tool_input})", flush=True)
                
            elif kind == "on_tool_end":
                pass # Optionally print tool output length

        if not spinner.done():
            spinner.cancel()
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()
            
        print(f"\n\n{c('✓', '32')} Done")

async def run():
    print(c("Choose your AI model:", "1"))
    print(f"  {c('[1]', '33')} Anthropic Claude (3.5 Sonnet)")
    print(f"  {c('[2]', '33')} Google Gemini (1.5 Flash)")
    
    choice = input(f"{c('>', '36')} ").strip()
    if choice not in ["1", "2"]:
        print("Invalid choice. Defaulting to Gemini.")
        choice = "2"
    
    manager = AgentManager(choice)

    if len(sys.argv) > 1:
        user_query = " ".join(sys.argv[1:])
    else:
        user_query = input("\nWhat are you looking for? (e.g., 'customers for my AI SaaS product'): ").strip()
        if not user_query:
            print("No query provided. Exiting.")
            return

    csv_path = os.path.abspath("Connections.csv")
    if not os.path.exists(csv_path):
        # Fallback to sample if real one doesn't exist for testing
        csv_path = os.path.abspath("Connections_Sample.csv")

    about_dir = os.path.abspath("about")

    with open(csv_path, "r") as f:
        lines = f.readlines()
        # LinkedIn CSVs often have 3 lines of notes at the top
        csv_content = "".join(lines[:1000])

    print_header(user_query, manager.model_name)

    prompt = f"""Here is a LinkedIn connections export CSV (first 3 lines are notes, data starts at line 4 with headers: First Name, Last Name, URL, Email Address, Company, Position, Connected On):

---
{csv_content}
---

USER'S REQUEST: {user_query}

Based on the user's request, identify the TOP 10 most relevant people from this CSV data. Do NOT use the Read tool to read the CSV — the data is already provided above.

Present your findings naturally — for each person, share their name, company, position, their LinkedIn URL, and why they're relevant. Always include the LinkedIn URL. Keep it concise."""

    await manager.run_query(prompt)

    while True:
        print()
        print(f"  {c('[1]', '33')} Show more people")
        print(f"  {c('[2]', '33')} Give personalised conversation starters")
        print(f"  {c('[q]', '90')} Quit")
        print(f"  {c('or type anything to ask', '90')}")
        print()
        try:
            choice_input = input(f"{c('>', '36')} ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not choice_input or choice_input.lower() in ("quit", "exit", "q"):
            break

        if choice_input == "1":
            await manager.run_query(
                "Show more relevant people from the CSV beyond the ones you already listed. Give the next 10. Same format as before."
            )
        elif choice_input == "2":
            await manager.run_query(
                f"""For each person you already listed, do the following:
1. Extract their LinkedIn username — it's the last path segment of their URL (e.g. "https://www.linkedin.com/in/johndoe" → "johndoe")
2. Use the Read tool to read "{about_dir}/<username>.md" — substituting the actual username
3. If the file doesn't exist, skip that person

Based on the profile content, write a personalised conversation starter — something specific to their background, recent work, or interests that would make a warm opener. Be specific, not generic. Skip anyone whose profile file is missing."""
            )
        else:
            await manager.run_query(choice_input)

    print(f"\n{c('Goodbye!', '90')}")

if __name__ == "__main__":
    asyncio.run(run())
