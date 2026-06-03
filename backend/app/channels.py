"""Intake channel identifiers — WhatsApp and web chat are stored and routed separately."""

from __future__ import annotations

from typing import Literal

WHATSAPP: Literal["whatsapp"] = "whatsapp"
WEB: Literal["web"] = "web"

WEB_SESSION_ID_PREFIX = "ws_"
