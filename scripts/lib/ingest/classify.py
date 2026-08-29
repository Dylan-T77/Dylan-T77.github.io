"""Topic and entity keyword classification for ingested items."""

from __future__ import annotations

TOPICS = {
    "ai": [
        "artificial intelligence",
        "machine learning",
        " llm",
        " ai ",
        "openai",
        "anthropic",
        "gemini",
        "qwen",
        "llama",
        "claude",
        "model hardware",
        "agentic",
    ],
    "robotics": [
        "robot",
        "robotics",
        "drone",
        "autonomous",
        "humanoid",
        "lerobot",
        "robotic arm",
    ],
    "space": [
        "space",
        "nasa",
        "spacex",
        "rocket",
        "satellite",
        "orbit",
        "moon",
        "mars",
        "artemis",
    ],
    "cybersecurity": [
        "security",
        "cyber",
        "vulnerability",
        "exploit",
        "malware",
        "ransomware",
        "breach",
        "cve",
        "phishing",
        "zero-day",
    ],
    "semiconductors": [
        "cpu",
        "gpu",
        "processor",
        "chip",
        "semiconductor",
        "nvidia",
        "amd",
        "intel",
        "tsmc",
        "foundry",
        "wafer",
    ],
}

ENTITIES = {
    "anthropic": ["anthropic", "claude", "model hardware standard", " mhs "],
    "nvidia": ["nvidia", "geforce", "cuda", "jetson", "omniverse"],
    "tsmc": ["tsmc", "taiwan semiconductor"],
    "openai": ["openai", "chatgpt", "sora"],
    "model-hardware-standard": ["model hardware standard", " mhs ", "hardware standard"],
}


def classify_text(title: str, summary: str) -> tuple[list[str], list[str]]:
    hay = f" {title} {summary} ".lower()
    topics = [topic for topic, words in TOPICS.items() if any(word in hay for word in words)]
    entities = [entity for entity, words in ENTITIES.items() if any(word in hay for word in words)]
    return topics, entities
