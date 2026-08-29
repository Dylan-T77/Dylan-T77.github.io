"""Sector taxonomy for information classification."""

from __future__ import annotations

# sector_id -> keyword list (match in title + summary)
SECTORS: dict[str, list[str]] = {
    "ai": [
        "artificial intelligence", "machine learning", " llm", " ai ", "openai",
        "anthropic", "gemini", "qwen", "llama", "claude", "agentic", "gpt",
        "foundation model", "neural", "deep learning",
    ],
    "semiconductors": [
        "cpu", "gpu", "processor", "chip", "semiconductor", "nvidia", "amd",
        "intel", "tsmc", "foundry", "wafer", "fab ", " lithography", "asml",
    ],
    "robotics": [
        "robot", "robotics", "drone", "autonomous", "humanoid", "lerobot",
        "robotic arm", "warehouse automation",
    ],
    "cybersecurity": [
        "security", "cyber", "vulnerability", "exploit", "malware", "ransomware",
        "breach", "cve", "phishing", "zero-day", "hack", "encryption",
    ],
    "space": [
        "space", "nasa", "spacex", "rocket", "satellite", "orbit", "moon",
        "mars", "artemis", "launch vehicle", "astro",
    ],
    "energy": [
        "energy", "renewable", "solar", "wind power", "grid", "nuclear",
        "power plant", "electricity", "battery storage",
    ],
    "data_centres": [
        "data center", "data centre", "datacenter", "hyperscale", "colocation",
        "server farm",
    ],
    "cloud": [
        "cloud", "aws", "azure", "google cloud", "saas", "infrastructure as a service",
        "kubernetes", "serverless",
    ],
    "quantum": [
        "quantum", "qubit", "quantinuum", "ionq", "quantum computing",
    ],
    "telecom": [
        "telecom", "5g", "6g", "broadband", "cellular", "spectrum auction",
        "fibre", "fiber optic",
    ],
    "consumer_tech": [
        "iphone", "android", "smartphone", "consumer", "wearable", "apple watch",
        "gaming console", "playstation", "xbox",
    ],
    "enterprise_tech": [
        "enterprise", "erp", "crm", "salesforce", "servicenow", "b2b software",
        "workplace",
    ],
    "defence_tech": [
        "defence", "defense", "military", "pentagon", "dod", "weapons", "missile",
        "nato", "army", "navy",
    ],
    "autonomous_systems": [
        "self-driving", "autonomous vehicle", "waymo", "cruise", "adas",
        "autopilot", "unmanned",
    ],
    "biotech": [
        "biotech", "genomics", "crispr", "drug discovery", "pharma tech",
        "bioinformatics", "synthetic biology",
    ],
    "hardware": [
        "hardware", "device", "laptop", "pc ", "motherboard", "peripheral",
        "tom's hardware",
    ],
    "manufacturing": [
        "manufacturing", "factory", "industrial", "automation", "supply factory",
        "production line",
    ],
    "supply_chain": [
        "supply chain", "logistics", "shortage", "export control", "sanction",
        "tariff", "import ban",
    ],
    "regulation": [
        "regulation", "regulator", "antitrust", "legislation", "compliance",
        "gdpr", "doj", "ftc", "sec ", "eu commission",
    ],
    "crypto": [
        "bitcoin", "ethereum", "crypto", "blockchain", "defi", "stablecoin",
        "token", "web3",
    ],
    "macro": [
        "inflation", "interest rate", "gdp", "recession", "fed ", "central bank",
        "market crash", "tariff",
    ],
}

SECTOR_LABELS: dict[str, str] = {
    "ai": "Artificial Intelligence",
    "semiconductors": "Semiconductors",
    "robotics": "Robotics",
    "cybersecurity": "Cybersecurity",
    "space": "Space",
    "energy": "Energy",
    "data_centres": "Data Centres",
    "cloud": "Cloud Infrastructure",
    "quantum": "Quantum Computing",
    "telecom": "Telecommunications",
    "consumer_tech": "Consumer Technology",
    "enterprise_tech": "Enterprise Technology",
    "defence_tech": "Defence Technology",
    "autonomous_systems": "Autonomous Systems",
    "biotech": "Biotechnology",
    "hardware": "Hardware",
    "manufacturing": "Manufacturing Technology",
    "supply_chain": "Supply Chain",
    "regulation": "Technology Regulation",
    "crypto": "Crypto / Blockchain",
    "macro": "Technology Macro",
    "general": "General Technology",
}


def classify_sectors(title: str, summary: str) -> tuple[list[str], str | None]:
    hay = f" {title} {summary} ".lower()
    scores: dict[str, int] = {}
    for sector_id, words in SECTORS.items():
        score = sum(1 for w in words if w in hay)
        if score:
            scores[sector_id] = score
    if not scores:
        return [], None
    ordered = sorted(scores, key=lambda k: (-scores[k], k))
    return ordered, ordered[0]
