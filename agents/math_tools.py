"""Deterministic math tools (SymPy) exposed to the LLM agents.

The LLM never decides correctness alone; SymPy is the sole authoritative verifier.
Features:
- Safe symbolic parsing without arbitrary Python code execution (sp.sympify RCE eliminated)
- Standard SPM Additional Mathematics variable whitelist (x, y, C, c, t, u, v, r, h, k, m, n, theta, a, b, pi, e, sin, cos, tan, ln, sqrt, dx, dy)
- Radical symbol normalisation (√ -> sqrt)
- Explicit constant of integration handling (+ C) with require_constant flag and forgot_c tagging
- Comprehensive calculus operations: diff, second_derivative, integrate, definite, tangent, normal, stationary_points
- Quadratic analysis: discriminant, roots, vertex, axis of symmetry
- 5-second execution timeout sandbox via concurrent.futures.ThreadPoolExecutor
- 100% backward compatibility for all legacy callers (check_equivalence, calculus, get_syllabus, run_tool, TOOL_SPECS)
"""

from __future__ import annotations

import atexit
import concurrent.futures
import re
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

# ---------------------------------------------------------------------
# Global Symbols & Allowed Token Whitelist
# ---------------------------------------------------------------------
x, y, C, t, u, v, r, h, k, m, n, theta, a, b, dx, dy = sp.symbols(
    "x y C t u v r h k m n theta a b dx dy"
)
dt, dh, dr, dA, dV, ds = sp.symbols("dt dh dr dA dV ds")

_TR = standard_transformations + (implicit_multiplication_application, convert_xor)

_ALLOWED_NAMES = {
    "x", "y", "C", "c", "t", "u", "v", "r", "h", "k", "m", "n",
    "theta", "a", "b", "pi", "e", "sin", "cos", "tan", "ln", "sqrt",
    "dx", "dy", "dt", "dh", "dr", "dA", "dV", "ds", "da", "dv"
}

_SINGLE_LETTER_VARS = {
    "x", "y", "C", "c", "t", "u", "v", "r", "h", "k", "m", "n", "a", "b", "s"
}

_LOCAL_DICT: Dict[str, Any] = {
    "x": x,
    "y": y,
    "C": C,
    "c": C,  # Map lowercase c to integration constant symbol C
    "t": t,
    "u": u,
    "v": v,
    "r": r,
    "h": h,
    "k": k,
    "m": m,
    "n": n,
    "s": ds, # Default s symbol
    "theta": theta,
    "a": a,
    "b": b,
    "dx": dx,
    "dy": dy,
    "dt": dt,
    "dh": dh,
    "dr": dr,
    "dA": dA,
    "da": dA,
    "dV": dV,
    "dv": dV,
    "ds": ds,
    "e": sp.E,
    "pi": sp.pi,
    "ln": sp.log,
    "sin": sp.sin,
    "cos": sp.cos,
    "tan": sp.tan,
    "sqrt": sp.sqrt,
}

_SUPD = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")
_SUP = str.maketrans("−×·", "-**")

DEFAULT_TIMEOUT_SECONDS: float = 5.0

# Persistent ThreadPoolExecutor for sandboxed evaluation
_SANDBOX_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=4, thread_name_prefix="SymPySandbox"
)

# Register exit hook to prevent process hangs on exit if calculations are running
atexit.register(lambda: _SANDBOX_EXECUTOR.shutdown(wait=False, cancel_futures=True))


# ---------------------------------------------------------------------
# Execution Timeout Sandbox
# ---------------------------------------------------------------------
def run_with_timeout(
    fn: Callable[..., Any],
    *args: Any,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    **kwargs: Any,
) -> Any:
    """Execute a callable in the sandbox thread pool with a strict timeout limit."""
    future = _SANDBOX_EXECUTOR.submit(fn, *args, **kwargs)
    try:
        return future.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        raise TimeoutError(f"Operasi matematik melebihi had masa {timeout} saat")


