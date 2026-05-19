import re
from functools import lru_cache
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


def parse_skill_md(filepath):
    data = {"name": "", "description": "", "raw_content": "", "body_content": "", "metadata": {}}
    try:
        with open(filepath, encoding="utf-8-sig") as f:
            content = f.read()
            data["raw_content"] = content

        # Extract body content (without frontmatter)
        body = re.sub(
            r"\A---[ \t]*\r?\n.*?\r?\n---[ \t]*(?:\r?\n|\Z)", "", content, count=1, flags=re.DOTALL
        )
        data["body_content"] = body.strip()

        match = re.match(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", content, re.DOTALL)
        if match:
            frontmatter = match.group(1)
            metadata = parse_frontmatter(frontmatter)
            data["metadata"] = metadata
            data["name"] = str(metadata.get("name", "") or "").strip()
            data["description"] = normalize_description(metadata.get("description", ""))
            data["is_bundle"] = metadata.get("type") == "bundle" or "bundle" in data["name"].lower()

        if not data["description"]:
            data["description"] = extract_markdown_description(content)

        # Look for commands (ONLY in commands/ subdir if SKILL.md exists)
        data["commands"] = []
        base_dir = Path(filepath).parent

        # Files in commands/ directory (trusted)
        commands_dir = base_dir / "commands"
        if commands_dir.is_dir():
            for md_file in commands_dir.glob("*.md"):
                # Basic check to skip obviously non-command files
                if md_file.stem.lower() not in {"readme", "license", "changelog"}:
                    data["commands"].append(str(md_file.absolute()))
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
    return data


def parse_command_md(filepath):
    data = {"name": "", "description": "", "raw_content": "", "body_content": "", "metadata": {}}
    try:
        stem = Path(filepath).stem

        # Skip common non-command files
        if stem.lower() in {
            "readme",
            "license",
            "changelog",
            "contributing",
            "todo",
            "package",
            "security",
            "skill",
        }:
            return None

        with open(filepath, encoding="utf-8-sig") as f:
            content = f.read()
            data["raw_content"] = content

        # Extract body content (without frontmatter)
        body = re.sub(
            r"\A---[ \t]*\r?\n.*?\r?\n---[ \t]*(?:\r?\n|\Z)", "", content, count=1, flags=re.DOTALL
        )
        data["body_content"] = body.strip()

        match = re.match(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", content, re.DOTALL)
        if match:
            frontmatter = match.group(1)
            metadata = parse_frontmatter(frontmatter)
            data["metadata"] = metadata
            data["name"] = str(metadata.get("name", "") or "").strip()
            data["client"] = metadata.get("client", "")
            data["category"] = metadata.get("category", "")
            data["description"] = normalize_description(metadata.get("description", ""))

        data["main_category"] = get_main_category(data.get("category", ""))

        # If no name in frontmatter, look for first H1 header
        if not data["name"]:
            h1_match = re.search(r"^#\s+(.*)$", content, re.MULTILINE)
            if h1_match:
                data["name"] = h1_match.group(1).strip()
            else:
                data["name"] = stem

        if not data["description"]:
            data["description"] = extract_markdown_description(content)

        # If name or filename contains client info, extract it
        if not data.get("client"):
            # Check for patterns like "DEPLOY.Codex" or "Codex.md"
            if "." in stem:
                parts = stem.split(".")
                data["client"] = parts[-1]
            else:
                # Check if filename IS a client name
                from skill_manager.core.quick_copy import CLIENT_FORMATS

                if stem in CLIENT_FORMATS:
                    data["client"] = stem

    except Exception as e:
        print(f"Error parsing command {filepath}: {e}")
        return None
    return data


def parse_frontmatter(frontmatter):
    if not frontmatter:
        return {}

    if yaml is not None:
        try:
            parsed = yaml.safe_load(frontmatter)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

    parsed = {}
    current_key = None
    current_lines = []

    def flush_multiline():
        nonlocal current_key, current_lines
        if current_key:
            parsed[current_key] = " ".join(line.strip() for line in current_lines).strip()
            current_key = None
            current_lines = []

    for line in frontmatter.splitlines():
        if re.match(r"^\s", line) and current_key:
            current_lines.append(line)
            continue

        flush_multiline()
        key_match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not key_match:
            continue

        key, value = key_match.groups()
        value = value.strip()
        if value in {">", "|", ">-", "|-"}:
            current_key = key
            current_lines = []
        else:
            parsed[key] = value.strip(" \"'")

    flush_multiline()
    return parsed


def normalize_description(value):
    if value is None:
        return ""
    if isinstance(value, list):
        value = " ".join(str(item) for item in value)
    elif not isinstance(value, str):
        value = str(value)
    return re.sub(r"\s+", " ", value).strip().strip(" \"'")


def extract_markdown_description(content):
    body = re.sub(
        r"\A---[ \t]*\r?\n.*?\r?\n---[ \t]*(?:\r?\n|\Z)", "", content, count=1, flags=re.DOTALL
    )
    paragraphs = []
    current = []

    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        if line.startswith("#") or line.startswith("```") or line.startswith("---"):
            continue
        current.append(re.sub(r"[*_`]+", "", line))

    if current:
        paragraphs.append(" ".join(current))

    return normalize_description(paragraphs[0] if paragraphs else "")


_CATEGORY_PATTERNS = None


def _get_category_patterns():
    global _CATEGORY_PATTERNS
    if _CATEGORY_PATTERNS is not None:
        return _CATEGORY_PATTERNS

    _CATEGORY_PATTERNS = {}
    for cat, keywords in CATEGORIES.items():
        # Split keywords into plain and special (those with special chars)
        plain = []
        special = []
        for kw in keywords:
            if re.search(r"[+#./\s-]", kw):
                special.append(kw)
            else:
                plain.append(kw)

        patterns = []
        if plain:
            patterns.append(
                re.compile(r"\b(" + "|".join(re.escape(kw) for kw in plain) + r")\b", re.I)
            )
        if special:
            # Special patterns might need individual matching
            patterns.extend([re.compile(re.escape(kw), re.I) for kw in special])

        _CATEGORY_PATTERNS[cat] = patterns
    return _CATEGORY_PATTERNS


CATEGORIES = {
    "Core Workflow": [
        "plan",
        "planning",
        "brainstorm",
        "brainstorming",
        "constructive work",
        "kaizen",
        "starred",
        "questions",
        "underspecified",
        "verification",
        "completion",
        "task",
        "workflow",
        "conductor",
        "build",
        "project guidelines",
        "sharp edges",
        "speckit",
        "updater",
    ],
    "Developer Tools": [
        "git",
        "github",
        "pr",
        "pull request",
        "commit",
        "issue",
        "dx",
        "developer experience",
        "file organizer",
        "vexor",
        "semantic file discovery",
        "cli",
        "tool",
        "tools",
        "comprehensive review",
    ],
    "Debugging": [
        "debug",
        "debugging",
        "error",
        "stack traces",
        "bug",
        "error detective",
        "logs",
        "root cause",
    ],
    "Architecture": [
        "architect",
        "senior architect",
        "project architect",
        "architecture",
        "architecture diagram",
        "architecture patterns",
        "system design",
        "c4",
        "adr",
        "decision record",
        "domain-driven",
        "ddd",
        "cqrs",
        "event sourcing",
        "bounded context",
        "monorepo",
    ],
    "Code Quality": [
        "technical debt",
        "legacy",
        "modernizer",
        "refactor",
        "clean code",
        "code quality",
    ],
    "Security": [
        "security",
        "hack",
        "vulnerability",
        "pentest",
        "penetration",
        "auth",
        "xss",
        "threat",
        "risk",
        "attack",
        "red team",
        "active directory",
        "kerberos",
        "forensics",
        "incident response",
        "privilege escalation",
        "secrets",
        "credentials",
        "mtls",
        "zero-trust",
        "shodan",
    ],
    "Compliance": ["compliance", "audit", "access review", "pci", "policy"],
    "Web Development": [
        "web",
        "frontend",
        "react",
        "next.js",
        "tailwind",
        "css",
        "ui",
        "ux",
        "fullstack",
        "angular",
        "vue",
        "html",
        "website",
        "portfolio",
        "wordpress",
        "three.js",
        "threejs",
        "webgl",
    ],
    "Mobile Development": [
        "mobile",
        "ios",
        "android",
        "flutter",
        "expo",
        "react native",
        "swift",
        "swiftui",
        "swiftpm",
        "app store",
        "aso",
        "kotlin",
    ],
    "Desktop Development": ["macos", "desktop", "electron", "avalonia", "makepad", "robius"],
    "AI": [
        "ai",
        "ia",
        "llm",
        "rag",
        "prompt",
        "model",
        "claude",
        "openai",
        "gemini",
        "anthropic",
        "hugging face",
        "vision model",
        "computer vision",
        "yolo",
        "sam",
        "notebooklm",
    ],
    "Agents": [
        "agent",
        "agents",
        "subagent",
        "subagents",
        "mcp",
        "crewai",
        "langchain",
        "context window",
        "agentes",
    ],
    "Game Development": ["game", "unity", "godot", "unreal"],
    "Backend Development": ["backend", "rails", "node", "api", "fastapi", "full-stack"],
    "Programming Languages": [
        "python",
        "typescript",
        "javascript",
        "rust",
        "go",
        "golang",
        "c-pro",
        " c code",
        "c++",
        "c#",
        "java",
        "ruby",
        "php",
        "elixir",
        "haskell",
        "julia",
        "memory safety",
        "memory-safe",
    ],
    "Shell Scripting": ["posix", "bash", "powershell", "busybox", "windows", "shell", "jq"],
    "Embedded Systems": ["embedded", "firmware", "arm cortex", "microcontroller"],
    "Localization": ["i18n", "localization", "translation", "locale", "rtl"],
    "Migration": ["migration", "code migration", "framework migration"],
    "Product Management": [
        "product",
        "startup",
        "saas",
        "micro-saas",
        "jtbd",
        "jobs-to-be-done",
        "customer",
        "market",
        "competitive",
        "brand",
        "persona",
        "idea",
        "darwin",
        "personal tool",
    ],
    "Business Strategy": [
        "business",
        "sales",
        "cro",
        "monetization",
        "pricing",
        "price",
        "churn",
        "retention",
        "growth",
    ],
    "Psychology": [
        "psychology",
        "psychologist",
        "identity",
        "trust",
        "calibrator",
        "assumption",
        "auditor",
        "first-principles",
        "emotional arc",
        "loss aversion",
        "objection",
        "pitch",
        "scarcity",
        "urgency",
        "sequence",
    ],
    "Careers": ["interview", "job search", "resume", "career"],
    "Marketing": [
        "marketing",
        "seo",
        "ads",
        "ad creative",
        "paid ads",
        "google ads",
        "meta",
        "linkedin",
        "tiktok",
        "influencer",
        "lead generation",
        "leads",
        "cold email",
        "copywriting",
        "headline",
        "subject line",
        "campaign",
        "audience",
        "brand reputation",
        "aso",
        "awareness",
    ],
    "Social Media": ["social", "twitter", "youtube", "publisher", "x/twitter"],
    "DevOps": [
        "devops",
        "ci/cd",
        "ci",
        "cd",
        "deploy",
        "deployment",
        "on-call",
        "runbook",
        "incident",
        "slack",
        "tmux",
    ],
    "Cloud Infrastructure": [
        "docker",
        "kubernetes",
        "k8s",
        "aws",
        "azure",
        "gcp",
        "cloud",
        "cloudflare",
        "terraform",
        "linux",
        "server",
        "istio",
        "service mesh",
    ],
    "Observability": [
        "observability",
        "monitor",
        "monitoring",
        "prometheus",
        "slo",
        "tracing",
        "jaeger",
        "tempo",
    ],
    "Build Systems": ["bazel", "nx", "turborepo"],
    "Background Jobs": ["inngest", "background jobs", "queues", "durable execution"],
    "Performance": ["performance", "performance bottlenecks", "performance optimizer", "profiling"],
    "Data": ["data", "vector", "warehouse", "forecast", "analysis", "analyze"],
    "Databases": ["sql", "postgres", "mysql", "database", "dbt"],
    "Analytics": ["analytics", "backtesting", "spreadsheet", "xlsx"],
    "Design": [
        "design",
        "canvas",
        "canva",
        "art",
        "figma",
        "theme",
        "visual",
        "hig",
        "human interface guidelines",
    ],
    "Content": [
        "content",
        "writing",
        "blog",
        "article",
        "video",
        "audio",
        "gif",
        "favicon",
        "unsplash",
        "remotion",
        "portfolio",
        "rsvp",
        "speed reader",
    ],
    "Diagrams": ["mermaid", "diagram"],
    "Documentation": [
        "documentation",
        "docs",
        "readme",
        "wiki",
        "onboarding",
        "obsidian",
        "markdown",
        "latex",
        "paper",
        "docx",
        "pptx",
        "office",
        "document",
    ],
    "Knowledge Management": [
        "summarizer",
        "explain",
        "socratic",
        "bullet",
        "knowledge",
        "context",
        "context save",
        "context restore",
        "diary",
        "logger",
    ],
    "Communications": [
        "communication",
        "communication mode",
        "internal comms",
        "communications",
        "brief",
        "terse",
        "caveman",
        "status reports",
    ],
    "Logistics": ["logistics", "freight", "carrier", "returns", "reverse logistics"],
    "Inventory": ["inventory", "demand planning", "warehouse"],
    "Procurement": ["procurement", "purchase", "energy procurement"],
    "Manufacturing": ["production scheduling", "manufacturing"],
    "ERP": ["odoo", "erp", "timesheet"],
    "Quality Control": ["quality control", "non-conformance"],
    "Billing": ["billing", "invoice"],
    "Payments": ["payment", "paypal", "stripe", "tax"],
    "Finance": ["finance", "financial", "trading", "investment", "buffett"],
    "Web3": [
        "blockchain",
        "web3",
        "defi",
        "nft",
        "smart contract",
        "bitcoin",
        "lightning",
        "wallet",
    ],
    "Legal": [
        "legal",
        "law",
        "contract",
        "compliant",
        "jurid",
        "direito",
        "advogado",
        "criminal",
        "trabalhista",
        "tributario",
        "consumidor",
        "imobiliario",
        "civil",
        "leilao",
        "leilões",
        "edital",
        "nulidades",
        "cpc",
        "lei",
    ],
    "Human Resources": ["employment", "hr", "payroll"],
    "Health": [
        "health",
        "medical",
        "clinical",
        "hospital",
        "emergency",
        "medical card",
        "goal analyzer",
        "健康",
        "医疗",
        "急救",
    ],
    "Fitness": ["fitness", "nutrition", "weightloss", "营养"],
    "Sleep": ["sleep", "睡眠"],
    "Mental Health": ["mental health", "心理"],
    "Sexual Health": ["sexual health"],
    "Oral Health": ["oral health", "口腔"],
    "Occupational Health": ["occupational health"],
    "Rehabilitation": ["rehabilitation", "康复"],
    "Travel Health": ["travel health"],
    "Traditional Medicine": ["tcm", "体质"],
    "Testing": [
        "test",
        "testing",
        "automation",
        "qa",
        "e2e",
        "playwright",
        "cypress",
        "jest",
        "tdd",
        "validation",
        "acceptance",
        "verify",
    ],
    "Linting": ["shellcheck", "linting", "lint"],
    "Uncategorized": [],
}

MAIN_CATEGORIES_MAPPING = {
    "🛠️ Core Engineering & Technology": [
        "AI",
        "Agents",
        "Architecture",
        "Backend Development",
        "Cloud Infrastructure",
        "DevOps",
        "Developer Tools",
        "Programming Languages",
        "Web Development",
        "Mobile Development",
        "Desktop Development",
        "Embedded Systems",
        "Web3",
        "Game Development",
        "Shell Scripting",
        "Build Systems",
        "Background Jobs",
    ],
    "📈 Business & Operations": [
        "Business Strategy",
        "Marketing",
        "Product Management",
        "Finance",
        "Legal",
        "Compliance",
        "Logistics",
        "Procurement",
        "Billing",
        "Payments",
        "ERP",
        "Human Resources",
        "Inventory",
        "Manufacturing",
        "Careers",
    ],
    "🛡️ Quality & Data": [
        "Security",
        "Testing",
        "Debugging",
        "Performance",
        "Observability",
        "Code Quality",
        "Linting",
        "Quality Control",
        "Migration",
        "Analytics",
        "Data",
        "Databases",
    ],
    "📚 Content & Knowledge": [
        "Content",
        "Documentation",
        "Knowledge Management",
        "Diagrams",
        "Design",
        "Communications",
        "Social Media",
        "Localization",
    ],
    "🧘 Specialized & Lifestyle": [
        "Psychology",
        "Health",
        "Mental Health",
        "Fitness",
        "Sleep",
        "Rehabilitation",
        "Traditional Medicine",
        "Occupational Health",
        "Oral Health",
        "Sexual Health",
        "Travel Health",
    ],
    "⚙️ System & Workflow": ["Core Workflow", "Uncategorized"],
}


@lru_cache(maxsize=1024)
def get_main_category(sub_category):
    if not sub_category:
        return "⚙️ System & Workflow"
    for main_cat, sub_cats in MAIN_CATEGORIES_MAPPING.items():
        if sub_category in sub_cats:
            return main_cat
        # Also check for common aliases
        if sub_category.lower() in [s.lower() for s in sub_cats]:
            return main_cat

    # If not found in mapping, default to System & Workflow
    return "⚙️ System & Workflow"


def categorize_skill(name, description):
    """
    Determines the best category for a skill based on its name and description.
    Uses keyword frequency with weighting.
    """
    # Name is high signal, give it more weight (repeat it)
    text = (name + " " + name + " " + description).lower()
    norm_text = re.sub(r"[-_]+", " ", text)

    best_category = "Uncategorized"
    max_matches = 0

    patterns = _get_category_patterns()

    for category, cat_patterns in patterns.items():
        matches = 0
        for p in cat_patterns:
            # If pattern has \b, it was a group of plain words
            if "\\b(" in p.pattern:
                matches += len(p.findall(text))
                # Also check normalized if different
                if text != norm_text:
                    matches += len(p.findall(norm_text))
            else:
                # Special pattern (literal or containing special chars)
                # Count ALL occurrences of special pattern
                matches += len(p.findall(text))
                if text != norm_text:
                    matches += len(p.findall(norm_text))

        if matches > max_matches:
            max_matches = matches
            best_category = category

    return {"main_category": get_main_category(best_category), "sub_category": best_category}


def keyword_matches(text, keyword):
    # This is now mostly unused by categorize_skill but kept for compatibility
    normalized_text = re.sub(r"[-_]+", " ", text)
    normalized_keyword = re.sub(r"[-_]+", " ", keyword)
    if re.search(r"[+#./\s-]", keyword):
        return keyword in text or normalized_keyword in normalized_text
    return (
        re.search(rf"\b{re.escape(keyword)}\b", text) is not None
        or re.search(rf"\b{re.escape(normalized_keyword)}\b", normalized_text) is not None
    )


def build_skill_search_text(skill_data):
    parts = [
        skill_data.get("name", ""),
        skill_data.get("description", ""),
        skill_data.get("folder_name", ""),
        skill_data.get("category", ""),
        skill_data.get("main_category", ""),
    ]
    metadata = skill_data.get("metadata") or {}
    for key in ("source", "risk", "category", "version", "date_added"):
        value = metadata.get(key)
        if value not in (None, ""):
            parts.append(str(value))
    return re.sub(r"\s+", " ", " ".join(parts)).lower()
