"""
Split-independence validator.

A tandem task should be independent: running it on one node must give the same
answer as running it on any other. The compiler freezes the task's whole module
into its WASM component, so a task may freely *read* module globals -- helper
functions, imports, constants -- because every node runs the same frozen copy.

The one thing that breaks independence is *writing* to a module global and
expecting the change to be shared: each node has its own isolated copy, so the
write goes nowhere the other nodes can see. That's what this validator flags.
(Writing to a name declared `tandem.immutable(...)` is likewise an error.)

This runs at decoration time (inside @tandem.compute and tandem.split) so
violations surface immediately when the module is imported, rather than at build
or first call.
"""

from __future__ import annotations

import ast
import builtins
import inspect
import textwrap
from typing import Callable

from tandem.errors import TandemValidationError
from tandem.immutable import all_immutable_names

_BUILTIN_NAMES = set(dir(builtins))


class _FreeVariableVisitor(ast.NodeVisitor):
    """
    Walk a function definition and collect every Name node that is read
    or written without being bound as a local/parameter in the function's
    own scope.

    Scope stack tracks:
      - function parameters
      - local assignments (including loop variables, with-targets,
        comprehension variables)
      - nested function/comprehension scopes (each gets its own frame)
    """

    def __init__(self) -> None:
        self.free_reads: list[tuple[str, int]] = []
        self.free_writes: list[tuple[str, int]] = []
        self._scopes: list[set[str]] = [set()]

    def _bound_in_any_scope(self, name: str) -> bool:
        return any(name in scope for scope in self._scopes)

    def _bind(self, name: str) -> None:
        self._scopes[-1].add(name)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._scopes.append(set())
        args = node.args
        for a in (*args.posonlyargs, *args.args, *args.kwonlyargs):
            self._bind(a.arg)
        if args.vararg:
            self._bind(args.vararg.arg)
        if args.kwarg:
            self._bind(args.kwarg.arg)
        for stmt in node.body:
            self.visit(stmt)
        self._scopes.pop()

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    def _visit_comprehension(self, node: ast.AST) -> None:
        self._scopes.append(set())
        for gen in node.generators:  # type: ignore[attr-defined]
            self.visit(gen.iter)
            self._bind_target(gen.target)
            for if_clause in gen.ifs:
                self.visit(if_clause)
        if hasattr(node, "elt"):
            self.visit(node.elt)  # type: ignore[attr-defined]
        if hasattr(node, "key"):
            self.visit(node.key)  # type: ignore[attr-defined]
            self.visit(node.value)  # type: ignore[attr-defined]
        self._scopes.pop()

    visit_ListComp = _visit_comprehension
    visit_SetComp = _visit_comprehension
    visit_GeneratorExp = _visit_comprehension
    visit_DictComp = _visit_comprehension

    def _bind_target(self, target: ast.AST) -> None:
        if isinstance(target, ast.Name):
            self._bind(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._bind_target(elt)
        elif isinstance(target, ast.Starred):
            self._bind_target(target.value)

    def visit_Assign(self, node: ast.Assign) -> None:
        self.visit(node.value)
        for target in node.targets:
            self._bind_target(target)
            if not isinstance(target, ast.Name):
                self.visit(target)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value:
            self.visit(node.value)
        self._bind_target(node.target)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        # x += 1 is both a read and a write.
        self.visit(node.value)
        if isinstance(node.target, ast.Name):
            name = node.target.id
            if not self._bound_in_any_scope(name):
                self.free_reads.append((name, node.lineno))
                self.free_writes.append((name, node.lineno))
            self._bind(name)
        else:
            self.visit(node.target)

    def visit_For(self, node: ast.For) -> None:
        self.visit(node.iter)
        self._bind_target(node.target)
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.orelse:
            self.visit(stmt)

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars:
                self._bind_target(item.optional_vars)
        for stmt in node.body:
            self.visit(stmt)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        self._scopes.append(set())
        for a in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
            self._bind(a.arg)
        self.visit(node.body)
        self._scopes.pop()

    def visit_Global(self, node: ast.Global) -> None:
        # Explicit `global x` is an unambiguous free-variable declaration.
        for name in node.names:
            self.free_reads.append((name, node.lineno))

    def visit_Name(self, node: ast.Name) -> None:
        name = node.id
        if name in _BUILTIN_NAMES:
            return
        if isinstance(node.ctx, ast.Load):
            if not self._bound_in_any_scope(name):
                self.free_reads.append((name, node.lineno))
        elif isinstance(node.ctx, (ast.Store, ast.Del)):
            if not self._bound_in_any_scope(name):
                self._bind(name)


def _parse_function_ast(func: Callable) -> ast.FunctionDef:
    try:
        source = inspect.getsource(func)
    except (OSError, TypeError) as e:
        raise TandemValidationError(
            f"Cannot validate '{getattr(func, '__name__', func)}': source "
            f"unavailable ({e}). Functions defined in the REPL or compiled "
            f"extensions cannot be statically checked."
        ) from e

    tree = ast.parse(textwrap.dedent(source))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return node  # type: ignore[return-value]

    raise TandemValidationError(
        f"Could not locate a function definition for "
        f"'{getattr(func, '__name__', func)}' in parsed source."
    )


def validate_independence(func: Callable) -> None:
    """
    Check that a task doesn't try to mutate shared module-level state.

    The compiler freezes the task's whole module into its WASM component, so
    *reading* module globals -- helper functions, imports, constants -- is
    perfectly fine: every node runs the same frozen copy, so everyone sees the
    same values. What doesn't make sense for a distributed task is *writing* to a
    module global and expecting the change to be shared, because each node has
    its own isolated copy. So that's the one thing we flag.

    Raises TandemValidationError on the first write to a module global, naming
    the offending variable and line number.
    """
    module_name = getattr(func, "__module__", "<unknown>")
    immutable_names = all_immutable_names(module_name)

    fn_node = _parse_function_ast(func)
    visitor = _FreeVariableVisitor()
    visitor.visit_FunctionDef(fn_node)

    label = getattr(func, "__name__", "<function>")

    for name, lineno in visitor.free_writes:
        if name in immutable_names:
            raise TandemValidationError(
                f"In '{label}' (line {lineno}): "
                f"immutable variable '{name}' cannot be modified inside a tandem task."
            )
        raise TandemValidationError(
            f"In '{label}' (line {lineno}): "
            f"global variable '{name}' cannot be modified inside a tandem task -- "
            f"each node runs its own frozen copy, so the change wouldn't be shared. "
            f"Use a parameter and return the result instead."
        )


# ---------------------------------------------------------------------------
# WASM-compatible type validation (runs at build time)
# ---------------------------------------------------------------------------

# Primitive types that map cleanly to the WASM Component Model.
_WASM_SCALAR_NAMES: set[str] = {"int", "float", "bool", "str", "bytes"}

# Generic container origins that are allowed when their type parameters
# are themselves WASM-compatible.
_WASM_CONTAINER_NAMES: set[str] = {"list", "List", "dict", "Dict", "tuple", "Tuple"}


def _annotation_source(node: ast.expr) -> str:
    """Recover a human-readable string from an annotation AST node."""
    try:
        return ast.unparse(node)
    except Exception:
        return "<unknown>"


def _is_wasm_compatible_annotation(node: ast.expr) -> bool:
    """
    Return True when *node* represents a type annotation that the
    Tandem builder can lower to WASM Component Model types.

    Allowed forms:
        int, float, bool, str, bytes
        list[T], dict[K, V], tuple[T, ...]
        None (for return-type void)
    """
    # ``None`` literal — used as a void return annotation.
    if isinstance(node, ast.Constant) and node.value is None:
        return True

    # Plain name: ``int``, ``str``, etc.
    if isinstance(node, ast.Name):
        return node.id in _WASM_SCALAR_NAMES or node.id == "None"

    # Subscript: ``list[int]``, ``dict[str, int]``, ``tuple[int, ...]``
    if isinstance(node, ast.Subscript):
        origin = node.value
        if not isinstance(origin, ast.Name):
            return False
        if origin.id not in _WASM_CONTAINER_NAMES:
            return False
        # Check type parameters
        slice_node = node.slice
        if isinstance(slice_node, ast.Tuple):
            return all(_is_wasm_compatible_annotation(elt) for elt in slice_node.elts)
        return _is_wasm_compatible_annotation(slice_node)

    # BinOp with ``|`` — union syntax (e.g. ``int | None``)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return (
            _is_wasm_compatible_annotation(node.left)
            and _is_wasm_compatible_annotation(node.right)
        )

    return False