# ---------------------------------------------------------------------
# Expression Preprocessing & Safe Parsing
# ---------------------------------------------------------------------
def _clean(s: str) -> str:
    """Preprocess mathematical string into standardized syntax for parsing.

    Note: Does NOT unconditionally strip '+ C' so integration constants can be checked.
    """
    if s is None:
        return ""
    s = str(s).strip()

    # Convert Unicode superscripts: x² -> x^2
    s = re.sub(r"[⁰¹²³⁴⁵⁶⁷⁸⁹]+", lambda m: "^" + m.group().translate(_SUPD), s)

    # Normalize mathematical operators
    s = s.translate(_SUP)

    # Remove derivative tick marks and integral signs
    s = s.replace("′", "").replace("'", "").replace("∫", "")

    # Strip equation prefixes: y = , f(x) = , dy/dx = , dy/dt = , x = , t = , theta =
    s = re.sub(
        r"^(?:f\s*\([a-zA-Z]+\)|d[a-zA-Z]+\s*/\s*d[a-zA-Z]+|theta|[a-zA-Z])\s*=\s*",
        "",
        s,
        flags=re.I,
    )

    # Greek letters: θ -> theta, π -> pi
    s = s.replace("θ", "theta").replace("Θ", "theta")
    s = s.replace("π", "pi").replace("Π", "pi")

    # Normalize single-letter uppercase variables (X -> x, Y -> y, T -> t, etc.)
    # except C (which is preserved for constant of integration) and differential tokens (dA, dV)
    s = re.sub(r"(?<![a-zA-Z])([XYTRHVAB])(?![a-zA-Z])", lambda m: m.group(1).lower(), s)

    # LaTeX radicals & fractions
    s = re.sub(r"\\sqrt\s*\{([^}]+)\}", r"sqrt(\1)", s)
    s = re.sub(r"\\frac\s*\{([^}]+)\}\s*\{([^}]+)\}", r"((\1)/(\2))", s)
    s = re.sub(r"\\cdot", "*", s)
    s = s.replace("\\", "")

    # Unicode radical √
    s = re.sub(r"√\s*\{([^}]+)\}", r"sqrt(\1)", s)
    s = re.sub(r"√\s*\(([^)]+)\)", r"sqrt(\1)", s)
    s = re.sub(r"√\s*([0-9a-zA-Z]+)", r"sqrt(\1)", s)
    s = s.replace("√", "sqrt")

    return s.strip()


def parse(s: str) -> sp.Expr:
    """Safely parse a mathematical expression string into a SymPy expression.

    Guarantees:
    - No raw sp.sympify is ever called on unsanitized strings (prevents RCE).
    - Length is bounded (<= 150 chars).
    - Character set is strictly constrained to safe mathematical symbols.
    - Token names must reside in _ALLOWED_NAMES or be composed of single-letter variables.
    """
    s = _clean(s)
    if not s:
        raise ValueError("ungkapan kosong")
    if len(s) > 150 or not re.fullmatch(r"[0-9a-zA-Z+\-*/^().\s]+", s):
        raise ValueError("ungkapan tidak sah")

    # Validate all alphabetic tokens
    for tok in re.findall(r"[A-Za-z]+", s):
        if tok not in _ALLOWED_NAMES:
            # Allow composite single-letter variable products (e.g. 'xy', '2uv', 'ah')
            if not all(c in _SINGLE_LETTER_VARS for c in tok):
                raise ValueError("nama tidak dibenarkan: " + tok)

    return parse_expr(s, transformations=_TR, local_dict=_LOCAL_DICT)


