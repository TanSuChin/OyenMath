"""
OyenMath Autonomous AI Learning Platform - Checkpoint & Persistence Layer
Milestone M1: Robust, atomic file persistence, corruption recovery,
Firestore fallback provider, and LangGraph 1.2.14 BaseCheckpointSaver bridge.

Provides:
- BaseMissionCheckpointer / BaseCheckpointProvider abstract interface
- OyenFileCheckpointer: atomic local JSON persistence with crash recovery
- CheckpointId: typed string with .path metadata
- OyenLangGraphCheckpointer: disk-backed BaseCheckpointSaver for interrupt / resume
- FirestoreMissionCheckpointer / FirestoreMissionStorage: cloud Firestore with local fallback
- get_default_checkpointer: factory for persistence provider
- Windows-safe atomic operations and sanitization helpers
"""

from __future__ import annotations

import abc
import glob
import json
import logging
import os
from pathlib import Path
import pickle
import re
import shutil
import threading
import time
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple, Union
import uuid

from pydantic import ValidationError

from .state import (
    MissionState,
    MissionStatus,
    mission_state_from_dict,
    mission_state_to_dict,
    now_utc_iso,
)

logger = logging.getLogger("oyen.checkpoint")

# Optional LangGraph imports
try:
    from langgraph.checkpoint.base import (
        BaseCheckpointSaver,
        Checkpoint,
        CheckpointMetadata,
        CheckpointTuple,
        ChannelVersions,
    )
    from langgraph.checkpoint.memory import InMemorySaver
    from langchain_core.runnables import RunnableConfig
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    BaseCheckpointSaver = object  # type: ignore
    InMemorySaver = object  # type: ignore


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class CheckpointError(Exception):
    """Base exception for all checkpointing operations."""
    pass


class CheckpointNotFoundError(CheckpointError, AttributeError):
    """Raised when the specified checkpoint or mission cannot be found."""
    pass


class CheckpointCorruptedError(CheckpointError):
    """Raised when checkpoint file exists but content cannot be parsed and recovered."""
    pass


# Alias for compatibility across explorer specs
CheckpointCorruptionError = CheckpointCorruptedError


class CheckpointPermissionError(CheckpointError):
    """Raised when file lock or permission fails after retries on Windows/POSIX."""
    pass


# ---------------------------------------------------------------------------
# Utility & Sanitization Helpers
# ---------------------------------------------------------------------------

def sanitize_identifier(ident: Any, default: str = "default") -> str:
    """Sanitize identifiers to prevent directory traversal and invalid path characters."""
    fallback = default if (default and default not in (".", "..")) else "safe_id"
    if not ident:
        return fallback
    ident_str = str(ident).strip()
    cleaned = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", ident_str)
    cleaned = re.sub(r"\.+", ".", cleaned).strip("._")
    if not cleaned or cleaned in (".", ".."):
        return fallback
    return cleaned


sanitize_filename = sanitize_identifier


def _apply_windows_extended_prefix(path_str: str) -> str:
    """Apply \\?\\ prefix on Windows for paths >= 240 chars to bypass MAX_PATH."""
    if os.name == "nt" and len(path_str) >= 240 and not path_str.startswith("\\\\?\\"):
        return "\\\\?\\" + os.path.abspath(path_str)
    return path_str


class CheckpointId(str):
    """
    Typed string representing a checkpoint identifier (e.g. 'chk_1731145600000_a1b2c3').
    Also exposes the absolute target filepath via .path attribute.
    """
    path: str

    def __new__(cls, chk_id: str, path: str = ""):
        obj = super().__new__(cls, chk_id)
        obj.path = str(path)
        return obj


# ---------------------------------------------------------------------------
# Thread-Safe Per-Mission Lock Registry
# ---------------------------------------------------------------------------

