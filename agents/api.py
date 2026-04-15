"""Gemini API wrapper with key rotation, retry, and caching."""

import json
import time
import hashlib
import streamlit as st
from google import genai
from google.genai import types

# --- Key Management ---
def get_api_keys() -> list[str]:
    keys = []
    for i in range(1, 11):
        k = st.secrets.get(f"GEMINI_API_KEY_{i}", "")
        if k: keys.append(k)
    single = st.secrets.get("GEMINI_API_KEY", "")
    if single and single not in keys:
        keys.insert(0, single)
    return keys

_key_index = 0
def get_next_key() -> str:
    global _key_index
    keys = get_api_keys()
    if not keys:
        raise ValueError("No GEMINI_API_KEY in Streamlit secrets")
    key = keys[_key_index % len(keys)]
    _key_index += 1
    return key

# --- Agent Config ---
AGENT_CONFIGS = {
    "Intake Agent":             {"model": "gemini-2.5-flash", "temperature": 0.1},
    "Construct Agent":          {"model": "gemini-2.5-flash", "temperature": 0.1},
    "Subskill Agent":           {"model": "gemini-2.5-flash", "temperature": 0.2},
    "Content Scoping Agent":    {"model": "gemini-2.5-flash", "temperature": 0.1},
    "Custom Hess Matrix Agent": {"model": "gemini-2.5-flash", "temperature": 0.15},
    "Misconception Agent":      {"model": "gemini-2.5-flash", "temperature": 0.1},
    "Content Selector":         {"model": "gemini-2.5-flash", "temperature": 0.1},
    "Generation Agent":         {"model": "gemini-2.5-flash", "temperature": 0.4},
    "AI SME QA":                {"model": "gemini-2.5-flash", "temperature": 0.1},
    "Research Agent":           {"model": "gemini-2.5-flash", "temperature": 0.1},
}

# --- Cache ---
@st.cache_data(ttl=1800, show_spinner=False)
def _cached_generate(cache_key: str, agent_name: str, system_prompt: str, user_payload: str, schema_json: str | None) -> dict:
    return _raw_generate(agent_name, system_prompt, user_payload, schema_json)

def _raw_generate(agent_name: str, system_prompt: str, user_payload: str, schema_json: str | None) -> dict:
    config = AGENT_CONFIGS.get(agent_name, {"model": "gemini-2.5-flash", "temperature": 0.2})
    api_key = get_next_key()
    client = genai.Client(api_key=api_key)

    gen_config = {"temperature": config["temperature"]}
    if system_prompt:
        gen_config["system_instruction"] = system_prompt
    if schema_json:
        gen_config["response_mime_type"] = "application/json"
        gen_config["response_schema"] = json.loads(schema_json)

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=config["model"],
                contents=user_payload,
                config=gen_config,
            )
            if response.text:
                return json.loads(response.text)
            raise ValueError("Empty response")
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                time.sleep(2 ** (attempt + 1))
                api_key = get_next_key()
                client = genai.Client(api_key=api_key)
                continue
            raise

def generate_agent_response(agent_name: str, system_prompt: str, user_payload: str, schema: dict | None = None, cacheable: bool = True) -> dict:
    """Main API call — with optional caching."""
    schema_json = json.dumps(schema) if schema else None
    if cacheable:
        cache_key = hashlib.md5((system_prompt + user_payload + (schema_json or "")).encode()).hexdigest()
        return _cached_generate(cache_key, agent_name, system_prompt, user_payload, schema_json)
    return _raw_generate(agent_name, system_prompt, user_payload, schema_json)

def generate_with_search(agent_name: str, system_prompt: str, user_payload: str) -> str:
    """Grounded search — returns raw text."""
    config = AGENT_CONFIGS.get(agent_name, {"model": "gemini-2.5-flash", "temperature": 0.1})
    api_key = get_next_key()
    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=config["model"],
        contents=user_payload,
        config={
            "system_instruction": system_prompt,
            "temperature": config["temperature"],
            "tools": [types.Tool(google_search=types.GoogleSearch())],
        },
    )
    return response.text or ""