# ---------------------------------------------------------------------
# Equivalence Checking (Authoritative Verification)
# ---------------------------------------------------------------------
def _check_equivalence_internal(
    a: str, b: str, require_constant: bool = False
) -> dict:
    pa = parse(a)
    pb = parse(b)

    has_c_a = pa.has(C) or bool(re.search(r"\b[cC]\b", str(a)))
    has_c_b = pb.has(C) or bool(re.search(r"\b[cC]\b", str(b)))

    # Exact symbolic difference
    d = sp.simplify(pa - pb)

    if require_constant:
        # If student answer omitted + C
        if not has_c_a and has_c_b:
            return {"equivalent": False, "difference": str(d), "tag": "forgot_c"}
        if not has_c_a and not has_c_b:
            # Neither has C but constant was required
            return {"equivalent": False, "difference": str(d), "tag": "forgot_c"}
        if has_c_a and not has_c_b:
            return {"equivalent": False, "difference": str(d)}

        is_eq = bool(d == 0)
        return {"equivalent": is_eq, "difference": str(d)}

    # require_constant is False (default)
    if d == 0:
        return {"equivalent": True, "difference": "0"}

    # Flag forgot_c if the core expressions match but expected answer includes + C
    if not has_c_a and has_c_b and sp.simplify(pa - pb + C) == 0:
        return {"equivalent": False, "difference": str(d), "tag": "forgot_c"}

    return {"equivalent": False, "difference": str(d)}


