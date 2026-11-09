"""
agents/storage/firestore_provider.py
Dedicated Firestore storage provider for OyenMath autonomous learning missions.
Provides FirestoreMissionStorage with graceful local fallback.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union

from ..checkpoint import (
    BaseMissionCheckpointer,
    FirestoreMissionCheckpointer,
    OyenFileCheckpointer,
    get_default_checkpointer,
)

logger = logging.getLogger("oyen.storage.firestore")

__all__ = ["FirestoreMissionStorage", "FirestoreMissionCheckpointer"]


class FirestoreMissionStorage(FirestoreMissionCheckpointer):
    """
    Firestore storage provider for OyenMath.
    Persists mission checkpoints in Google Cloud Firestore when configured,
    or falls back automatically and gracefully to OyenFileCheckpointer when offline.
    """
    pass