def validate_wasm_types(func: Callable) -> list[str]:
    """
    Check that *func*'s parameter and return-type annotations use only
    types that the Tandem builder can lower to WASM Component Model
    interface types.

    Returns a list of human-readable **warning** strings for missing
    annotations and raises ``TandemValidationError`` for annotations
    that cannot be compiled.
    """
    fn_node = _parse_function_ast(func)
    label = getattr(func, "__name__", "<function>")
    warnings: list[str] = []

    # --- check parameter annotations ---
    all_args = [
        *fn_node.args.posonlyargs,
        *fn_node.args.args,
        *fn_node.args.kwonlyargs,
    ]
    if fn_node.args.vararg:
        all_args.append(fn_node.args.vararg)
    if fn_node.args.kwarg:
        all_args.append(fn_node.args.kwarg)

    for arg_node in all_args:
        ann = arg_node.annotation
        if ann is None:
            warnings.append(
                f"In '{label}': parameter '{arg_node.arg}' has no type annotation. "
                f"Tandem will infer types at runtime, but explicit annotations "
                f"are recommended for WASM compilation."
            )
            continue
        if not _is_wasm_compatible_annotation(ann):
            raise TandemValidationError(
                f"In '{label}' (line {arg_node.lineno}): parameter "
                f"'{arg_node.arg}' has annotation '{_annotation_source(ann)}' "
                f"which cannot be compiled to WASM. Allowed types: "
                f"int, float, bool, str, bytes, list[T], dict[K,V], tuple[T,...]."
            )

    # --- check return annotation ---
    ret = fn_node.returns
    if ret is None:
        warnings.append(
            f"In '{label}': missing return type annotation. "
            f"Tandem will infer the return type at runtime."
        )
    elif not _is_wasm_compatible_annotation(ret):
        raise TandemValidationError(
            f"In '{label}' (line {fn_node.lineno}): return annotation "
            f"'{_annotation_source(ret)}' cannot be compiled to WASM. "
            f"Allowed types: int, float, bool, str, bytes, list[T], dict[K,V], "
            f"tuple[T,...], None."
        )

    return warnings

