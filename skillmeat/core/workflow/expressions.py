"""SWDL expression parser and evaluator for ``${{ }}`` syntax.

Implements a recursive descent parser for the SkillMeat Workflow Definition
Language (SWDL) expression language. Expressions are embedded in YAML string
fields and resolved at workflow execution time against a runtime context.

Typical usage::

    from skillmeat.core.workflow.expressions import (
        ExpressionContext,
        ExpressionParser,
        ExpressionError,
    )

    ctx = ExpressionContext(
        parameters={"feature_name": "auth-v2"},
        stages={
            "research": {
                "outputs": {"summary": "done"},
                "status": "completed",
            }
        },
    )

    parser = ExpressionParser()

    # Evaluate a single expression string
    value = parser.evaluate("parameters.feature_name", ctx)   # "auth-v2"

    # Resolve all ${{ }} placeholders in a template string
    text = parser.resolve_string(
        "Feature: ${{ parameters.feature_name }}", ctx
    )  # "Feature: auth-v2"

Supported syntax:
    - Property access:   ``parameters.x``, ``stages.s.outputs.k``
    - Comparisons:       ``==``, ``!=``, ``<``, ``>``, ``<=``, ``>=``
    - Boolean ops:       ``&&``, ``||``, ``!``
    - Ternary:           ``a ? b : c``
    - String literals:   ``'hello'``, ``"world"``
    - Number literals:   ``42``, ``3.14``
    - Boolean literals:  ``true``, ``false``
    - Null literal:      ``null``
    - Built-in calls:    ``length(x)``, ``contains(s, sub)``,
                         ``toJSON(x)``, ``fromJSON(s)``
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, List, Optional, Union


# ---------------------------------------------------------------------------
# Public error type
# ---------------------------------------------------------------------------


class ExpressionError(Exception):
    """Raised when an expression cannot be parsed or evaluated.

    Attributes:
        message:    Human-readable description of the failure.
        expression: The raw expression text that caused the failure.
    """

    def __init__(self, message: str, expression: str = "") -> None:
        self.message = message
        self.expression = expression
        detail = f"{message} (in expression: {expression!r})" if expression else message
        super().__init__(detail)


# ---------------------------------------------------------------------------
# Runtime evaluation context
# ---------------------------------------------------------------------------


@dataclass
class ExpressionContext:
    """Holds the runtime state available to SWDL expression evaluation.

    All attributes default to empty collections so that callers only need to
    populate the namespaces they actually use.

    Attributes:
        parameters: Workflow-level parameters supplied by the caller at
                    execution time.  Accessed via ``parameters.<name>``.
        stages:     Per-stage runtime state keyed by stage id.  Each value
                    is a dict that may contain ``outputs`` (dict) and
                    ``status`` (str).  Accessed via
                    ``stages.<id>.outputs.<key>`` or ``stages.<id>.status``.
        context:    Arbitrary context key/value pairs.  Accessed via
                    ``context.<key>``.
        env:        Environment variables.  Accessed via ``env.<name>``.
        run:        Current run metadata (e.g. run id, start time).
                    Accessed via ``run.<key>``.
        workflow:   Workflow-level metadata.  Accessed via
                    ``workflow.<key>``.
    """

    parameters: dict[str, Any] = field(default_factory=dict)
    stages: dict[str, dict[str, Any]] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    env: dict[str, str] = field(default_factory=dict)
    run: dict[str, Any] = field(default_factory=dict)
    workflow: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# AST node types
# ---------------------------------------------------------------------------


@dataclass
class Literal:
    """An atomic constant: string, number, bool, or null.

    Attributes:
        value: The Python value of the literal.
    """

    value: Any


@dataclass
class PropertyAccess:
    """A dot-separated property path resolved against the context.

    Examples::

        parameters.feature_name      -> path = ["parameters", "feature_name"]
        stages.research.outputs.key  -> path = ["stages", "research", "outputs", "key"]

    Attributes:
        path: Ordered list of path segments.
    """

    path: List[str]


@dataclass
class UnaryOp:
    """A unary operator applied to a single operand.

    Currently only ``!`` (logical not) is supported.

    Attributes:
        op:      The operator symbol (``"!"``).
        operand: The expression the operator is applied to.
    """

    op: str
    operand: "ASTNode"


@dataclass
class BinaryOp:
    """A binary operator applied to two operands.

    Supported operators: ``==``, ``!=``, ``<``, ``>``, ``<=``, ``>=``,
    ``&&``, ``||``.

    Attributes:
        op:    The operator symbol.
        left:  Left-hand operand expression.
        right: Right-hand operand expression.
    """

    op: str
    left: "ASTNode"
    right: "ASTNode"


@dataclass
class Ternary:
    """A conditional ternary expression (``condition ? then : else``).

    Attributes:
        condition: Boolean expression to evaluate.
        then:      Value when condition is truthy.
        else_:     Value when condition is falsy.
    """

    condition: "ASTNode"
    then: "ASTNode"
    else_: "ASTNode"


@dataclass
class FunctionCall:
    """A call to a built-in function.

    Supported functions: ``length``, ``contains``, ``toJSON``, ``fromJSON``.

    Attributes:
        name: Function name (case-sensitive).
        args: Positional argument expressions.
    """

    name: str
    args: List["ASTNode"]


# Union type alias for all AST nodes.
ASTNode = Union[Literal, PropertyAccess, UnaryOp, BinaryOp, Ternary, FunctionCall]


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

# Token kinds
_TK_IDENT = "IDENT"
_TK_STRING = "STRING"
_TK_NUMBER = "NUMBER"
_TK_OP = "OP"
_TK_LPAREN = "LPAREN"
_TK_RPAREN = "RPAREN"
_TK_COMMA = "COMMA"
_TK_DOT = "DOT"
_TK_QUESTION = "QUESTION"
_TK_COLON = "COLON"
_TK_EOF = "EOF"

# Ordered token patterns (longest match first for multi-char operators).
_TOKEN_PATTERNS: List[tuple[str, str]] = [
    (_TK_STRING, r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\''),
    (_TK_NUMBER, r"-?(?:\d+\.\d+|\d+)"),
    (_TK_OP, r"==|!=|<=|>=|&&|\|\||[!<>]"),
    (_TK_LPAREN, r"\("),
    (_TK_RPAREN, r"\)"),
    (_TK_COMMA, r","),
    (_TK_DOT, r"\."),
    (_TK_QUESTION, r"\?"),
    (_TK_COLON, r":"),
    (_TK_IDENT, r"[A-Za-z_][A-Za-z0-9_-]*"),
]

_MASTER_RE = re.compile(
    "|".join(f"(?P<{kind}>{pat})" for kind, pat in _TOKEN_PATTERNS)
)

_EXPRESSION_RE = re.compile(r"\$\{\{\s*(.*?)\s*\}\}", re.DOTALL)


@dataclass
class _Token:
    kind: str
    value: str


def _tokenize(text: str, expression: str = "") -> List[_Token]:
    """Convert an expression string into a flat token list.

    Args:
        text:       The expression text to tokenize.
        expression: Original expression (for error messages).

    Returns:
        List of ``_Token`` objects terminated by a single ``_TK_EOF`` token.

    Raises:
        ExpressionError: On unrecognized characters.
    """
    tokens: List[_Token] = []
    pos = 0
    while pos < len(text):
        # Skip whitespace
        if text[pos].isspace():
            pos += 1
            continue
        m = _MASTER_RE.match(text, pos)
        if not m:
            raise ExpressionError(
                f"Unexpected character {text[pos]!r} at position {pos}",
                expression,
            )
        kind = m.lastgroup
        assert kind is not None
        tokens.append(_Token(kind=kind, value=m.group()))
        pos = m.end()
    tokens.append(_Token(kind=_TK_EOF, value=""))
    return tokens


# ---------------------------------------------------------------------------
# Recursive descent parser
# ---------------------------------------------------------------------------


class _Parser:
    """Recursive descent parser that produces an ASTNode from token stream.

    Grammar (informal, precedence low → high)::

        expr        = ternary
        ternary     = or_expr ( '?' expr ':' expr )?
        or_expr     = and_expr ( '||' and_expr )*
        and_expr    = equality ( '&&' equality )*
        equality    = relational ( ( '==' | '!=' ) relational )*
        relational  = unary ( ( '<' | '>' | '<=' | '>=' ) unary )*
        unary       = '!' unary | primary
        primary     = literal | function_call | property_access | '(' expr ')'
        literal     = STRING | NUMBER | 'true' | 'false' | 'null'
        function_call  = IDENT '(' ( expr ( ',' expr )* )? ')'
        property_access = IDENT ( '.' IDENT )*
    """

    def __init__(self, tokens: List[_Token], expression: str = "") -> None:
        self._tokens = tokens
        self._pos = 0
        self._expression = expression

    # ------------------------------------------------------------------
    # Low-level helpers
    # ------------------------------------------------------------------

    def _peek(self) -> _Token:
        return self._tokens[self._pos]

    def _advance(self) -> _Token:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def _expect(self, kind: str) -> _Token:
        tok = self._peek()
        if tok.kind != kind:
            raise ExpressionError(
                f"Expected {kind} but got {tok.kind} ({tok.value!r})",
                self._expression,
            )
        return self._advance()

    def _match_op(self, *ops: str) -> Optional[str]:
        tok = self._peek()
        if tok.kind == _TK_OP and tok.value in ops:
            self._advance()
            return tok.value
        return None

    # ------------------------------------------------------------------
    # Grammar rules
    # ------------------------------------------------------------------

    def parse(self) -> ASTNode:
        node = self._expr()
        if self._peek().kind != _TK_EOF:
            tok = self._peek()
            raise ExpressionError(
                f"Unexpected token {tok.value!r} after expression",
                self._expression,
            )
        return node

    def _expr(self) -> ASTNode:
        return self._ternary()

    def _ternary(self) -> ASTNode:
        node = self._or_expr()
        if self._peek().kind == _TK_QUESTION:
            self._advance()  # consume '?'
            then = self._expr()
            self._expect(_TK_COLON)
            else_ = self._expr()
            return Ternary(condition=node, then=then, else_=else_)
        return node

    def _or_expr(self) -> ASTNode:
        node = self._and_expr()
        while self._match_op("||"):
            right = self._and_expr()
            node = BinaryOp(op="||", left=node, right=right)
        return node

    def _and_expr(self) -> ASTNode:
        node = self._equality()
        while self._match_op("&&"):
            right = self._equality()
            node = BinaryOp(op="&&", left=node, right=right)
        return node

    def _equality(self) -> ASTNode:
        node = self._relational()
        op = self._match_op("==", "!=")
        if op:
            right = self._relational()
            node = BinaryOp(op=op, left=node, right=right)
        return node

    def _relational(self) -> ASTNode:
        node = self._unary()
        op = self._match_op("<", ">", "<=", ">=")
        if op:
            right = self._unary()
            node = BinaryOp(op=op, left=node, right=right)
        return node

    def _unary(self) -> ASTNode:
        if self._match_op("!"):
            operand = self._unary()
            return UnaryOp(op="!", operand=operand)
        return self._primary()

    def _primary(self) -> ASTNode:
        tok = self._peek()

        # Grouped expression
        if tok.kind == _TK_LPAREN:
            self._advance()
            node = self._expr()
            self._expect(_TK_RPAREN)
            return node

        # String literal
        if tok.kind == _TK_STRING:
            self._advance()
            raw = tok.value
            # Strip surrounding quotes and process basic escape sequences
            inner = raw[1:-1]
            inner = inner.replace("\\'", "'").replace('\\"', '"').replace("\\\\", "\\")
            return Literal(value=inner)

        # Number literal
        if tok.kind == _TK_NUMBER:
            self._advance()
            text = tok.value
            try:
                value: Union[int, float] = int(text) if "." not in text else float(text)
            except ValueError:
                raise ExpressionError(f"Invalid number literal {text!r}", self._expression)
            return Literal(value=value)

        # Keyword literals and identifiers
        if tok.kind == _TK_IDENT:
            # Boolean / null keywords
            if tok.value == "true":
                self._advance()
                return Literal(value=True)
            if tok.value == "false":
                self._advance()
                return Literal(value=False)
            if tok.value == "null":
                self._advance()
                return Literal(value=None)

            # Function call: IDENT '(' ... ')'
            next_tok = self._tokens[self._pos + 1] if self._pos + 1 < len(self._tokens) else _Token(_TK_EOF, "")
            if next_tok.kind == _TK_LPAREN:
                return self._function_call()

            # Property access: IDENT ( '.' IDENT )*
            return self._property_access()

        raise ExpressionError(
            f"Unexpected token {tok.kind} ({tok.value!r}) in primary expression",
            self._expression,
        )

    def _function_call(self) -> ASTNode:
        name_tok = self._expect(_TK_IDENT)
        self._expect(_TK_LPAREN)
        args: List[ASTNode] = []
        if self._peek().kind != _TK_RPAREN:
            args.append(self._expr())
            while self._peek().kind == _TK_COMMA:
                self._advance()
                args.append(self._expr())
        self._expect(_TK_RPAREN)
        return FunctionCall(name=name_tok.value, args=args)

    def _property_access(self) -> ASTNode:
        first = self._expect(_TK_IDENT)
        path = [first.value]
        while self._peek().kind == _TK_DOT:
            self._advance()  # consume '.'
            segment = self._expect(_TK_IDENT)
            path.append(segment.value)
        return PropertyAccess(path=path)


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------

_BUILTIN_FUNCTIONS = {"length", "contains", "toJSON", "fromJSON"}


def _evaluate_node(node: ASTNode, ctx: ExpressionContext, expression: str = "") -> Any:
    """Recursively evaluate an AST node against the runtime context.

    Args:
        node:       The AST node to evaluate.
        ctx:        The runtime expression context.
        expression: Original expression text (for error messages).

    Returns:
        The Python value produced by the node.

    Raises:
        ExpressionError: On evaluation failures (bad property path, unknown
                         function, type errors).
    """
    if isinstance(node, Literal):
        return node.value

    if isinstance(node, PropertyAccess):
        return _resolve_property(node.path, ctx, expression)

    if isinstance(node, UnaryOp):
        operand_val = _evaluate_node(node.operand, ctx, expression)
        if node.op == "!":
            return not operand_val
        raise ExpressionError(f"Unknown unary operator {node.op!r}", expression)

    if isinstance(node, BinaryOp):
        return _evaluate_binary(node, ctx, expression)

    if isinstance(node, Ternary):
        condition_val = _evaluate_node(node.condition, ctx, expression)
        if condition_val:
            return _evaluate_node(node.then, ctx, expression)
        return _evaluate_node(node.else_, ctx, expression)

    if isinstance(node, FunctionCall):
        return _evaluate_function(node, ctx, expression)

    raise ExpressionError(
        f"Unknown AST node type {type(node).__name__}", expression
    )


def _resolve_property(path: List[str], ctx: ExpressionContext, expression: str) -> Any:
    """Walk a dotted path into the context, returning None on missing keys.

    The first path segment must name a top-level context namespace
    (``parameters``, ``stages``, ``context``, ``env``, ``run``,
    ``workflow``).  Subsequent segments are resolved by successive dict
    key lookups.  Any ``KeyError`` or ``TypeError`` encountered along the
    way returns ``None`` rather than raising, matching GitHub Actions
    semantics for missing expression paths.

    Args:
        path:       Ordered path segments.
        ctx:        The runtime context.
        expression: Original expression text (for error messages).

    Returns:
        The resolved value, or ``None`` if any segment is missing.

    Raises:
        ExpressionError: When the first segment is not a valid namespace.
    """
    if not path:
        raise ExpressionError("Empty property path", expression)

    root_name = path[0]
    root_map: dict[str, Any] = {
        "parameters": ctx.parameters,
        "stages": ctx.stages,
        "context": ctx.context,
        "env": ctx.env,
        "run": ctx.run,
        "workflow": ctx.workflow,
    }

    if root_name not in root_map:
        raise ExpressionError(
            f"Unknown context namespace {root_name!r}. "
            f"Valid namespaces: {sorted(root_map)}",
            expression,
        )

    current: Any = root_map[root_name]
    for segment in path[1:]:
        if current is None:
            return None
        try:
            if isinstance(current, dict):
                current = current[segment]
            else:
                # Support attribute access for non-dict objects (e.g. dataclasses)
                current = getattr(current, segment)
        except (KeyError, AttributeError, TypeError):
            return None
    return current


def _evaluate_binary(node: BinaryOp, ctx: ExpressionContext, expression: str) -> Any:
    op = node.op

    # Short-circuit boolean operators
    if op == "&&":
        left_val = _evaluate_node(node.left, ctx, expression)
        if not left_val:
            return left_val
        return _evaluate_node(node.right, ctx, expression)

    if op == "||":
        left_val = _evaluate_node(node.left, ctx, expression)
        if left_val:
            return left_val
        return _evaluate_node(node.right, ctx, expression)

    left_val = _evaluate_node(node.left, ctx, expression)
    right_val = _evaluate_node(node.right, ctx, expression)

    try:
        if op == "==":
            return left_val == right_val
        if op == "!=":
            return left_val != right_val
        if op == "<":
            return left_val < right_val  # type: ignore[operator]
        if op == ">":
            return left_val > right_val  # type: ignore[operator]
        if op == "<=":
            return left_val <= right_val  # type: ignore[operator]
        if op == ">=":
            return left_val >= right_val  # type: ignore[operator]
    except TypeError as exc:
        raise ExpressionError(
            f"Cannot compare {type(left_val).__name__!r} and "
            f"{type(right_val).__name__!r} with {op!r}: {exc}",
            expression,
        ) from exc

    raise ExpressionError(f"Unknown binary operator {op!r}", expression)


def _evaluate_function(
    node: FunctionCall, ctx: ExpressionContext, expression: str
) -> Any:
    """Dispatch a built-in function call.

    Supported functions:

    ``length(x)``
        Returns ``len(x)`` for lists, strings, and dicts.

    ``contains(s, sub)``
        Returns ``sub in s`` for strings (substring check) and
        lists (membership check).

    ``toJSON(x)``
        Serializes ``x`` to a JSON string using ``json.dumps``.

    ``fromJSON(s)``
        Parses a JSON string ``s`` using ``json.loads``.

    Args:
        node:       The FunctionCall AST node.
        ctx:        The runtime context.
        expression: Original expression text (for error messages).

    Returns:
        The function result.

    Raises:
        ExpressionError: On unknown function names or argument errors.
    """
    name = node.name
    if name not in _BUILTIN_FUNCTIONS:
        raise ExpressionError(
            f"Unknown function {name!r}. "
            f"Available functions: {sorted(_BUILTIN_FUNCTIONS)}",
            expression,
        )

    evaluated_args = [_evaluate_node(arg, ctx, expression) for arg in node.args]

    if name == "length":
        if len(evaluated_args) != 1:
            raise ExpressionError(
                f"length() expects 1 argument, got {len(evaluated_args)}", expression
            )
        try:
            return len(evaluated_args[0])
        except TypeError as exc:
            raise ExpressionError(
                f"length() argument has no length: {exc}", expression
            ) from exc

    if name == "contains":
        if len(evaluated_args) != 2:
            raise ExpressionError(
                f"contains() expects 2 arguments, got {len(evaluated_args)}", expression
            )
        container, item = evaluated_args
        try:
            return item in container
        except TypeError as exc:
            raise ExpressionError(
                f"contains() type error: {exc}", expression
            ) from exc

    if name == "toJSON":
        if len(evaluated_args) != 1:
            raise ExpressionError(
                f"toJSON() expects 1 argument, got {len(evaluated_args)}", expression
            )
        try:
            return json.dumps(evaluated_args[0])
        except (TypeError, ValueError) as exc:
            raise ExpressionError(
                f"toJSON() serialization error: {exc}", expression
            ) from exc

    if name == "fromJSON":
        if len(evaluated_args) != 1:
            raise ExpressionError(
                f"fromJSON() expects 1 argument, got {len(evaluated_args)}", expression
            )
        try:
            return json.loads(evaluated_args[0])
        except (TypeError, ValueError) as exc:
            raise ExpressionError(
                f"fromJSON() parse error: {exc}", expression
            ) from exc

    # Should be unreachable given the name guard above
    raise ExpressionError(f"Unhandled function {name!r}", expression)  # pragma: no cover


# ---------------------------------------------------------------------------
# Public ExpressionParser class
# ---------------------------------------------------------------------------


class ExpressionParser:
    """Parse and evaluate SWDL ``${{ }}`` expressions.

    This class is the primary public interface for expression handling.
    An instance is stateless and safe to reuse across many evaluations.

    Example::

        parser = ExpressionParser()
        ctx = ExpressionContext(parameters={"env": "prod"})

        # Low-level: parse to AST
        ast = parser.parse("parameters.env == 'prod'")

        # Mid-level: evaluate a raw expression string
        result = parser.evaluate("parameters.env == 'prod'", ctx)  # True

        # High-level: resolve all ${{ }} placeholders in a template
        text = parser.resolve_string(
            "Deploying to ${{ parameters.env }}", ctx
        )  # "Deploying to prod"
    """

    # ------------------------------------------------------------------
    # Expression extraction
    # ------------------------------------------------------------------

    def extract_expressions(self, text: str) -> List[str]:
        """Find and return all ``${{ expr }}`` expression strings in *text*.

        The returned strings are the raw expression bodies, with leading and
        trailing whitespace stripped, and without the surrounding
        ``${{ }}`` delimiters.

        Args:
            text: A YAML string value or other text possibly containing
                  one or more ``${{ expr }}`` placeholders.

        Returns:
            List of expression strings in the order they appear in *text*.
            Empty list if no expressions are found.

        Example::

            parser.extract_expressions(
                "Hello ${{ parameters.name }}, status: ${{ stages.s.status }}"
            )
            # ["parameters.name", "stages.s.status"]
        """
        return [m.group(1).strip() for m in _EXPRESSION_RE.finditer(text)]

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def parse(self, expression: str) -> ASTNode:
        """Parse an expression string into an AST.

        Does **not** evaluate the expression — use :meth:`evaluate` for
        combined parse + evaluate.

        Args:
            expression: The raw expression body (without ``${{ }}``).

        Returns:
            The root AST node.

        Raises:
            ExpressionError: If the expression cannot be parsed.

        Example::

            ast = parser.parse("parameters.feature == 'auth'")
            # BinaryOp(op='==', left=PropertyAccess(['parameters', 'feature']),
            #          right=Literal('auth'))
        """
        stripped = expression.strip()
        try:
            tokens = _tokenize(stripped, expression)
            p = _Parser(tokens, expression)
            return p.parse()
        except ExpressionError:
            raise
        except Exception as exc:
            raise ExpressionError(
                f"Parse error: {exc}", expression
            ) from exc

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, expression: str, ctx: ExpressionContext) -> Any:
        """Parse and evaluate an expression against a runtime context.

        Args:
            expression: The raw expression body (without ``${{ }}``).
            ctx:        The runtime evaluation context.

        Returns:
            The Python value produced by evaluating the expression.

        Raises:
            ExpressionError: If the expression cannot be parsed or evaluated.

        Example::

            ctx = ExpressionContext(parameters={"skip": False})
            parser.evaluate("parameters.skip == false", ctx)  # True
        """
        ast = self.parse(expression)
        try:
            return _evaluate_node(ast, ctx, expression)
        except ExpressionError:
            raise
        except Exception as exc:
            raise ExpressionError(
                f"Evaluation error: {exc}", expression
            ) from exc

    # ------------------------------------------------------------------
    # String resolution
    # ------------------------------------------------------------------

    def resolve_string(self, text: str, ctx: ExpressionContext) -> str:
        """Replace all ``${{ expr }}`` placeholders in *text* with evaluated values.

        Each placeholder is evaluated independently against *ctx* and its
        result is converted to a string via ``str()`` before substitution.
        Non-string results (numbers, booleans, dicts, lists) are converted
        using Python's default ``str()`` representation.  Use
        ``toJSON(x)`` inside the expression for JSON-formatted output.

        If *text* contains no ``${{ }}`` placeholders it is returned
        unchanged.

        Args:
            text: A template string potentially containing one or more
                  ``${{ expr }}`` placeholders.
            ctx:  The runtime evaluation context.

        Returns:
            The template string with all placeholders replaced.

        Raises:
            ExpressionError: If any placeholder expression fails to parse
                             or evaluate.

        Example::

            ctx = ExpressionContext(
                parameters={"name": "auth-v2"},
                stages={"build": {"status": "completed"}},
            )
            parser.resolve_string(
                "Feature ${{ parameters.name }} — build: ${{ stages.build.status }}",
                ctx,
            )
            # "Feature auth-v2 — build: completed"
        """

        def _replace(match: re.Match) -> str:  # type: ignore[type-arg]
            expr_body = match.group(1).strip()
            value = self.evaluate(expr_body, ctx)
            if value is None:
                return ""
            if isinstance(value, bool):
                # Use lowercase to match SWDL / JSON conventions
                return "true" if value else "false"
            return str(value)

        return _EXPRESSION_RE.sub(_replace, text)
