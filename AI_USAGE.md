# AI Usage Declaration (AI_USAGE.md)

In compliance with Section 6 of the Crunch Week Problem Statement:

### 1. In-Product AI APIs & Models
- **Models / APIs Used**:
  - `gemini-1.5-flash` / Google Gemini API (or OpenAI GPT-4o-mini compatible fallback endpoint)
  - **Purpose**: Plain English and Hinglish Natural Language Processing (NLP) for unstructured room and venue booking requests (e.g. *"seminar hall kal shaam 6 baje, 2 ghante, 100 log, mic chahiye"*).
  - **Prompt Locations**: `src/services/aiParser.ts` and `server/prompts.py`.
  - **Decisions the LLM is NOT allowed to make**:
    - The LLM **never** decides whether a booking is valid or whether a room is free.
    - The LLM **never** modifies the master timetable directly.
    - All LLM outputs are strictly converted into strongly typed JSON proposals that pass through deterministic code-based constraint checkers (`validator.py` logic) before any state changes occur.
    - If the LLM API fails, times out, or runs out of credits, a full manual booking wizard is provided and functions seamlessly.

### 2. AI Tools Used During Development
- **Coding Assistant**: Antigravity AI (Google DeepMind Agentic Coding Assistant)
  - **Parts helped with**: Scaffolding project structure, modeling constraint satisfaction heuristics (MRV, forward-checking), crafting responsive Tailwind CSS layouts, and building the Hinglish/English parser regex & prompt templates.
