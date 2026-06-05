import os
import sys
import asyncio
import readline
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage


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


def flush_pending_tool(pending):
    if not pending:
        return
    name = pending["name"]
    count = pending["count"]
    files = pending["files"]

    label = c(name, "36")
    if count > 1:
        label += c(f" x{count}", "33")

    if files:
        details = ", ".join(
            f"{os.path.basename(f[0])} · {f[1]} lines" for f in files[:5]
        )
        if len(files) > 5:
            details += f", +{len(files) - 5} more"
        print(f"  → {label} ({details})", flush=True)
    else:
        print(f"  → {label}", flush=True)


def print_header(user_query):
    title = "LinkedIn Connection Finder"
    q_line = f"Query: \"{user_query}\""
    width = max(len(title), len(q_line)) + 4
    print(c(f"\n╭{'─' * width}╮", "90"))
    print(c(f"│  {title:<{width - 2}}│", "90"))
    print(c(f"│  {q_line:<{width - 2}}│", "90"))
    print(c(f"╰{'─' * width}╯", "90"))
    print()


async def run_query(prompt, show_tools=True, continue_conversation=False):
    input_tokens = 0
    output_tokens = 0
    pending = None
    seen_text = False

    spinner = asyncio.create_task(thinking_animation())

    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            model="global.anthropic.claude-sonnet-4-6",
            allowed_tools=["Read", "Glob", "Grep"],
            permission_mode="bypassPermissions",
            continue_conversation=continue_conversation,
        ),
    ):
        if isinstance(message, AssistantMessage):
            if message.usage:
                input_tokens += getattr(message.usage, "input_tokens", 0) or 0
                output_tokens += getattr(message.usage, "output_tokens", 0) or 0

            for block in message.content:
                if hasattr(block, "text"):
                    if not spinner.done():
                        spinner.cancel()
                        sys.stdout.write("\r\033[K")
                        sys.stdout.flush()
                    if not seen_text and pending:
                        flush_pending_tool(pending)
                        pending = None
                        print()
                        seen_text = True
                    print(block.text, end="", flush=True)

                elif hasattr(block, "name") and show_tools:
                    if not spinner.done():
                        spinner.cancel()
                        sys.stdout.write("\r\033[K")
                        sys.stdout.flush()

                    tool_name = block.name
                    tool_input = getattr(block, "input", {})
                    file_path = tool_input.get("file_path", "")

                    if pending and pending["name"] == tool_name:
                        pending["count"] += 1
                        if file_path:
                            limit = tool_input.get("limit", 0)
                            pending["files"].append((file_path, limit or "?"))
                    else:
                        flush_pending_tool(pending)
                        pending = {"name": tool_name, "count": 1, "files": []}
                        if file_path:
                            limit = tool_input.get("limit", 0)
                            pending["files"].append((file_path, limit or "?"))

                elif hasattr(block, "tool_use_id") and pending:
                    content = getattr(block, "content", "")
                    if isinstance(content, str) and pending["files"]:
                        lines = content.count("\n")
                        idx = len(pending["files"]) - 1
                        path, _ = pending["files"][idx]
                        pending["files"][idx] = (path, lines)

        elif isinstance(message, ResultMessage):
            if not spinner.done():
                spinner.cancel()
                sys.stdout.write("\r\033[K")
                sys.stdout.flush()
            flush_pending_tool(pending)
            pending = None
            print(f"\n\n{c('✓', '32')} Done ({message.subtype})")

    print(f"\n{c(f'--- Tokens: input={input_tokens:,} | output={output_tokens:,} | total={input_tokens + output_tokens:,} ---', '90')}")
    return input_tokens, output_tokens


async def run():
    if len(sys.argv) > 1:
        user_query = " ".join(sys.argv[1:])
    else:
        user_query = input("What are you looking for? (e.g., 'customers for my AI SaaS product', 'VCs who invest in fintech'): ").strip()
        if not user_query:
            print("No query provided. Exiting.")
            return

    csv_path = os.path.abspath("Connections.csv")
    about_dir = os.path.abspath("about")

    with open(csv_path, "r") as f:
        lines = f.readlines()
        csv_content = "".join(lines[:1000])

    print_header(user_query)

    prompt = f"""Here is a LinkedIn connections export CSV (first 3 lines are notes, data starts at line 4 with headers: First Name, Last Name, URL, Email Address, Company, Position, Connected On):

---
{csv_content}
---

USER'S REQUEST: {user_query}

Based on the user's request, identify the TOP 10 most relevant people from this CSV data. Do NOT use the Read tool — the data is already provided above.

Present your findings naturally — for each person, share their name, company, position, their LinkedIn URL, and why they're relevant. Always include the LinkedIn URL. Keep it concise."""

    await run_query(prompt)

    while True:
        print()
        print(f"  {c('[1]', '33')} Show more people")
        print(f"  {c('[2]', '33')} Give personalised conversation starters")
        print(f"  {c('[q]', '90')} Quit")
        print(f"  {c('or type anything to ask', '90')}")
        print()
        try:
            choice = input(f"{c('>', '36')} ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not choice or choice.lower() in ("quit", "exit", "q"):
            break

        if choice == "1":
            await run_query(
                "Show more relevant people from the CSV beyond the ones you already listed. Give the next 10. Same format as before.",
                continue_conversation=True,
            )
        elif choice == "2":
            await run_query(
                f"""For each person you already listed, do the following:
1. Extract their LinkedIn username — it's the last path segment of their URL (e.g. "https://www.linkedin.com/in/johndoe" → "johndoe")
2. Use the Read tool to read "{about_dir}/<username>.md" — substituting the actual username
3. If the file doesn't exist, skip that person

Based on the profile content, write a personalised conversation starter — something specific to their background, recent work, or interests that would make a warm opener. Be specific, not generic. Skip anyone whose profile file is missing.""",
                continue_conversation=True,
            )
        else:
            await run_query(choice, continue_conversation=True)

    print(f"\n{c('Goodbye!', '90')}")


if __name__ == "__main__":
    asyncio.run(run())
