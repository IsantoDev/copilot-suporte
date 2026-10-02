"""Configuração lida do .env, num lugar só."""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    # repr=False: o token nunca aparece se a configuração for impressa ou cair num log.
    movidesk_token: str = field(default_factory=lambda: os.getenv("MOVIDESK_TOKEN", ""), repr=False)
    # Endereço do Movidesk da empresa; fica no .env para não aparecer no repositório público.
    movidesk_url: str = field(default_factory=lambda: os.getenv("MOVIDESK_URL", "").rstrip("/"))
    modelo: str = "google/embeddinggemma-300m"
