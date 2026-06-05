import csv
import os
import asyncio
from google import genai
from google.genai import types
from google.oauth2 import service_account

CONCURRENCY = 10
MAX_RETRIES = 5

credentials = service_account.Credentials.from_service_account_file(
    "sharp-leaf-451416-r4-d77b49e95f49.json",
    scopes=["https://www.googleapis.com/auth/cloud-platform"],
)

client = genai.Client(
    vertexai=True,
    project="sharp-leaf-451416-r4",
    location="global",
    credentials=credentials,
)

semaphore = asyncio.Semaphore(CONCURRENCY)


def get_username_from_url(url):
    return url.rstrip("/").split("/")[-1]


async def research_person(idx, first_name, last_name, company, position, url):
    username = get_username_from_url(url)

    prompt = f"""Search for "{first_name} {last_name}" who works at "{company}" as "{position}".
Their LinkedIn username is "{username}" from: {url}

Search for "{first_name} {last_name} {username}" and use the first relevant result. Cross-reference their name, company, and LinkedIn username to confirm it's the right person. Only include facts about THIS person.

If you cannot find detailed information, still provide whatever you can based on their name, company, position, and LinkedIn.

Otherwise return a concise professional summary in markdown:
# {first_name} {last_name}

## Professional Summary
(2-3 sentences)

## Current Role
(Company and position details)

## Background
(Previous roles, education)

## Notable Achievements
(Products, funding, awards, press mentions)

## Online Presence
- LinkedIn: {url}
(Other verified links)
"""

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)]
        ),
    ]

    grounding_tool = types.Tool(google_search=types.GoogleSearch())

    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        top_p=0.95,
        max_output_tokens=2048,
        tools=[grounding_tool],
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
        ],
    )

    async with semaphore:
        for attempt in range(MAX_RETRIES):
            try:
                response = await client.aio.models.generate_content(
                    model="gemini-3.1-flash-lite",
                    contents=contents,
                    config=generate_content_config,
                )
                usage = response.usage_metadata
                print(f"[{idx}] {first_name} {last_name} — input: {usage.prompt_token_count}, output: {usage.candidates_token_count}, total: {usage.total_token_count}")
                if response.candidates and response.candidates[0].grounding_metadata:
                    gm = response.candidates[0].grounding_metadata
                    if gm.web_search_queries:
                        print(f"[{idx}] Search queries: {gm.web_search_queries}")
                    if gm.grounding_chunks:
                        print(f"[{idx}] Sources ({len(gm.grounding_chunks)}):")
                        for chunk in gm.grounding_chunks[:5]:
                            if chunk.web:
                                print(f"       - {chunk.web.title}: {chunk.web.uri}")
                output_path = os.path.join("about", f"{username}.md")
                with open(output_path, "w", encoding="utf-8") as out:
                    out.write(response.text)
                print(f"[{idx}] Saved {output_path}")
                return username, response.text
            except Exception as e:
                if "429" in str(e) and attempt < MAX_RETRIES - 1:
                    wait = [60, 90, 120, 120, 120][attempt]
                    print(f"[{idx}] Rate limited, retrying in {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    print(f"[{idx}] Error researching {first_name} {last_name}: {e}")
                    return username, f"# {first_name} {last_name}\n\nError fetching information: {e}\n"


async def main():
    csv_path = "Connections.csv"
    about_dir = "about"
    os.makedirs(about_dir, exist_ok=True)

    with open(csv_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    data_lines = lines[3:]
    reader = csv.DictReader(data_lines)

    tasks = []
    for idx, row in enumerate(reader, 1):
        first_name = row["First Name"].strip()
        last_name = row["Last Name"].strip()
        url = row["URL"].strip()
        company = row.get("Company", "").strip()
        position = row.get("Position", "").strip()

        username = get_username_from_url(url)
        output_path = os.path.join(about_dir, f"{username}.md")

        if os.path.exists(output_path):
            print(f"[{idx}] Skipping {first_name} {last_name} (already exists)")
            continue

        tasks.append((idx, first_name, last_name, company, position, url))

    print(f"Processing {len(tasks)} profiles with {CONCURRENCY} concurrent requests...\n")

    results = await asyncio.gather(
        *[research_person(idx, fn, ln, co, pos, url) for idx, fn, ln, co, pos, url in tasks]
    )

    saved = 0
    for username, content in results:
        if content:
            output_path = os.path.join(about_dir, f"{username}.md")
            with open(output_path, "w", encoding="utf-8") as out:
                out.write(content)
            saved += 1

    print(f"\nDone! Saved {saved} profiles.")


if __name__ == "__main__":
    asyncio.run(main())
