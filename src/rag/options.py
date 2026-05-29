from pathlib import Path

from pydantic_settings import BaseSettings


class RagOptions(BaseSettings):
    chroma_db_path: Path = Path("./chroma_db")
    instructions_dir: Path = Path("./context_store/instructions")
    codebase_dir: Path = Path("./context_store/codebase")
    samples_dir: Path = Path("./context_store/samples")
    embed_model: str = "nomic-embed-text"
    instructions_chunk_size: int = 512
    codebase_chunk_size: int = 1024
    samples_chunk_size: int = 800
    chunk_overlap: int = 64
    retrieval_k: int = 5

    model_config = {"env_prefix": "RAG_"}
