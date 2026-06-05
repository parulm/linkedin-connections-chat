# LinkedIn Connections Chat

An AI-powered toolset to research your LinkedIn connections and engage with them intelligently using Claude and Gemini.

## Features

- **Automated Research**: Use Google Gemini with Search Grounding to generate professional summaries of your connections.
- **Interactive Search**: Query your network using natural language (e.g., "Find CTOs in my network").
- **Multi-Model Support**: Choose between **Anthropic Claude** and **Google Gemini** for your interactive sessions.
- **Personalized Starters**: Generate warm, context-aware conversation starters based on researched profile data.

## Getting Started

### 1. Prerequisites
- Python 3.9+
- A LinkedIn connections export (`Connections.csv`).

### 2. Installation

1. Clone the repository and navigate to the directory.
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install langchain langchain-anthropic langchain-google-genai langgraph python-dotenv google-genai
   ```

### 3. Configuration

1. Create a `.env` file from the template:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and add your API keys:
   - `ANTHROPIC_API_KEY`: Required for Claude models.
   - `GOOGLE_API_KEY`: Required for Gemini models in the interactive CLI.
   - `GOOGLE_CLOUD_API_KEY`: Required for the search grounding in the research script.

### 4. Usage

#### Step 1: Research your connections
Place your `Connections.csv` in the root folder and run the research script. This will create an `about/` directory with Markdown summaries for each person.
```bash
python search_connections.py
```

#### Step 2: Interactive Search & Engagement
Launch the interactive CLI to query your connections and generate conversation starters.
```bash
python read_expand.py
```
You will be prompted to choose between Claude and Gemini at startup.

## Project Structure

- `read_expand.py`: Interactive CLI using LangChain.
- `search_connections.py`: Research automation using Gemini + Google Search.
- `about/`: (Generated) Contains professional summaries for your connections.
- `GEMINI.md`: Internal technical documentation and architectural notes.
