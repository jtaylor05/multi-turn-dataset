from .llm_api import LLMAPI, MockAPI, OpenAIAPI, AlibabaAPI, AnthropicAPI, GoogleAPI, OllamaAPI

# =============================================================
# AI MODEL NAMES — Current as of June 2026
# Sources: Anthropic Docs, OpenAI Docs, Google AI Docs, Alibaba Cloud Docs
# =============================================================

# -------------------------------------------------------------
# ANTHROPIC — Claude Models
# Docs: https://platform.claude.com/docs/en/about-claude/models/overview
# -------------------------------------------------------------

# Current / Active
anthropic_current = [
    "claude-fable-5",             # Most capable widely released model (Mythos-class)
    "claude-mythos-5",            # Project Glasswing only (invitation-only)
    "claude-mythos-preview",      # Project Glasswing only (predecessor)
    "claude-opus-4-8",            # Most capable Opus-tier model
    "claude-opus-4-7",            # Previous Opus; still active
    "claude-opus-4-6",            # Active
    "claude-sonnet-4-6",          # Best speed/intelligence balance
    "claude-haiku-4-5",
    "claude-haiku-4-5-20251001",  # Fastest model; alias: claude-haiku-4-5
]

# Older / Deprecated (still sometimes accessible)
anthropic_deprecated = [
    "claude-opus-4-5",
    "claude-opus-4-5-20251101",
    "claude-sonnet-4-5",
    "claude-sonnet-4-5-20250929",
    "claude-opus-4-1",
    "claude-opus-4-1-20250805",   # Retires 2026-08-05
    "claude-opus-4-0",
    "claude-sonnet-4-0",
    "claude-3-7-sonnet-20250219",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-20240620",
    "claude-3-5-haiku-20241022",
    "claude-3-haiku-20240307",
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-2.1",
    "claude-2.0",
]

# -------------------------------------------------------------
# OPENAI — GPT, o-series, Codex, OSS, Embedding, Image, Audio
# Docs: https://platform.openai.com/docs/models
# -------------------------------------------------------------

# Current flagship / GPT-5 family
openai_gpt5_family = [
    "gpt-5.5",
    "gpt-5.5-2026-04-23",
    "gpt-5.4",
    "gpt-5.4-2026-03-05",
    "gpt-5.4-mini",
    "gpt-5.4-mini-2026-03-17",
    "gpt-5.4-nano",
    "gpt-5.4-nano-2026-03-17",
    "gpt-5.4-pro",
    "gpt-5.5-pro",
]

# GPT-4.x family
openai_gpt4_family = [
    "gpt-4.1",
    "gpt-4.1-2025-04-14",
    "gpt-4.1-mini",
    "gpt-4.1-mini-2025-04-14",
    "gpt-4.1-nano",
    "gpt-4.1-nano-2025-04-14",
    "gpt-4o",
    "gpt-4o-mini",
]

# o-series reasoning models
openai_o_series = [
    "o3",
    "o3-2025-04-16",
    "o3-pro",
    "o4-mini",
    "o4-mini-2025-04-16",
]

# Open-weight models (Apache 2.0)
openai_open_weight = [
    "gpt-oss-120b",
    "gpt-oss-20b",
]

# Image generation models
openai_image = [
    "gpt-image-1",
]

# Audio / speech models
openai_audio = [
    "gpt-4o-audio-preview",
    "gpt-4o-mini-audio-preview",
    "gpt-4o-transcribe",
    "gpt-4o-mini-transcribe",
    "gpt-4o-mini-tts",
    "whisper-1",
]

# Embedding models
openai_embeddings = [
    "text-embedding-3-large",
    "text-embedding-3-small",
    "text-embedding-ada-002",
]

# Moderation models
openai_moderation = [
    "omni-moderation-latest",
]

# Deprecated but recently available
openai_deprecated = [
    "gpt-5",
    "gpt-5-2025-08-07",
    "gpt-5-mini",
    "gpt-5.1",
    "gpt-5.2",
    "gpt-4.5-preview",
    "gpt-4.5-preview-2025-02-27",
    "o1",
    "o1-2024-12-17",
    "o1-mini",
    "o3-mini",
]

