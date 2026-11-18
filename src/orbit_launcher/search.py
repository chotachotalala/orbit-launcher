"""Local ranking and calculator without eval, network calls or arbitrary code."""

import ast
import math
import operator
from difflib import SequenceMatcher

from .models import Entry

EN = "`qwertyuiop[]asdfghjkl;'zxcvbnm,."
RU = "ёйцукенгшщзхъфывапролджэячсмитьбю"
LAYOUTS = (str.maketrans(EN, RU), str.maketrans(RU, EN))


def normalize(text: str) -> str:
    return text.casefold().replace("ё", "е").strip()


def search(entries: list[Entry], query: str, mode: str = "all") -> list[Entry]:
    query = normalize(query)
    variants = {query, *(normalize(query.translate(t)) for t in LAYOUTS)}
    ranked = []
    for entry in entries:
        if mode == "favorites" and not entry.favorite:
            continue
        if mode == "recent" and not entry.last_used:
            continue
        if mode in {"app", "folder", "file", "url"} and entry.kind != mode:
            continue
        name, aliases = normalize(entry.name), normalize(entry.aliases)
        score = 0.0
        for variant in variants:
            if not query:
                score = 1
            elif variant == name:
                score = max(score, 120)
            elif name.startswith(variant):
                score = max(score, 95)
            elif variant in name:
                score = max(score, 75)
            elif variant in aliases:
                score = max(score, 65)
            elif all(token in f"{name} {aliases}" for token in variant.split()):
                score = max(score, 55)
            elif len(variant) >= 3:
                similarity = SequenceMatcher(None, variant, name).ratio()
                if similarity >= 0.62:
                    score = max(score, similarity * 45)
        if score:
            usage = min(entry.launches, 20) * 0.15
            boost = 8 if entry.favorite else 0
            ranked.append((score + usage + boost, entry))
    if mode == "recent" and not query:
        return sorted((e for _, e in ranked), key=lambda e: e.last_used, reverse=True)
    return [e for _, e in sorted(ranked, key=lambda pair: (-pair[0], normalize(pair[1].name)))]


OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}


def calculate(text: str) -> str | None:
    """Return a formatted number, or None for unsupported/oversized expressions."""
    text = text.strip().removeprefix("=").strip().replace(",", ".")
    if not text or len(text) > 180 or not any(c in text for c in "+-*/%"):
        return None
    try:
        tree = ast.parse(text, mode="eval")
        if sum(1 for _ in ast.walk(tree)) > 70:
            return None

        def visit(node):
            if isinstance(node, ast.Constant) and type(node.value) in {int, float}:
                value = node.value
            elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
                value = visit(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1)
            elif isinstance(node, ast.BinOp) and type(node.op) in OPS:
                left, right = visit(node.left), visit(node.right)
                if isinstance(node.op, ast.Pow) and (abs(right) > 12 or abs(left) > 1e10):
                    raise ValueError
                value = OPS[type(node.op)](left, right)
            else:
                raise ValueError
            if type(value) not in {int, float} or not math.isfinite(value) or abs(value) > 1e15:
                raise ValueError
            return value

        result = visit(tree.body)
        return f"{result:.12g}"
    except (ValueError, TypeError, SyntaxError, ArithmeticError, RecursionError):
        return None