def check_equivalence(
    a: str,
    b: str,
    require_constant: bool = False,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict:
    """Authoritative check if two expressions are mathematically equivalent in SymPy.

    Returns:
      {'equivalent': True, 'difference': '0'} or
      {'equivalent': False, 'difference': '...', 'tag': 'forgot_c'} or
      {'error': '...'}
    """
    try:
        return run_with_timeout(
            _check_equivalence_internal,
            a,
            b,
            require_constant=require_constant,
            timeout=timeout,
        )
    except TimeoutError as te:
        return {"error": str(te), "timeout": True, "equivalent": False}
    except Exception as e:
        return {"error": str(e), "equivalent": False}


# ---------------------------------------------------------------------
# Calculus Operations
# ---------------------------------------------------------------------
def _calculus_internal(
    op: str,
    expr: str,
    lower: Optional[Union[str, float, int]] = None,
    upper: Optional[Union[str, float, int]] = None,
    var: str = "x",
    at_x: Optional[Union[str, float, int]] = None,
) -> dict:
    var = _clean(var).strip() if var else "x"
    if not var:
        var = "x"
    e = parse(expr)
    v = _LOCAL_DICT.get(var, sp.symbols(var))

    if op == "diff":
        res = sp.diff(e, v)
        return {"result": str(res)}

    if op in ("diff2", "second_derivative"):
        res = sp.diff(e, v, 2)
        return {"result": str(res), "first_derivative": str(sp.diff(e, v))}

    if op == "integrate":
        res = sp.integrate(e, v)
        return {"result": str(res) + " + C"}

    if op == "definite":
        if lower is None or upper is None:
            raise ValueError(
                "had bawah (lower) dan had atas (upper) diperlukan untuk kamiran tentu"
            )
        # CRITICAL SECURITY FIX: strictly parse bounds via parse(); NEVER raw sp.sympify
        low_val = parse(str(lower))
        up_val = parse(str(upper))
        res = sp.integrate(e, (v, low_val, up_val))
        return {"result": str(sp.simplify(res))}

    if op == "simplify":
        return {"result": str(sp.simplify(e))}

    if op == "tangent":
        if at_x is None:
            raise ValueError("Nilai titik at_x diperlukan untuk garis tangen")
        return tangent(expr, at_x=at_x, var=var)

    if op == "normal":
        if at_x is None:
            raise ValueError("Nilai titik at_x diperlukan untuk garis normal")
        return normal(expr, at_x=at_x, var=var)

    if op == "stationary_points":
        return stationary_points(expr, var=var)

    return {"error": f"op tidak diketahui: {op}"}


def calculus(
    op: str,
    expr: str,
    lower: Optional[Union[str, float, int]] = None,
    upper: Optional[Union[str, float, int]] = None,
    var: str = "x",
    at_x: Optional[Union[str, float, int]] = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict:
    """Execute symbolic calculus operations (diff, integrate, definite, simplify, etc.)."""
    var = _clean(var).strip() if var else "x"
    if not var:
        var = "x"
    try:
        return run_with_timeout(
            _calculus_internal,
            op,
            expr,
            lower=lower,
            upper=upper,
            var=var,
            at_x=at_x,
            timeout=timeout,
        )
    except TimeoutError as te:
        return {"error": str(te), "timeout": True}
    except Exception as ex:
        return {"error": str(ex)}


# ---------------------------------------------------------------------
# Expanded Mathematical Operations
# ---------------------------------------------------------------------
def _second_derivative_internal(expr: str, var: str = "x") -> dict:
    var = _clean(var).strip() if var else "x"
    if not var:
        var = "x"
    e = parse(expr)
    v = _LOCAL_DICT.get(var, sp.symbols(var))
    d1 = sp.diff(e, v)
    d2 = sp.diff(e, v, 2)
    return {
        "result": str(sp.simplify(d2)),
        "first_derivative": str(sp.simplify(d1)),
        "second_derivative": str(sp.simplify(d2)),
    }


def second_derivative(
    expr: str, var: str = "x", timeout: float = DEFAULT_TIMEOUT_SECONDS
) -> dict:
    """Calculate the first and second derivative of an expression."""
    var = _clean(var).strip() if var else "x"
    if not var:
        var = "x"
    try:
        return run_with_timeout(
            _second_derivative_internal, expr, var=var, timeout=timeout
        )
    except TimeoutError as te:
        return {"error": str(te), "timeout": True}
    except Exception as ex:
        return {"error": str(ex)}


def _tangent_internal(
    expr: str, at_x: Union[str, float, int], var: str = "x"
) -> dict:
    var = _clean(var).strip() if var else "x"
    if not var:
        var = "x"
    e = parse(expr)
    v = _LOCAL_DICT.get(var, sp.symbols(var))
    x0 = parse(str(at_x))

    d1 = sp.diff(e, v)
    m = sp.simplify(d1.subs(v, x0))
    y0 = sp.simplify(e.subs(v, x0))

    # Tangent line: y - y0 = m*(x - x0) => y = m*x + (y0 - m*x0)
    c_line = sp.simplify(y0 - m * x0)
    line_expr = sp.simplify(m * v + c_line)

    return {
        "gradient": str(m),
        "point": f"({x0}, {y0})",
        "x0": str(x0),
        "y0": str(y0),
        "equation": f"y = {line_expr}",
        "line_expr": str(line_expr),
        "result": f"y = {line_expr}",
    }


def tangent(
    expr: str,
    at_x: Union[str, float, int],
    var: str = "x",
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict:
    """Calculate tangent line equation and gradient to curve at point x = at_x."""
    var = _clean(var).strip() if var else "x"
    if not var:
        var = "x"
    try:
        return run_with_timeout(
            _tangent_internal, expr, at_x, var=var, timeout=timeout
        )
    except TimeoutError as te:
        return {"error": str(te), "timeout": True}
    except Exception as ex:
        return {"error": str(ex)}


def _normal_internal(
    expr: str, at_x: Union[str, float, int], var: str = "x"
) -> dict:
    var = _clean(var).strip() if var else "x"
    if not var:
        var = "x"
    e = parse(expr)
    v = _LOCAL_DICT.get(var, sp.symbols(var))
    x0 = parse(str(at_x))

    d1 = sp.diff(e, v)
    m_t = sp.simplify(d1.subs(v, x0))
    y0 = sp.simplify(e.subs(v, x0))

    # Check for horizontal tangent (vertical normal line)
    if m_t == 0:
        return {
            "gradient": "undefined",
            "tangent_gradient": "0",
            "point": f"({x0}, {y0})",
            "x0": str(x0),
            "y0": str(y0),
            "equation": f"{var} = {x0}",
            "line_expr": str(x0),
            "result": f"{var} = {x0}",
        }

    m_n = sp.simplify(-1 / m_t)
    c_line = sp.simplify(y0 - m_n * x0)
    line_expr = sp.simplify(m_n * v + c_line)

    return {
        "gradient": str(m_n),
        "tangent_gradient": str(m_t),
        "point": f"({x0}, {y0})",
        "x0": str(x0),
        "y0": str(y0),
        "equation": f"y = {line_expr}",
        "line_expr": str(line_expr),
        "result": f"y = {line_expr}",
    }


def normal(
    expr: str,
    at_x: Union[str, float, int],
    var: str = "x",
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict:
    """Calculate normal line equation and gradient to curve at point x = at_x."""
    var = _clean(var).strip() if var else "x"
    if not var:
        var = "x"
    try:
        return run_with_timeout(
            _normal_internal, expr, at_x, var=var, timeout=timeout
        )
    except TimeoutError as te:
        return {"error": str(te), "timeout": True}
    except Exception as ex:
        return {"error": str(ex)}


def _stationary_points_internal(expr: str, var: str = "x") -> dict:
    var = _clean(var).strip() if var else "x"
    if not var:
        var = "x"
    e = parse(expr)
    v = _LOCAL_DICT.get(var, sp.symbols(var))
    d1 = sp.diff(e, v)
    d2 = sp.diff(e, v, 2)

    # Solve dy/dx = 0
    roots = sp.solve(d1, v)
    points_list: List[Dict[str, Any]] = []

    for r_val in roots:
        y_val = sp.simplify(e.subs(v, r_val))
        d2_val = sp.simplify(d2.subs(v, r_val))

        nature = "unknown"
        nature_ms = "tidak diketahui"
        if d2_val.is_number:
            if d2_val > 0:
                nature = "minimum"
                nature_ms = "titik minimum"
            elif d2_val < 0:
                nature = "maximum"
                nature_ms = "titik maksimum"
            else:
                nature = "inflection"
                nature_ms = "titik lengkok balas"

        points_list.append({
            "x": str(r_val),
            "y": str(y_val),
            "point": f"({r_val}, {y_val})",
            "second_derivative_value": str(d2_val),
            "nature": nature,
            "nature_ms": nature_ms,
        })

    return {
        "points": points_list,
        "count": len(points_list),
        "first_derivative": str(sp.simplify(d1)),
        "second_derivative": str(sp.simplify(d2)),
        "result": points_list,
    }


def stationary_points(
    expr: str, var: str = "x", timeout: float = DEFAULT_TIMEOUT_SECONDS
) -> dict:
    """Find stationary (turning) points of f(x) and classify as minimum, maximum, or inflection."""
    var = _clean(var).strip() if var else "x"
    if not var:
        var = "x"
    try:
        return run_with_timeout(
            _stationary_points_internal, expr, var=var, timeout=timeout
        )
    except TimeoutError as te:
        return {"error": str(te), "timeout": True}
    except Exception as ex:
        return {"error": str(ex)}


def _quadratic_analysis_internal(expr: str, var: str = "x") -> dict:
    var = _clean(var).strip() if var else "x"
    if not var:
        var = "x"
    # Handle equation format: 'lhs = rhs'
    if "=" in expr:
        parts = expr.split("=", 1)
        e = parse(parts[0]) - parse(parts[1])
    else:
        e = parse(expr)

    v = _LOCAL_DICT.get(var, sp.symbols(var))
    poly = sp.Poly(e, v)

    if poly.degree() != 2:
        return {
            "error": f"Bukan ungkapan kuadratik (darjah={poly.degree()})",
            "is_quadratic": False,
        }

    a_coef = poly.coeff_monomial(v**2)
    b_coef = poly.coeff_monomial(v)
    c_coef = poly.coeff_monomial(1)

    disc = sp.simplify(b_coef**2 - 4 * a_coef * c_coef)
    roots = [str(r_val) for r_val in sp.solve(e, v)]

    # Determine nature of roots (SPM KSSM criteria)
    if disc.is_number:
        if disc > 0:
            nature = "two_real_distinct"
            nature_ms = "dua punca nyata dan berbeza"
        elif disc == 0:
            nature = "two_equal_roots"
            nature_ms = "dua punca nyata yang sama"
        else:
            nature = "no_real_roots"
            nature_ms = "tiada punca nyata"
    else:
        nature = "symbolic"
        nature_ms = "simbolik"

    # Axis of symmetry & vertex (h, k)
    h_val = sp.simplify(-b_coef / (2 * a_coef))
    k_val = sp.simplify(e.subs(v, h_val))

    optimum_type = "minimum" if a_coef > 0 else "maximum"
    optimum_type_ms = "nilai minimum" if a_coef > 0 else "nilai maksimum"

    return {
        "is_quadratic": True,
        "a": str(a_coef),
        "b": str(b_coef),
        "c": str(c_coef),
        "discriminant": str(disc),
        "roots": roots,
        "nature_of_roots": nature,
        "nature_of_roots_ms": nature_ms,
        "axis_of_symmetry": f"{var} = {h_val}",
        "vertex": f"({h_val}, {k_val})",
        "vertex_h": str(h_val),
        "vertex_k": str(k_val),
        "optimum_type": optimum_type,
        "optimum_type_ms": optimum_type_ms,
        "optimum_value": str(k_val),
        "result": {
            "discriminant": str(disc),
            "roots": roots,
            "vertex": f"({h_val}, {k_val})",
        },
    }


def quadratic_analysis(
    expr: str, var: str = "x", timeout: float = DEFAULT_TIMEOUT_SECONDS
) -> dict:
    """Analyze a quadratic expression or equation (discriminant, roots, vertex, symmetry)."""
    var = _clean(var).strip() if var else "x"
    if not var:
        var = "x"
    try:
        return run_with_timeout(
            _quadratic_analysis_internal, expr, var=var, timeout=timeout
        )
    except TimeoutError as te:
        return {"error": str(te), "timeout": True}
    except Exception as ex:
        return {"error": str(ex)}


# ---------------------------------------------------------------------
# Syllabus Knowledge Base (Preserved)
# ---------------------------------------------------------------------
SYLLABUS = {
    "ind": "Hukum indeks: a^m*a^n=a^(m+n); a^m/a^n=a^(m-n); (a^m)^n=a^(mn).",
    "quad": "f(x)=ax^2+bx+c: paksi simetri x=-b/2a; verteks (−b/2a, f(−b/2a)); diskriminan b^2-4ac.",
    "dif": "Petua kuasa: d/dx(ax^n)=anx^(n-1); pemalar jadi 0; bx jadi b; kecerunan tangen = f'(k).",
    "integ": "∫ax^n dx = a x^(n+1)/(n+1) + C; kamiran tentu: ganti had atas tolak had bawah; jangan lupa +C bagi kamiran tak tentu.",
}


def get_syllabus(topic: str) -> dict:
    """Retrieve KSSM Additional Mathematics syllabus notes for topic code."""
    return {"notes": SYLLABUS.get(topic, "tiada nota")}


# ---------------------------------------------------------------------
# Tool Specifications (Anthropic Function-Calling Format)
# ---------------------------------------------------------------------
TOOL_SPECS = [
    {
        "name": "check_equivalence",
        "description": "Check if two algebraic expressions are mathematically equal (SymPy). Use to verify the student's answer against the correct one.",
        "input_schema": {
            "type": "object",
            "properties": {
                "a": {"type": "string", "description": "Student or first expression"},
                "b": {"type": "string", "description": "Correct or expected expression"},
                "require_constant": {
                    "type": "boolean",
                    "description": "Whether to enforce constant of integration (+ C)",
                },
            },
            "required": ["a", "b"],
        },
    },
    {
        "name": "calculus",
        "description": "Differentiate, integrate (indefinite/definite), or simplify an expression using SymPy.",
        "input_schema": {
            "type": "object",
            "properties": {
                "op": {
                    "type": "string",
                    "enum": [
                        "diff",
                        "integrate",
                        "definite",
                        "simplify",
                        "second_derivative",
                        "tangent",
                        "normal",
                        "stationary_points",
                    ],
                },
                "expr": {"type": "string"},
                "lower": {"type": "string"},
                "upper": {"type": "string"},
                "var": {"type": "string"},
                "at_x": {"type": "string"},
            },
            "required": ["op", "expr"],
        },
    },
    {
        "name": "get_syllabus",
        "description": "Retrieve KSSM Additional Mathematics notes for a topic id (ind, quad, dif, integ).",
        "input_schema": {
            "type": "object",
            "properties": {"topic": {"type": "string"}},
            "required": ["topic"],
        },
    },
    {
        "name": "quadratic_analysis",
        "description": "Analyze a quadratic expression: calculate discriminant (b^2 - 4ac), roots, vertex (h, k), and axis of symmetry.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expr": {"type": "string"},
                "var": {"type": "string"},
            },
            "required": ["expr"],
        },
    },
    {
        "name": "tangent_normal",
        "description": "Find tangent or normal line equation and gradient to a curve at a given x point.",
        "input_schema": {
            "type": "object",
            "properties": {
                "op": {"type": "string", "enum": ["tangent", "normal"]},
                "expr": {"type": "string"},
                "at_x": {"type": "string"},
                "var": {"type": "string"},
            },
            "required": ["op", "expr", "at_x"],
        },
    },
    {
        "name": "stationary_points",
        "description": "Find stationary (turning) points of f(x) and classify as minimum, maximum, or inflection.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expr": {"type": "string"},
                "var": {"type": "string"},
            },
            "required": ["expr"],
        },
    },
]


