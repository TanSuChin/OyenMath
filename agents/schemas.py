"""OyenMath Autonomous AI Learning Platform - Tool Schemas & Validation Layer.

Milestone M2: Strict Pydantic v2 Schemas for Mathematical Tools, Input Validation,
and Structured Invocation Logging.

Features:
- Strict Pydantic v2 validation for all tool inputs
- Explicit schemas: CheckEquivalenceInput, CalculusInput, QuadraticAnalysisInput,
  TangentNormalInput, StationaryPointsInput, GetSyllabusInput
- Tool validation wrappers with structured error envelopes
- High-resolution structured logging (caller, parameters, latency ms, status)
- Safe execution dispatcher preventing invalid or out-of-spec tool calls
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import math
import time
from typing import Any, Dict, List, Literal, Optional, Tuple, Type, Union
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from . import math_tools as mt

logger = logging.getLogger("oyen.tools")


# =====================================================================
# Strict Pydantic v2 Tool Input Schemas
# =====================================================================

def _reject_nan_inf(v: Any, field_name: str) -> Any:
    """Reject NaN and infinite floats or string representations."""
    if v is None:
        return v
    if isinstance(v, (int, float)):
        if math.isnan(v) or math.isinf(v):
            raise ValueError(f"Nilai '{field_name}' tidak boleh NaN atau Inf")
    elif isinstance(v, str):
        v_clean = v.strip().lower()
        if v_clean in ("nan", "+nan", "-nan", "inf", "+inf", "-inf", "infinity", "-infinity"):
            raise ValueError(f"Nilai '{field_name}' tidak boleh NaN atau Inf")
    return v


class ToolInputBase(BaseModel):
    """Base model for all mathematical tool inputs."""
    model_config = ConfigDict(
        extra="forbid",  # Reject unknown fields to prevent parameter injection
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class CheckEquivalenceInput(ToolInputBase):
    """Input schema for check_equivalence tool."""
    a: str = Field(
        ...,
        min_length=1,
        max_length=150,
        description="First mathematical expression (or student answer)",
    )
    b: str = Field(
        ...,
        min_length=1,
        max_length=150,
        description="Second mathematical expression (or expected answer)",
    )
    require_constant: bool = Field(
        default=False,
        description="Whether to require explicit constant of integration (+ C)",
    )

    @field_validator("a", "b", mode="before")
    @classmethod
    def coerce_to_str(cls, v: Any) -> str:
        if v is None:
            raise ValueError("Ungkapan tidak boleh kosong")
        return str(v).strip()


class CalculusInput(ToolInputBase):
    """Input schema for calculus tool."""
    op: Literal[
        "diff",
        "integrate",
        "definite",
        "simplify",
        "second_derivative",
        "diff2",
        "tangent",
        "normal",
        "stationary_points",
    ] = Field(
        ...,
        description="Calculus operation to perform",
    )
    expr: str = Field(
        ...,
        min_length=1,
        max_length=150,
        description="Mathematical expression to differentiate, integrate, or evaluate",
    )
    var: str = Field(
        default="x",
        min_length=1,
        max_length=10,
        description="Independent variable (default 'x')",
    )
    lower: Optional[Union[str, float, int]] = Field(
        default=None,
        description="Lower integration bound (required when op='definite')",
    )
    upper: Optional[Union[str, float, int]] = Field(
        default=None,
        description="Upper integration bound (required when op='definite')",
    )
    at_x: Optional[Union[str, float, int]] = Field(
        default=None,
        description="Point x0 for tangent/normal calculations",
    )

    @field_validator("lower", "upper", "at_x", mode="before")
    @classmethod
    def validate_finite_bounds(cls, v: Any, info) -> Any:
        return _reject_nan_inf(v, info.field_name)

    @model_validator(mode="after")
    def validate_op_requirements(self) -> "CalculusInput":
        if self.op == "definite":
            if self.lower is None or self.upper is None:
                raise ValueError(
                    "Kedua-dua 'lower' dan 'upper' diperlukan apabila op='definite'"
                )
        if self.op in ("tangent", "normal"):
            if self.at_x is None:
                raise ValueError(
                    f"Nilai 'at_x' diperlukan apabila op='{self.op}'"
                )
        return self


class QuadraticAnalysisInput(ToolInputBase):
    """Input schema for quadratic_analysis tool."""
    expr: str = Field(
        ...,
        min_length=1,
        max_length=150,
        description="Quadratic expression or equation (e.g. '2x^2 - 4x - 6' or 'x^2 - 5x + 6 = 0')",
    )
    var: str = Field(
        default="x",
        min_length=1,
        max_length=10,
        description="Variable of the quadratic expression (default 'x')",
    )


class TangentNormalInput(ToolInputBase):
    """Input schema for tangent_normal tool."""
    op: Literal["tangent", "normal"] = Field(
        default="tangent",
        description="Calculate tangent line or normal line",
    )
    expr: str = Field(
        ...,
        min_length=1,
        max_length=150,
        description="Curve equation y = f(x)",
    )
    at_x: Union[str, float, int] = Field(
        ...,
        description="x-coordinate of the point of tangency/normal",
    )
    var: str = Field(
        default="x",
        min_length=1,
        max_length=10,
        description="Independent variable (default 'x')",
    )

    @field_validator("at_x", mode="before")
    @classmethod
    def validate_finite_at_x(cls, v: Any, info) -> Any:
        return _reject_nan_inf(v, info.field_name)


class StationaryPointsInput(ToolInputBase):
    """Input schema for stationary_points tool."""
    expr: str = Field(
        ...,
        min_length=1,
        max_length=150,
        description="Function expression f(x)",
    )
    var: str = Field(
        default="x",
        min_length=1,
        max_length=10,
        description="Independent variable (default 'x')",
    )


class GetSyllabusInput(ToolInputBase):
    """Input schema for get_syllabus tool."""
    topic: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Topic id code (ind, quad, dif, integ)",
    )


# =====================================================================
# Tool Schema Registry
# =====================================================================

TOOL_SCHEMA_REGISTRY: Dict[str, Type[BaseModel]] = {
    "check_equivalence": CheckEquivalenceInput,
    "calculus": CalculusInput,
    "quadratic_analysis": QuadraticAnalysisInput,
    "quadratic": QuadraticAnalysisInput,
    "tangent_normal": TangentNormalInput,
    "tangent": TangentNormalInput,
    "normal": TangentNormalInput,
    "stationary_points": StationaryPointsInput,
    "get_syllabus": GetSyllabusInput,
}


def get_tool_schema(name: str) -> Optional[Type[BaseModel]]:
    """Look up the Pydantic input schema for a given tool name."""
    return TOOL_SCHEMA_REGISTRY.get(name)


def validate_tool_input(
    tool_name: str, args: Dict[str, Any]
) -> Tuple[bool, Optional[BaseModel], Optional[str]]:
    """Validate tool input dictionary against its registered Pydantic schema.

    Returns:
        (is_valid, validated_model_or_None, error_message_or_None)
    """
    schema_cls = get_tool_schema(tool_name)
    if not schema_cls:
        return False, None, f"Tool '{tool_name}' tiada skema yang berdaftar"

    try:
        # Handle field aliases (e.g. expr_a -> a, expr_b -> b)
        normalized = dict(args) if isinstance(args, dict) else {}
        if tool_name == "check_equivalence":
            if "expr_a" in normalized and "a" not in normalized:
                normalized["a"] = normalized.pop("expr_a")
            if "expr_b" in normalized and "b" not in normalized:
                normalized["b"] = normalized.pop("expr_b")

        model = schema_cls.model_validate(normalized)
        return True, model, None
    except ValidationError as ve:
        err_details = "; ".join(
            f"{e['loc'][0] if e['loc'] else 'input'}: {e['msg']}"
            for e in ve.errors()
        )
        return False, None, f"Pengesahan parameter gagal: {err_details}"
    except Exception as ex:
        return False, None, f"Ralat pengesahan: {str(ex)}"


# =====================================================================
# Structured Tool Invocation Logging
# =====================================================================

class ToolInvocationLog(BaseModel):
    """Structured record of a single tool invocation."""
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    tool_name: str
    caller: Optional[str] = None
    input_args: Dict[str, Any]
    duration_ms: float
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# Thread-safe in-memory log buffer (last 500 records)
_TOOL_LOG_BUFFER: List[ToolInvocationLog] = []
_MAX_TOOL_LOGS = 500


def record_tool_invocation(log_entry: ToolInvocationLog) -> None:
    """Record a tool invocation in the global structured log buffer."""
    global _TOOL_LOG_BUFFER
    _TOOL_LOG_BUFFER.append(log_entry)
    if len(_TOOL_LOG_BUFFER) > _MAX_TOOL_LOGS:
        _TOOL_LOG_BUFFER = _TOOL_LOG_BUFFER[-_MAX_TOOL_LOGS:]

    level = logging.INFO if log_entry.success else logging.WARNING
    logger.log(
        level,
        "Tool %s called by %s in %.2fms (success=%s)",
        log_entry.tool_name,
        log_entry.caller or "anonymous",
        log_entry.duration_ms,
        log_entry.success,
    )


def get_tool_invocation_logs() -> List[Dict[str, Any]]:
    """Retrieve all structured tool invocation logs."""
    return [log.model_dump() for log in _TOOL_LOG_BUFFER]


def clear_tool_logs() -> None:
    """Clear structured invocation logs (used in unit test teardown)."""
    global _TOOL_LOG_BUFFER
    _TOOL_LOG_BUFFER.clear()


# =====================================================================
# Validated Tool Execution Wrapper
# =====================================================================

def run_validated_tool(
    name: str, args: Dict[str, Any], caller: Optional[str] = None
) -> Dict[str, Any]:
    """Execute a mathematical tool with strict Pydantic validation and logging.

    1. Validates input args against Pydantic schema
    2. Dispatches to SymPy engine in math_tools
    3. Measures execution latency
    4. Records structured log
    5. Returns result or error envelope
    """
    t0 = time.perf_counter()
    sanitized_args = dict(args) if isinstance(args, dict) else {}

    is_valid, validated_model, err_msg = validate_tool_input(name, sanitized_args)
    if not is_valid:
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        record_tool_invocation(
            ToolInvocationLog(
                tool_name=name,
                caller=caller,
                input_args=sanitized_args,
                duration_ms=duration_ms,
                success=False,
                error=err_msg,
            )
        )
        return {
            "error": err_msg,
            "validation_error": True,
            "tool_name": name,
        }

    # Dispatch to math_tools
    try:
        model_dump = validated_model.model_dump() if validated_model else sanitized_args
        res = mt.run_tool(name, model_dump)
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        success = "error" not in res
        err = res.get("error") if not success else None

        record_tool_invocation(
            ToolInvocationLog(
                tool_name=name,
                caller=caller,
                input_args=model_dump,
                duration_ms=duration_ms,
                success=success,
                result=res if success else None,
                error=err,
            )
        )
        return res
    except Exception as ex:
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        err = str(ex)
        record_tool_invocation(
            ToolInvocationLog(
                tool_name=name,
                caller=caller,
                input_args=sanitized_args,
                duration_ms=duration_ms,
                success=False,
                error=err,
            )
        )
        return {"error": err, "tool_name": name}
