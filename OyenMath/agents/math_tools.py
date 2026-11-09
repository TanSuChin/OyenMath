"""Deterministic math tools (SymPy) exposed to the LLM agents. The LLM never decides correctness alone."""
import re
import sympy as sp
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application, convert_xor

x, y, C = sp.symbols("x y C")
_TR = standard_transformations + (implicit_multiplication_application, convert_xor)
_ALLOWED_NAMES = {"x", "y", "C", "c", "pi", "e", "sin", "cos", "tan", "ln", "sqrt", "dx", "dy"}
_SUPD = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")
_SUP = str.maketrans("−×·", "-**")


def _clean(s: str) -> str:
    s = re.sub(r"[⁰¹²³⁴⁵⁶⁷⁸⁹]+", lambda m: "^" + m.group().translate(_SUPD), str(s)).translate(_SUP).replace("′", "").replace("∫", "")
    s = re.sub(r"\b(f\s*\(x\)|dy\s*/\s*dx|y)\s*=", "", s, flags=re.I)
    s = re.sub(r"\+\s*[cC]\b", "", s)  # constant of integration is checked separately
    return s.strip()


def parse(s: str):
    s = _clean(s)
    if len(s) > 120 or not re.fullmatch(r"[0-9a-zA-Z+\-*/^().\s]+", s or ""):
        raise ValueError("ungkapan tidak sah")
    for tok in re.findall(r"[A-Za-z]+", s):
        if tok not in _ALLOWED_NAMES and not re.fullmatch(r"[xyC]+", tok):
            raise ValueError("nama tidak dibenarkan: " + tok)
    return parse_expr(s, transformations=_TR, local_dict={"x": x, "y": y, "C": C, "e": sp.E, "pi": sp.pi, "ln": sp.log})


def check_equivalence(a: str, b: str) -> dict:
    try:
        d = sp.simplify(parse(a) - parse(b))
        return {"equivalent": bool(d == 0), "difference": str(d)}
    except Exception as e:
        return {"error": str(e)}


def calculus(op: str, expr: str, lower=None, upper=None) -> dict:
    try:
        e = parse(expr)
        if op == "diff":
            return {"result": str(sp.diff(e, x))}
        if op == "integrate":
            return {"result": str(sp.integrate(e, x)) + " + C"}
        if op == "definite":
            return {"result": str(sp.integrate(e, (x, sp.sympify(lower), sp.sympify(upper))))}
        if op == "simplify":
            return {"result": str(sp.simplify(e))}
        return {"error": "op tidak diketahui"}
    except Exception as ex:
        return {"error": str(ex)}


SYLLABUS = {
    "ind": "Hukum indeks: a^m*a^n=a^(m+n); a^m/a^n=a^(m-n); (a^m)^n=a^(mn).",
    "quad": "f(x)=ax^2+bx+c: paksi simetri x=-b/2a; verteks (−b/2a, f(−b/2a)); diskriminan b^2-4ac.",
    "dif": "Petua kuasa: d/dx(ax^n)=anx^(n-1); pemalar jadi 0; bx jadi b; kecerunan tangen = f'(k).",
    "integ": "∫ax^n dx = a x^(n+1)/(n+1) + C; kamiran tentu: ganti had atas tolak had bawah; jangan lupa +C bagi kamiran tak tentu.",
}


def get_syllabus(topic: str) -> dict:
    return {"notes": SYLLABUS.get(topic, "tiada nota")}


TOOL_SPECS = [
    {"name": "check_equivalence", "description": "Check if two algebraic expressions are mathematically equal (SymPy). Use to verify the student's answer against the correct one.",
     "input_schema": {"type": "object", "properties": {"a": {"type": "string"}, "b": {"type": "string"}}, "required": ["a", "b"]}},
    {"name": "calculus", "description": "Differentiate, integrate (indefinite/definite) or simplify an expression in x using SymPy.",
     "input_schema": {"type": "object", "properties": {"op": {"type": "string", "enum": ["diff", "integrate", "definite", "simplify"]}, "expr": {"type": "string"}, "lower": {"type": "string"}, "upper": {"type": "string"}}, "required": ["op", "expr"]}},
    {"name": "get_syllabus", "description": "Retrieve KSSM Additional Mathematics notes for a topic id (ind, quad, dif, integ).",
     "input_schema": {"type": "object", "properties": {"topic": {"type": "string"}}, "required": ["topic"]}},
]


def run_tool(name: str, args: dict) -> dict:
    if name == "check_equivalence":
        return check_equivalence(args.get("a", ""), args.get("b", ""))
    if name == "calculus":
        return calculus(args.get("op", ""), args.get("expr", ""), args.get("lower"), args.get("upper"))
    if name == "get_syllabus":
        return get_syllabus(args.get("topic", ""))
    return {"error": "tool tidak wujud"}
