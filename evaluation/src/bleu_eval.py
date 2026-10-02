import ast
import re
import keyword
import tokenize
import io
from typing import Any

# ---------------------------------------------------------------------------
# Custom Tokenizer
# ---------------------------------------------------------------------------

# Python built-ins and keywords for semantic classification
_KEYWORDS    = set(keyword.kwlist)
_BUILTINS    = set(dir(__builtins__)) if isinstance(__builtins__, dict) else set(dir(__builtins__))
_OPS         = set("+-*/%&|^~<>=!@")
_DELIMITERS  = set("()[]{},:;.")

# Semantic token prefixes that encode meaning into the token string itself,
# allowing the codebleu n-gram model to reward structurally similar code.
_PREFIX = {
    "keyword":    "KW",     # if / for / return / def / class …
    "builtin":    "BI",     # len / print / range / isinstance …
    "name":       "ID",     # user-defined identifiers
    "number":     "NUM",    # numeric literals
    "string":     "STR",    # string literals
    "operator":   "OP",     # + - * == != …
    "delimiter":  "DL",     # ( ) [ ] { } , : . ;
    "comment":    "CM",     # inline comments
    "decorator":  "DC",     # @decorator names
    "type_hint":  "TH",     # annotations / type hints
    "fstring":    "FS",     # f-string bodies
    "walrus":     "WA",     # := (walrus operator)
    "unknown":    "UK",
}


def _classify_name(name: str) -> str:
    """Return the semantic prefix for a bare identifier."""
    if name in _KEYWORDS:
        return _PREFIX["keyword"]
    if name in _BUILTINS:
        return _PREFIX["builtin"]
    return _PREFIX["name"]


def _extract_type_hints(code: str) -> set[int]:
    """
    Return the set of token positions (line, col) that are type annotations,
    by walking the AST and recording annotation node positions.
    """
    hint_positions: set[tuple[int, int]] = set()
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return hint_positions

    for node in ast.walk(tree):
        # Function argument annotations and return annotations
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
                if arg.annotation:
                    hint_positions.add((arg.annotation.lineno, arg.annotation.col_offset))
            if node.returns:
                hint_positions.add((node.returns.lineno, node.returns.col_offset))
        # Variable annotations  (x: int = 5)
        if isinstance(node, ast.AnnAssign) and node.annotation:
            hint_positions.add((node.annotation.lineno, node.annotation.col_offset))

    return hint_positions


def _extract_decorators(code: str) -> set[tuple[int, int]]:
    """Return (line, col) positions of decorator name nodes."""
    positions: set[tuple[int, int]] = set()
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return positions
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            for dec in node.decorator_list:
                positions.add((dec.lineno, dec.col_offset))
    return positions


