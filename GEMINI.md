# LinkedIn Connections Chat

This repository contains tools to search, research, and interact with your LinkedIn connections export. It leverages AI (Claude and Gemini) to provide an intelligent interface for finding and engaging with relevant people in your network.

## Project Structure

- `Connections_Sample.csv`: Example of the LinkedIn data format (Note: The scripts expect a file named `Connections.csv`).
- `search_connections.py`: Researches people in your connections list using Google Gemini and saves summaries to an `about/` directory.
- `read_expand.py`: An interactive CLI tool that allows you to query your connections and generate personalized conversation starters using Claude.
- `.env.example`: Template for required environment variables/API keys.

## Core Workflows

### 1. Research Connections (`search_connections.py`)
- Reads `Connections.csv`.
- Uses **Google Gemini 3.1 Flash-Lite** with **Google Search grounding** to find detailed professional info for each connection.
- Saves a Markdown summary for each person in `about/<linkedin_username>.md`.
- Features: Concurrency control, rate limiting, and duplicate detection.

### 2. Interactive Search & Engagement (`read_expand.py`)
- Provides a CLI "LinkedIn Connection Finder".
- Uses **LangChain** to support both **Anthropic Claude** and **Google Gemini** (interactive choice at startup).
- Uses custom tools (`Read`, `Glob`, `Grep`) to filter connections and pull in detailed summaries from the `about/` folder.
- Can generate **personalized conversation starters** based on the research data.

## Setup Requirements

- **API Keys**:
  - Vertex AI / Google Cloud credentials for Gemini.
  - Anthropic API Key for Claude.
- **Data**: A `Connections.csv` file exported from LinkedIn.
- **Python Dependencies**: `langchain`, `langchain-anthropic`, `langchain-google-genai`, `langgraph`, etc. (See `read_expand.py` for full list).

## Usage

1.  Place your LinkedIn export in the root as `Connections.csv`.
2.  Run `python search_connections.py` to populate the `about/` folder with detailed profile info.
3.  Run `python read_expand.py` to start the interactive search and engagement CLI.
