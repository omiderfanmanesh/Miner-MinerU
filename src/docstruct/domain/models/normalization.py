"""Markdown-normalization report models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class NormalizationChunk:
    index: int
    start_line: int
    end_line: int
    input_chars: int
    output_chars: int


@dataclass
class NormalizationReport:
    source_file: str
    output_file: str
    model: str
    chunk_count: int
    chunks: list[NormalizationChunk] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source_file": self.source_file,
            "output_file": self.output_file,
            "model": self.model,
            "chunk_count": self.chunk_count,
            "chunks": [asdict(chunk) for chunk in self.chunks],
        }