# -------------------------------------------------------------
# GOOGLE — Gemini Models
# Docs: https://ai.google.dev/gemini-api/docs/models
# -------------------------------------------------------------

# Gemini 3.x family (current frontier)
google_gemini_3x = [
    "gemini-3.5-flash",                     # GA — most intelligent Flash
    "gemini-3.1-pro-preview",               # Preview — strongest reasoning
    "gemini-3.1-pro-preview-customtools",   # Preview — better custom tool use
    "gemini-3.1-flash-lite",                # GA — cost/speed efficient
    "gemini-3-flash-preview",               # Preview
    "gemini-3.1-flash-image",               # GA — image gen ("Nano Banana 2")
    "gemini-3-pro-image",                   # GA — image gen ("Nano Banana Pro")
    "gemini-3.5-live-translate-preview",    # Preview — real-time speech translation
    "gemini-3.1-flash-live-preview",        # Preview — Live API / voice
    "gemini-3.1-flash-tts-preview",         # Preview — TTS
]

# Gemini 2.5 family
google_gemini_25 = [
    "gemini-2.5-pro",                              # Most advanced stable model
    "gemini-2.5-flash",                            # Fast + capable
    "gemini-2.5-flash-lite",                       # Fastest / cheapest
    "gemini-2.5-flash-image",                      # Image gen ("Nano Banana")
    "gemini-2.5-flash-native-audio-preview-12-2025",  # Live API / native audio
    "gemini-2.5-flash-preview-tts",                # TTS
    "gemini-2.5-pro-preview-tts",                  # High-fidelity TTS
]

# Embedding models
google_embeddings = [
    "gemini-embedding-2",
    "text-embedding-004",
]

# Agentic / managed agents
google_agents = [
    "antigravity-preview-05-2026",
]

# Video generation (Veo)
google_video = [
    "veo-3.1-generate-preview",
    "veo-3.1-fast-generate-preview",
]

# Music generation (Lyria)
google_music = [
    "lyria-3",
    "lyria-realtime",
]

# Open models (Gemma)
google_gemma = [
    "gemma-4",
    "gemma-3n",
    "gemma-3",
]

# -------------------------------------------------------------
# QWEN (Alibaba Cloud / DashScope)
# Docs: https://www.alibabacloud.com/help/en/model-studio/models
# -------------------------------------------------------------

# Flagship API models (proprietary, via DashScope)
qwen_flagship = [
    "qwen3-max",
    "qwen3.5-plus",
    "qwen3.5-flash",
    "qwen3.6-plus",       # Proprietary; limited availability
    "qwen3.7-max",        # Preview
    "qwen3.7-plus",       # Preview
    "qwen-plus",
    "qwen-flash",
    "qwen-turbo",         # Legacy; replaced by qwen-flash
]

# Open-weight Qwen3 dense models (Apache 2.0)
qwen3_open_dense = [
    "Qwen3-0.6B",
    "Qwen3-1.7B",
    "Qwen3-4B",
    "Qwen3-8B",
    "Qwen3-14B",
    "Qwen3-32B",
    # Instruct / Thinking snapshots
    "Qwen3-Instruct-2507",
    "Qwen3-Thinking-2507",
]

# Open-weight Qwen3 MoE models
qwen3_open_moe = [
    "Qwen3-30B-A3B",
    "Qwen3-235B-A22B",
    "Qwen3-235B-A22B-Instruct-2507",
    "Qwen3-235B-A22B-Thinking-2507",
    "Qwen3-30B-A3B-Instruct-2507",
    "Qwen3-30B-A3B-Thinking-2507",
    "Qwen3-next-80B-A3B-Thinking",  # Sep 2025 update; thinking-only
    "Qwen3-next-80B-A3B-Instruct",  # Sep 2025 update; non-thinking
]

