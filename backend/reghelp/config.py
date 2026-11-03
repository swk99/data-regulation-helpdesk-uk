import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(os.getenv('DATA_DIR', './data')))
    ollama_url: str = field(default_factory=lambda: os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434').rstrip('/'))
    chat_model: str = field(default_factory=lambda: os.getenv('CHAT_MODEL', 'qwen2.5:14b'))
    embedding_model: str = field(default_factory=lambda: os.getenv('EMBEDDING_MODEL', 'nomic-embed-text'))
    api_token: str = field(default_factory=lambda: os.getenv('API_TOKEN', ''))
    origins: list[str] = field(default_factory=lambda: os.getenv('CORS_ORIGINS', 'https://swk99.github.io,http://localhost:5173').split(','))
    source_file: Path = field(default_factory=lambda: Path(os.getenv('SOURCE_FILE', str(Path(__file__).parent.parent / 'sources.yaml'))))
    request_delay: float = 2.0
    max_bytes: int = 15 * 1024 * 1024
    discovery_budget: int = 12
    document_budget: int = 10
