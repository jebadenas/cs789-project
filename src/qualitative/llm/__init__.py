"""LLM journal-analysis strand — see docs/qualitative/llm-journal-analysis-plan.md.

Every model call goes through ``model.call_model`` so the backend (local Ollama
now; cluster vLLM or Gemini later) is a one-line swap and no pipeline logic
depends on it.
"""