# ---------------------------------------------------------------------
# Dynamic Tool Dispatcher (Preserved & Enhanced)
# ---------------------------------------------------------------------
def run_tool(name: str, args: dict) -> dict:
    """Execute tool by name with dictionary arguments. Fully backward compatible."""
    if not isinstance(args, dict):
        args = {}

    if name == "check_equivalence":
        return check_equivalence(
            str(args.get("a", args.get("expr_a", ""))),
            str(args.get("b", args.get("expr_b", ""))),
            require_constant=bool(args.get("require_constant", False)),
        )

    if name == "calculus":
        return calculus(
            str(args.get("op", "")),
            str(args.get("expr", "")),
            lower=args.get("lower"),
            upper=args.get("upper"),
            var=str(args.get("var", "x")),
            at_x=args.get("at_x"),
        )

    if name == "get_syllabus":
        return get_syllabus(str(args.get("topic", "")))

    if name in ("quadratic_analysis", "quadratic"):
        return quadratic_analysis(
            str(args.get("expr", "")),
            var=str(args.get("var", "x")),
        )

    if name in ("tangent_normal", "tangent", "normal"):
        op = str(args.get("op", name if name in ("tangent", "normal") else "tangent"))
        at_x = args.get("at_x")
        if at_x is None:
            return {"error": "Parameter 'at_x' diperlukan"}
        if op == "normal":
            return normal(
                str(args.get("expr", "")),
                at_x=at_x,
                var=str(args.get("var", "x")),
            )
        return tangent(
            str(args.get("expr", "")),
            at_x=at_x,
            var=str(args.get("var", "x")),
        )

    if name == "stationary_points":
        return stationary_points(
            str(args.get("expr", "")),
            var=str(args.get("var", "x")),
        )

    return {"error": "tool tidak wujud"}