def intelligent_tokenize(code: str) -> list[str]:
    """
    Tokenize Python source into semantically-prefixed token strings.

    Each returned token has the form  PREFIX_value, e.g.:
        KW_return   - the keyword `return`
        BI_len      - the builtin `len`
        ID_my_var   - a user-defined name
        NUM_42      - a numeric literal
        STR         - any string literal (value elided for normalisation)
        OP_==       - an operator
        DL_(        - a delimiter
        TH_int      - a type-hint name
        DC_property - a decorator name
        FS          - an f-string
        WA_:=       - walrus operator
        CM          - a comment (content elided)

    Value elision for STR / FS / CM prevents spurious mismatches on
    literal content that carries no structural signal.
    """
    hint_positions  = _extract_type_hints(code)
    dec_positions   = _extract_decorators(code)
    tokens: list[str] = []

    try:
        token_stream = tokenize.generate_tokens(io.StringIO(code).readline)
        for tok_type, tok_str, (srow, scol), _, _ in token_stream:
            pos = (srow, scol)

            # ---- skip noise ------------------------------------------------
            if tok_type in (tokenize.NEWLINE, tokenize.NL,
                            tokenize.INDENT, tokenize.DEDENT,
                            tokenize.ENCODING, tokenize.ENDMARKER):
                continue

            # ---- comments --------------------------------------------------
            if tok_type == tokenize.COMMENT:
                tokens.append(_PREFIX["comment"])
                continue

            # ---- string literals (including f-strings) ---------------------
            if tok_type == tokenize.STRING:
                if tok_str.startswith(("f'", 'f"', "f'''", 'f"""',
                                       "F'", 'F"', "F'''", 'F"""')):
                    tokens.append(_PREFIX["fstring"])
                else:
                    tokens.append(_PREFIX["string"])
                continue

            # ---- numeric literals ------------------------------------------
            if tok_type == tokenize.NUMBER:
                tokens.append(f"{_PREFIX['number']}_{tok_str}")
                continue

            # ---- operators -------------------------------------------------
            if tok_type == tokenize.OP:
                if tok_str == ":=":
                    tokens.append(f"{_PREFIX['walrus']}_{tok_str}")
                elif tok_str in _DELIMITERS:
                    tokens.append(f"{_PREFIX['delimiter']}_{tok_str}")
                else:
                    tokens.append(f"{_PREFIX['operator']}_{tok_str}")
                continue

            # ---- names (keywords, builtins, identifiers) -------------------
            if tok_type == tokenize.NAME:
                # Decorator?
                if pos in dec_positions:
                    tokens.append(f"{_PREFIX['decorator']}_{tok_str}")
                    continue
                # Type hint?
                if pos in hint_positions:
                    tokens.append(f"{_PREFIX['type_hint']}_{tok_str}")
                    continue
                tokens.append(f"{_classify_name(tok_str)}_{tok_str}")
                continue

            # ---- fallback --------------------------------------------------
            tokens.append(f"{_PREFIX['unknown']}_{tok_str}")

    except tokenize.TokenError:
        # Incomplete or malformed code — fall back to simple split
        tokens = re.findall(r"[A-Za-z_]\w*|[^\w\s]|\d+", code)

    return tokens


# ---------------------------------------------------------------------------
# CodeBLEU via library + custom tokenizer
# ---------------------------------------------------------------------------

def calculate_codebleu_scores(
    snippets: list[str],
    reference: str,
    weights: tuple[float, float, float, float] = (0.25, 0.25, 0.25, 0.25),
) -> list[dict[str, Any]]:
    """
    Calculate CodeBLEU scores for each snippet against a single reference,
    using the `codebleu` library driven by an intelligent custom tokenizer.

    The custom tokenizer enriches every token with a semantic prefix so that
    the library's n-gram and weighted-ngram passes reward structurally similar
    code (matching keywords, builtins, operators, type hints, decorators) more
    strongly than coincidental identifier overlap.

    Parameters
    ----------
    snippets  : list of candidate Python code strings.
    reference : ground-truth / reference Python code string.
    weights   : (w_ngram, w_weighted_ngram, w_syntax, w_dataflow)
                All four must sum to 1.0.

    Returns
    -------
    List (same order/length as `snippets`) of dicts:
        {
            "codebleu":          float,
            "ngram_bleu":        float,
            "weighted_ngram":    float,
            "syntax_match":      float,
            "dataflow_match":    float,
        }
    """
    try:
        from codebleu import calc_codebleu
    except ImportError as exc:
        raise ImportError(
            "The `codebleu` package is required: pip install codebleu"
        ) from exc

    if abs(sum(weights) - 1.0) > 1e-6:
        raise ValueError(f"weights must sum to 1.0, got {sum(weights):.6f}")

    results = []
    ref_tokens = intelligent_tokenize(reference)

    for snippet in snippets:
        hyp_tokens = intelligent_tokenize(snippet)

        # calc_codebleu accepts pre-tokenized inputs when passed as lists.
        # We pass the tokenized forms for the n-gram / weighted-ngram
        # components and the raw strings for AST / data-flow components.
        raw = calc_codebleu(
            references=[[reference]],
            predictions=[snippet],
            lang="python",
            weights=weights,
            tokenizer=intelligent_tokenize,
        )

        results.append({
            "codebleu":       round(raw["codebleu"],            6),
            "ngram_bleu":     round(raw["ngram_match_score"],   6),
            "weighted_ngram": round(raw["weighted_ngram_match_score"], 6),
            "syntax_match":   round(raw["syntax_match_score"],  6),
            "dataflow_match": round(raw["dataflow_match_score"], 6),
        })

    return results