# Qwen3.5 / Qwen3.6 open-weight
qwen35_36_open = [
    "Qwen3.5-9B",
    "Qwen3.5-27B",
    "Qwen3.5-32B",
    "Qwen3.5-72B",
    "Qwen3.5-30B-A3B",       # MoE
    "Qwen3.5-397B-A17B",     # Large MoE (API only)
    "Qwen3.6-27B",           # Dense
    "Qwen3.6-35B-A3B",       # MoE (Apache 2.0)
]

# Qwen Coder models
qwen_coder = [
    "Qwen3-Coder-480B-A35B",  # State-of-the-art open coding model
    "Qwen3-Coder-Next",       # 80B-A3B, 256K context (alias)
    "Qwen2.5-Coder-7B-Instruct",
    "Qwen2.5-Coder-32B-Instruct",
    "qwen3-coder-plus",       # API alias (DashScope)
]

# Qwen VL (Vision-Language) models
qwen_vl = [
    "qwen3-vl-plus",
    "qwen3-vl-flash",
    "Qwen3-VL-Flash-2026-01-22",
    "Qwen2.5-VL-3B-Instruct",
    "Qwen2.5-VL-7B-Instruct",
    "Qwen2.5-VL-32B-Instruct",
    "Qwen2.5-VL-72B-Instruct",
    "qwen-vl-max",
    "qwen-vl-plus",
]

# Qwen2.5 open-weight base (still widely used)
qwen25_open = [
    "Qwen2.5-0.5B",
    "Qwen2.5-1.5B",
    "Qwen2.5-3B",
    "Qwen2.5-7B",
    "Qwen2.5-14B",
    "Qwen2.5-32B",
    "Qwen2.5-72B",
    "Qwen2.5-Max",   # Proprietary API variant
]

# Embedding / other Qwen models
qwen_other = [
    "text-embedding-v3",  # Qwen embedding via DashScope
    "qwen-mt-turbo",      # Machine translation model
]

ollama = [
    "gemma4",
    "gemma4:31b",
    "gemma4:26b",
    "gemma4:12b"
]

mock = [
    "mock-llm",
    "mock-llm-fail",
    "mock-llm-delay",
    "mock-llm-error"
]

def get_mock_api(model_name : str) -> MockAPI:
    if model_name == "mock-llm":
        return MockAPI(model=model_name, chance_of_error=0.0, chance_of_delay=0.0, chance_of_failure=0.0)
    elif model_name == "mock-llm-fail":
        return MockAPI(model=model_name, chance_of_error=0.0, chance_of_delay=0.0, chance_of_failure=1.0)
    elif model_name == "mock-llm-delay":
        return MockAPI(model=model_name, chance_of_error=0.0, chance_of_delay=1.0, chance_of_failure=0.0)
    elif model_name == "mock-llm-error":
        return MockAPI(model=model_name, chance_of_error=1.0, chance_of_delay=0.0, chance_of_failure=0.0)
    else:
        raise ValueError(f"Unknown mock model name: {model_name}.")

def get_ollama_api(model_name : str) -> OllamaAPI:
    url = "http://ollama-server-danielrc:11434"
    if model_name in ["gemma4", "gemma4:31b"]:
        return OllamaAPI(model="gemma4:31b", base_url=url, timeout=300)
    else:
        return OllamaAPI(model=model_name, base_url=url, timeout=300)

def get_api(model_name : str) -> LLMAPI:
    if model_name in anthropic_current:
        return AnthropicAPI(model=model_name)
    if model_name in openai_gpt5_family + openai_gpt4_family + openai_o_series:
        return OpenAIAPI(model=model_name)
    if model_name in google_gemini_25:
        return GoogleAPI(model=model_name)
    if model_name in qwen_flagship:
        return AlibabaAPI(model=model_name)
    if model_name in mock:
        return get_mock_api(model_name)
    if model_name in ollama:
        return get_ollama_api(model_name)
    raise ValueError(f"There exists no valid model with name {model_name}")