class MissionLockRegistry:
    """
    Thread-safe registry providing dedicated mutexes per mission_id.
    Prevents write collisions across concurrent worker and API threads
    while allowing different missions to process in parallel.
    """
    def __init__(self) -> None:
        self._locks: Dict[str, threading.Lock] = {}
        self._registry_lock = threading.Lock()

    def get_lock(self, mission_id: str) -> threading.Lock:
        with self._registry_lock:
            if mission_id not in self._locks:
                self._locks[mission_id] = threading.Lock()
            return self._locks[mission_id]

    def release_lock(self, mission_id: str) -> None:
        with self._registry_lock:
            self._locks.pop(mission_id, None)


_LOCK_REGISTRY = MissionLockRegistry()


# ---------------------------------------------------------------------------
# Base Mission Checkpointer Interface
# ---------------------------------------------------------------------------

class BaseMissionCheckpointer(abc.ABC):
    """
    Abstract Base Class for mission state persistence.
    Operates on typed MissionState instances or state dictionaries.
    """

    @abc.abstractmethod
    def save_checkpoint(
        self, state: Union[MissionState, Dict[str, Any]], return_path: bool = False
    ) -> str:
        """
        Save the mission state.
        Args:
            state: MissionState or dictionary with mission_id and student_id.
            return_path: If True, return the saved file path string. Otherwise checkpoint_id.
        Returns:
            CheckpointId string (or saved file path if return_path=True).
        """
        pass

    @abc.abstractmethod
    def load_checkpoint(
        self,
        mission_id: str,
        checkpoint_id: Optional[str] = None,
        student_id: Optional[str] = None,
        as_dict: bool = False,
    ) -> Optional[Union[MissionState, Dict[str, Any]]]:
        """
        Load checkpoint for mission_id. Returns None if mission does not exist.
        """
        pass

    @abc.abstractmethod
    def list_checkpoints(
        self,
        mission_id: Optional[str] = None,
        student_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        List checkpoints or missions summary metadata.
        """
        pass

    @abc.abstractmethod
    def delete_checkpoint(self, mission_id: str, student_id: Optional[str] = None) -> bool:
        """Delete checkpoint. Returns True if deleted, False if not found."""
        pass

    def delete_mission(self, mission_id: str, student_id: Optional[str] = None) -> bool:
        """Alias for delete_checkpoint."""
        return self.delete_checkpoint(mission_id, student_id)

    def mission_exists(self, mission_id: str, student_id: Optional[str] = None) -> bool:
        """Check if a mission checkpoint exists."""
        return self.load_checkpoint(mission_id, student_id=student_id) is not None


BaseCheckpointProvider = BaseMissionCheckpointer


# ---------------------------------------------------------------------------
# Oyen File Checkpointer (Atomic JSON on Local Disk)
# ---------------------------------------------------------------------------

class OyenFileCheckpointer(BaseMissionCheckpointer):
    """
    Thread-safe, atomic filesystem checkpointer.
    Stores current mission state at:
        .oyen_data/missions/{student_id}/{mission_id}.json
    Stores historical snapshots at:
        .oyen_data/missions/{student_id}/{mission_id}_checkpoints/{timestamp}_{checkpoint_id}.json

    Guarantees:
    - Atomic file replacement via write-flush-fsync-replace
    - Windows file-lock collision retry on WinError 5 / WinError 32
    - Automatic corruption recovery from latest historical snapshot
    - Thread-safe synchronization via per-mission mutexes
    """

    def __init__(
        self,
        base_dir: Optional[Union[str, Path]] = None,
        max_history: int = 50,
        lock_registry: Optional[MissionLockRegistry] = None,
    ) -> None:
        if base_dir is None:
            env_dir = os.environ.get("OYEN_DATA_DIR")
            if env_dir:
                self.base_dir = Path(env_dir) / "missions"
            else:
                # Default relative to repository root
                root = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                self.base_dir = root / ".oyen_data" / "missions"
        else:
            self.base_dir = Path(base_dir)

        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.max_history = max_history
        self._lock_reg = lock_registry or _LOCK_REGISTRY
        self._student_index: Dict[str, str] = {}
        self._index_lock = threading.Lock()

    def get_student_dir(self, student_id: str) -> Path:
        clean_sid = sanitize_identifier(student_id, default="dev-local")
        p = self.base_dir / clean_sid
        try:
            p.resolve().relative_to(self.base_dir.resolve())
        except ValueError:
            p = self.base_dir / "dev-local"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_mission_path(self, student_id: str, mission_id: str) -> Path:
        clean_mid = sanitize_identifier(mission_id, default="safe_id")
        return self.get_student_dir(student_id) / f"{clean_mid}.json"

    def get_history_dir(self, student_id: str, mission_id: str) -> Path:
        clean_mid = sanitize_identifier(mission_id, default="safe_id")
        p = self.get_student_dir(student_id) / f"{clean_mid}_checkpoints"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _locate_student_id(self, mission_id: str) -> Optional[str]:
        """Resolve student_id for a mission_id via index cache or filesystem scan."""
        clean_mid = sanitize_identifier(mission_id)
        with self._index_lock:
            if clean_mid in self._student_index:
                return self._student_index[clean_mid]

        pattern = str(self.base_dir / "*" / f"{clean_mid}.json")
        matches = glob.glob(pattern)
        if matches:
            parent_name = Path(matches[0]).parent.name
            with self._index_lock:
                self._student_index[clean_mid] = parent_name
            return parent_name

        # Also search history directories
        hist_pattern = str(self.base_dir / "*" / f"{clean_mid}_checkpoints")
        hist_matches = glob.glob(hist_pattern)
        if hist_matches:
            parent_name = Path(hist_matches[0]).parent.name
            with self._index_lock:
                self._student_index[clean_mid] = parent_name
            return parent_name

        return None

    def _atomic_write_json(self, target_path: Path, data: Dict[str, Any]) -> None:
        """
        Write JSON data to target_path using an atomic replace operation.
        Employs unique temporary filenames, fsync, and exponential retry on Windows.
        """
        target_path.parent.mkdir(parents=True, exist_ok=True)
        unique_id = f"{os.getpid()}_{threading.get_ident()}_{uuid.uuid4().hex[:8]}"
        tmp_path = target_path.parent / f"{target_path.name}.{unique_id}.tmp"

        safe_tmp_str = _apply_windows_extended_prefix(str(tmp_path))
        safe_target_str = _apply_windows_extended_prefix(str(target_path))

        try:
            with open(safe_tmp_str, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())

            # Atomic rename with retry loop for Windows PermissionError
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    os.replace(safe_tmp_str, safe_target_str)
                    break
                except PermissionError as pe:
                    if attempt == max_retries - 1:
                        raise CheckpointPermissionError(
                            f"Permission denied replacing {target_path} after {max_retries} retries: {pe}"
                        )
                    time.sleep(0.02 * (2 ** attempt))
        finally:
            if os.path.exists(safe_tmp_str):
                try:
                    os.remove(safe_tmp_str)
                except OSError:
                    pass

    def save_checkpoint(
        self, state: Union[MissionState, Dict[str, Any]], return_path: bool = False
    ) -> str:
        """
        Save active mission state and store a historical snapshot.
        """
        if isinstance(state, MissionState):
            state_dict = state.to_dict()
            mission_id = state.mission_id
            student_id = state.student_id
        elif isinstance(state, dict):
            state_dict = dict(state)
            mission_id = state_dict.get("mission_id")
            student_id = state_dict.get("student_id")
        else:
            raise ValueError(f"State must be MissionState or dict, got {type(state).__name__}")

        if not mission_id:
            raise ValueError("State must contain a non-empty 'mission_id'.")

        student_id = student_id or "dev-local"
        clean_mid = sanitize_identifier(str(mission_id))
        clean_sid = sanitize_identifier(str(student_id))

        with self._index_lock:
            self._student_index[clean_mid] = clean_sid

        now_ts = time.time()
        now_iso = now_utc_iso()
        chk_id_str = f"chk_{int(now_ts * 1000)}_{uuid.uuid4().hex[:6]}"

        state_dict["checkpoint_id"] = chk_id_str
        state_dict["updated_at"] = now_iso
        if "created_at" not in state_dict or not state_dict["created_at"]:
            state_dict["created_at"] = now_iso

        # Update in-memory state object if provided
        if isinstance(state, MissionState):
            state.updated_at = now_iso

        lock = self._lock_reg.get_lock(clean_mid)
        with lock:
            # 1. Write latest active mission file
            latest_path = self.get_mission_path(clean_sid, clean_mid)
            self._atomic_write_json(latest_path, state_dict)

            # 2. Write historical snapshot
            history_dir = self.get_history_dir(clean_sid, clean_mid)
            snapshot_path = history_dir / f"{int(now_ts * 1000)}_{chk_id_str}.json"
            self._atomic_write_json(snapshot_path, state_dict)

            # 3. Prune old history if exceeded
            self._prune_history(history_dir)

        result = CheckpointId(chk_id_str, path=str(latest_path))
        return str(latest_path) if return_path else result

    def _prune_history(self, history_dir: Path) -> None:
        """Keep only the latest max_history snapshots."""
        try:
            files = sorted(history_dir.glob("*.json"))
            if len(files) > self.max_history:
                excess = len(files) - self.max_history
                for p in files[:excess]:
                    try:
                        p.unlink()
                    except OSError:
                        pass
        except Exception as e:
            logger.warning(f"Error pruning checkpoint history: {e}")

    def load_checkpoint(
        self,
        mission_id: str,
        checkpoint_id: Optional[str] = None,
        student_id: Optional[str] = None,
        as_dict: bool = False,
    ) -> Optional[Union[MissionState, Dict[str, Any]]]:
        """
        Load checkpoint for mission_id.
        Supports automatic resolution across student folders and corruption recovery.
        """
        clean_mid = sanitize_identifier(mission_id)

        # Disambiguate positional checkpoint_id vs student_id
        actual_chk_id = checkpoint_id
        actual_sid = student_id
        if checkpoint_id and not checkpoint_id.startswith("chk_") and not checkpoint_id.replace("_", "").isdigit():
            # If 2nd parameter was passed as a student_id instead of checkpoint_id
            if student_id is None:
                actual_sid = checkpoint_id
                actual_chk_id = None

        if not actual_sid:
            actual_sid = self._locate_student_id(clean_mid)

        if not actual_sid:
            return None

        lock = self._lock_reg.get_lock(clean_mid)
        with lock:
            if actual_chk_id:
                history_dir = self.get_history_dir(actual_sid, clean_mid)
                matches = list(history_dir.glob(f"*_{actual_chk_id}.json")) + list(
                    history_dir.glob(f"{actual_chk_id}.json")
                )
                if not matches:
                    return None
                target_file = matches[0]
            else:
                target_file = self.get_mission_path(actual_sid, clean_mid)

            if not target_file.exists():
                return None

            try:
                with open(target_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if not content:
                    raise CheckpointCorruptedError(f"Checkpoint file {target_file} is empty (0 bytes).")
                data = json.loads(content)
                # Verify schema validity by validating against MissionState
                st = mission_state_from_dict(data)
                return data if as_dict else st
            except (
                json.JSONDecodeError,
                UnicodeDecodeError,
                CheckpointCorruptedError,
                ValidationError,
                ValueError,
                TypeError,
            ) as e:
                logger.error(f"Checkpoint corruption in {target_file}: {e}")
                # Attempt automatic recovery from latest snapshot in history
                recovered = self._recover_from_history(actual_sid, clean_mid)
                if recovered is not None:
                    return recovered if as_dict else mission_state_from_dict(recovered)
                raise CheckpointCorruptedError(f"Corrupted checkpoint in {target_file} and no valid history: {e}")

    def _recover_from_history(self, student_id: str, clean_mid: str) -> Optional[Dict[str, Any]]:
        """Attempt to restore the latest valid historical snapshot."""
        history_dir = self.get_history_dir(student_id, clean_mid)
        snapshots = sorted(history_dir.glob("*.json"), reverse=True)
        for snap in snapshots:
            try:
                with open(snap, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if not content:
                    continue
                data = json.loads(content)
                # Verify schema validity
                mission_state_from_dict(data)
                # Restore to latest active mission file
                latest_path = self.get_mission_path(student_id, clean_mid)
                self._atomic_write_json(latest_path, data)
                logger.info(f"Successfully auto-recovered corrupted mission {clean_mid} from {snap.name}")
                return data
            except Exception:
                continue
        return None

    def _list_mission_history(self, mission_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """List historical checkpoint snapshots for a single mission."""
        clean_mid = sanitize_identifier(mission_id)
        student_id = self._locate_student_id(clean_mid)
        if not student_id:
            return []

        lock = self._lock_reg.get_lock(clean_mid)
        with lock:
            history_dir = self.get_history_dir(student_id, clean_mid)
            files = sorted(history_dir.glob("*.json"), reverse=True)
            if limit:
                files = files[:limit]

            results = []
            for p in files:
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    results.append({
                        "checkpoint_id": data.get("checkpoint_id", p.stem),
                        "timestamp": data.get("updated_at", ""),
                        "status": data.get("status", "UNKNOWN"),
                        "current_agent": data.get("current_agent", ""),
                        "step": data.get("budget", {}).get("steps_taken", 0),
                        "file_size": p.stat().st_size,
                    })
                except Exception:
                    continue
            return results

    def list_missions(self, student_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List active saved missions across students or for a specific student."""
        results = []
        student_dirs = []
        if student_id:
            safe_s = sanitize_identifier(student_id)
            sp = self.base_dir / safe_s
            if sp.is_dir():
                student_dirs.append(sp)
        else:
            student_dirs = [p for p in self.base_dir.iterdir() if p.is_dir() and not p.name.startswith("_")]

        for s_dir in student_dirs:
            for f_entry in s_dir.glob("*.json"):
                if f_entry.name.startswith("."):
                    continue
                try:
                    with open(f_entry, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                    results.append({
                        "mission_id": raw.get("mission_id"),
                        "student_id": raw.get("student_id"),
                        "topic_id": raw.get("topic_id"),
                        "status": raw.get("status"),
                        "target_mastery": raw.get("goal", {}).get("target_mastery", 0.8),
                        "verified_mastery": raw.get("verified_mastery", {}),
                        "created_at": raw.get("created_at"),
                        "updated_at": raw.get("updated_at"),
                    })
                except Exception as e:
                    logger.warning(f"Skipping unparseable checkpoint {f_entry}: {e}")
        return results

    def list_checkpoints(
        self,
        mission_id: Optional[str] = None,
        student_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Universal list helper:
        - If mission_id is provided, lists snapshots for that mission.
        - If mission_id is None, lists active missions.
        """
        if mission_id is not None:
            if self.mission_exists(mission_id):
                return self._list_mission_history(mission_id, limit=limit)
            elif (self.base_dir / sanitize_identifier(mission_id)).is_dir():
                return self.list_missions(student_id=mission_id)
            return self._list_mission_history(mission_id, limit=limit)
        return self.list_missions(student_id=student_id)

    def delete_checkpoint(self, mission_id: str, student_id: Optional[str] = None) -> bool:
        """Delete active mission file and all historical snapshots."""
        clean_mid = sanitize_identifier(mission_id)
        actual_sid = student_id or self._locate_student_id(clean_mid)
        if not actual_sid:
            return False

        lock = self._lock_reg.get_lock(clean_mid)
        with lock:
            latest = self.get_mission_path(actual_sid, clean_mid)
            history = self.get_history_dir(actual_sid, clean_mid)
            deleted = False

            if latest.exists():
                try:
                    latest.unlink()
                    deleted = True
                except OSError:
                    pass

            if history.exists():
                try:
                    shutil.rmtree(history)
                    deleted = True
                except OSError:
                    pass

            with self._index_lock:
                self._student_index.pop(clean_mid, None)

        self._lock_reg.release_lock(clean_mid)
        return deleted

    def get_langgraph_checkpointer(self) -> Any:
        """Construct a disk-backed LangGraph BaseCheckpointSaver bridge."""
        if not LANGGRAPH_AVAILABLE:
            raise RuntimeError("langgraph is not installed.")
        return OyenLangGraphCheckpointer(base_dir=str(self.base_dir / "_langgraph"))


# ---------------------------------------------------------------------------
# LangGraph BaseCheckpointSaver Bridge
# ---------------------------------------------------------------------------

if LANGGRAPH_AVAILABLE:
    class OyenLangGraphCheckpointer(InMemorySaver):
        """
        Disk-backed persistent checkpoint saver for LangGraph StateGraph workflows.
        Persists graph channels, tasks, and interrupt states across process restarts.
        """
        def __init__(self, base_dir: Optional[Union[str, Path]] = None) -> None:
            super().__init__()
            self.base_dir = Path(base_dir or (Path(os.getcwd()) / ".oyen_data" / "missions" / "_langgraph"))
            self.base_dir.mkdir(parents=True, exist_ok=True)
            self._file_lock = threading.RLock()
            self._loaded_threads: set[str] = set()

        def _get_thread_file(self, thread_id: str) -> Path:
            clean_tid = sanitize_identifier(thread_id)
            return self.base_dir / f"{clean_tid}.chk"

        def _ensure_thread_loaded(self, thread_id: str) -> None:
            if thread_id in self._loaded_threads:
                return
            with self._file_lock:
                if thread_id in self._loaded_threads:
                    return
                chk_file = self._get_thread_file(thread_id)
                if chk_file.exists():
                    try:
                        with open(chk_file, "rb") as f:
                            data = pickle.load(f)
                            for k, v in data.get("storage", {}).items():
                                self.storage[k].update(v)
                            self.writes.update(data.get("writes", {}))
                            self.blobs.update(data.get("blobs", {}))
                    except Exception as e:
                        logger.warning(f"Could not load LangGraph checkpoint for {thread_id}: {e}")
                self._loaded_threads.add(thread_id)

        def _persist_thread(self, thread_id: str) -> None:
            clean_tid = sanitize_identifier(thread_id)
            chk_file = self._get_thread_file(clean_tid)
            unique_tmp = f"{chk_file.name}.{os.getpid()}_{uuid.uuid4().hex[:8]}.tmp"
            tmp_file = chk_file.parent / unique_tmp

            with self._file_lock:
                # Convert storage to plain dictionaries to avoid lambda pickling error
                # and take atomic snapshot copies under lock before iteration / dump
                plain_storage = {k: dict(v) for k, v in list(self.storage.items()) if k == thread_id}
                plain_writes = {k: v for k, v in list(self.writes.items()) if k[0] == thread_id}
                plain_blobs = {k: v for k, v in list(self.blobs.items()) if k[0] == thread_id}

                try:
                    with open(tmp_file, "wb") as f:
                        pickle.dump({"storage": plain_storage, "writes": plain_writes, "blobs": plain_blobs}, f)
                        f.flush()
                        os.fsync(f.fileno())

                    for attempt in range(5):
                        try:
                            os.replace(tmp_file, chk_file)
                            break
                        except PermissionError:
                            if attempt == 4:
                                raise
                            time.sleep(0.015 * (2 ** attempt))
                finally:
                    if tmp_file.exists():
                        try:
                            tmp_file.unlink()
                        except OSError:
                            pass

        def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
            thread_id = config["configurable"]["thread_id"]
            self._ensure_thread_loaded(thread_id)
            with self._file_lock:
                return super().get_tuple(config)

        def list(
            self,
            config: Optional[RunnableConfig],
            *,
            filter: Optional[Dict[str, Any]] = None,
            before: Optional[RunnableConfig] = None,
            limit: Optional[int] = None,
        ) -> Iterator[CheckpointTuple]:
            if config:
                thread_id = config["configurable"]["thread_id"]
                self._ensure_thread_loaded(thread_id)
            with self._file_lock:
                return iter(list(super().list(config, filter=filter, before=before, limit=limit)))

        def put(
            self,
            config: RunnableConfig,
            checkpoint: Checkpoint,
            metadata: CheckpointMetadata,
            new_versions: ChannelVersions,
        ) -> RunnableConfig:
            thread_id = config["configurable"]["thread_id"]
            self._ensure_thread_loaded(thread_id)
            with self._file_lock:
                res = super().put(config, checkpoint, metadata, new_versions)
                self._persist_thread(thread_id)
                return res

        def put_writes(
            self,
            config: RunnableConfig,
            writes: Sequence[Tuple[str, Any]],
            task_id: str,
            task_path: str = "",
        ) -> None:
            thread_id = config["configurable"]["thread_id"]
            self._ensure_thread_loaded(thread_id)
            with self._file_lock:
                super().put_writes(config, writes, task_id, task_path)
                self._persist_thread(thread_id)

        def delete_thread(self, thread_id: str) -> None:
            self._ensure_thread_loaded(thread_id)
            chk_file = self._get_thread_file(thread_id)
            with self._file_lock:
                self.storage.pop(thread_id, None)
                if chk_file.exists():
                    try:
                        chk_file.unlink()
                    except OSError:
                        pass
                self._loaded_threads.discard(thread_id)
else:
    class OyenLangGraphCheckpointer:  # type: ignore
        def __init__(self, *args, **kwargs):
            raise RuntimeError("langgraph is required to use OyenLangGraphCheckpointer.")


# ---------------------------------------------------------------------------
# Firestore Mission Checkpointer Stub & Fallback
# ---------------------------------------------------------------------------

class FirestoreMissionCheckpointer(BaseMissionCheckpointer):
    """
    Firestore-backed mission checkpointer with automatic local file fallback.
    If firebase_admin is absent or unconfigured, gracefully delegates to OyenFileCheckpointer.
    """
    def __init__(
        self,
        collection_name: str = "oyen_students",
        fallback_to_file: bool = True,
        fallback_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        self.collection_name = collection_name
        self.fallback_to_file = fallback_to_file
        self.fallback_dir = fallback_dir
        self._fallback_instance: Optional[OyenFileCheckpointer] = None
        self._client: Any = None
        self._initialized = False

        self._init_firestore()

    def _init_firestore(self) -> None:
        try:
            import firebase_admin
            from firebase_admin import firestore

            if not firebase_admin._apps:
                firebase_admin.initialize_app()
            self._client = firestore.client()
            self._initialized = True
            logger.info("FirestoreMissionCheckpointer connected successfully.")
        except Exception as e:
            logger.info(f"Firestore not available ({e}). Using local file checkpointer.")
            self._initialized = False
            if self.fallback_to_file:
                self._fallback_instance = OyenFileCheckpointer(base_dir=self.fallback_dir)
            else:
                raise RuntimeError(f"Firestore initialization failed and fallback_to_file is False: {e}")

    @property
    def is_using_fallback(self) -> bool:
        return self._fallback_instance is not None

    def save_checkpoint(
        self, state: Union[MissionState, Dict[str, Any]], return_path: bool = False
    ) -> str:
        if self._fallback_instance:
            return self._fallback_instance.save_checkpoint(state, return_path=return_path)

        state_dict = state.to_dict() if isinstance(state, MissionState) else dict(state)
        mission_id = sanitize_identifier(str(state_dict.get("mission_id")))
        student_id = sanitize_identifier(str(state_dict.get("student_id") or "dev-local"))
        chk_id = f"chk_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"

        state_dict["checkpoint_id"] = chk_id
        state_dict["updated_at"] = now_utc_iso()

        doc_ref = (
            self._client.collection(self.collection_name)
            .document(student_id)
            .collection("missions")
            .document(mission_id)
        )
        doc_ref.set(state_dict)
        doc_ref.collection("checkpoints").document(chk_id).set(state_dict)
        return chk_id

    def load_checkpoint(
        self,
        mission_id: str,
        checkpoint_id: Optional[str] = None,
        student_id: Optional[str] = None,
        as_dict: bool = False,
    ) -> Optional[Union[MissionState, Dict[str, Any]]]:
        if self._fallback_instance:
            return self._fallback_instance.load_checkpoint(
                mission_id, checkpoint_id=checkpoint_id, student_id=student_id, as_dict=as_dict
            )

        clean_mid = sanitize_identifier(mission_id)
        query = self._client.collection_group("missions").where("mission_id", "==", clean_mid).limit(1)
        docs = list(query.stream())
        if not docs:
            return None

        doc_ref = docs[0].reference
        if checkpoint_id:
            snap = doc_ref.collection("checkpoints").document(checkpoint_id).get()
            data = snap.to_dict() if snap.exists else None
        else:
            snap = doc_ref.get()
            data = snap.to_dict() if snap.exists else None

        if data is None:
            return None
        return data if as_dict else mission_state_from_dict(data)

    def list_checkpoints(
        self,
        mission_id: Optional[str] = None,
        student_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if self._fallback_instance:
            return self._fallback_instance.list_checkpoints(
                mission_id=mission_id, student_id=student_id, limit=limit
            )

        if mission_id:
            clean_mid = sanitize_identifier(mission_id)
            query = self._client.collection_group("missions").where("mission_id", "==", clean_mid).limit(1)
            docs = list(query.stream())
            if not docs:
                return []
            chk_query = docs[0].reference.collection("checkpoints").order_by("updated_at", direction="DESCENDING")
            if limit:
                chk_query = chk_query.limit(limit)
            return [d.to_dict() for d in chk_query.stream()]

        q = self._client.collection_group("missions")
        if student_id:
            clean_sid = sanitize_identifier(student_id)
            q = q.where("student_id", "==", clean_sid)
        if limit:
            q = q.limit(limit)
        return [d.to_dict() for d in q.stream()]

    def delete_checkpoint(self, mission_id: str, student_id: Optional[str] = None) -> bool:
        if self._fallback_instance:
            return self._fallback_instance.delete_checkpoint(mission_id, student_id)

        clean_mid = sanitize_identifier(mission_id)
        query = self._client.collection_group("missions").where("mission_id", "==", clean_mid).limit(1)
        docs = list(query.stream())
        if not docs:
            return False

        doc_ref = docs[0].reference
        for chk in doc_ref.collection("checkpoints").stream():
            chk.reference.delete()
        doc_ref.delete()
        return True


FirestoreMissionStorage = FirestoreMissionCheckpointer


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------

def get_default_checkpointer(
    mode: Optional[str] = None,
    base_dir: Optional[Union[str, Path]] = None,
) -> BaseMissionCheckpointer:
    """
    Factory creating the configured checkpointer.
    Mode:
      - 'file': OyenFileCheckpointer.
      - 'firestore': FirestoreMissionCheckpointer (with fallback to file).
      - 'auto' / None: Uses firestore if FIREBASE_CONFIG or GOOGLE_APPLICATION_CREDENTIALS exists,
                       otherwise OyenFileCheckpointer.
    """
    selected_mode = (mode or os.environ.get("OYEN_PERSISTENCE_MODE", "auto")).lower()
    if selected_mode == "file":
        return OyenFileCheckpointer(base_dir=base_dir)

    if selected_mode == "firestore":
        return FirestoreMissionCheckpointer(fallback_to_file=True, fallback_dir=base_dir)

    # Auto mode
    has_creds = bool(
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        or os.environ.get("FIREBASE_CONFIG")
    )
    if has_creds:
        return FirestoreMissionCheckpointer(fallback_to_file=True, fallback_dir=base_dir)
    return OyenFileCheckpointer(base_dir=base_dir)
