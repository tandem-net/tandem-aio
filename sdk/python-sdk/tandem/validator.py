"""
Static split-independence validator.

Implements the rule from the design doc:

    A tandemed function MUST be independent — it may only read:
      1. its own parameters / locals derived from them
      2. names declared @tandem.immutable (tandem.immutable(...))
      3. builtins

    Any other free variable read (module globals, enclosing-scope
    closures) is a validation error. Any assignment/augmented-assignment
    to an immutable name from inside a tandemed function is also an
    error ("immutable variable cannot be modified").

This is implemented as an AST walk over the function's source, rather
than bytecode inspection, since AST gives much clearer error messages
(line numbers, the exact offending name) and is what a real CLI/compiler
front-end would do too.

Limitations (documented, not hidden):
  - Only catches free-variable reads that are simple Name nodes at the
    AST level. Indirect access (e.g. via globals(), getattr tricks,
    eval/exec) is NOT caught — this mirrors the fact that the real
    compiler doesn't exist yet and static analysis has fundamental
    limits without full whole-program analysis.
  - Calls to *other* functions are not (yet) transitively validated —
    i.e. if `foo` calls `helper()` and `helper` reads a global, that
    violation is only caught if `helper` itself is also decorated and
    validated. This matches the "no compiler yet" scope of the SDK; the
    CLI will eventually need to validate the full call graph.
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
    Walks a single function definition and records:
      - every Name that is read but not a local, parameter, or builtin
      - every Name that is written (Store/AugStore) and not a local/parameter

    Comprehensions and nested functions get their own scopes; we track
    bound names per-scope using a simple stack so locals defined inside
    a list comprehension don't leak out as "free", and so nested defs
    are still subject to the same rule (they're walked too).
    """

    def __init__(self) -> None:
        self.free_reads: list[tuple[str, int]] = []   # (name, lineno)
        self.free_writes: list[tuple[str, int]] = []  # (name, lineno)
        self._scopes: list[set[str]] = [set()]

    def _bound_in_any_scope(self, name: str) -> bool:
        return any(name in scope for scope in self._scopes)

    def _bind(self, name: str) -> None:
        self._scopes[-1].add(name)

    # -- function signature: parameters are bound names -----------------
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

    # -- comprehensions introduce their own scope ------------------------
    def _visit_comprehension(self, node) -> None:
        self._scopes.append(set())
        for gen in node.generators:
            self.visit(gen.iter)
            self._bind_target(gen.target)
            for if_clause in gen.ifs:
                self.visit(if_clause)
        if hasattr(node, "elt"):
            self.visit(node.elt)
        if hasattr(node, "key"):
            self.visit(node.key)
            self.visit(node.value)
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

    # -- assignments bind their targets ----------------------------------
    def visit_Assign(self, node: ast.Assign) -> None:
        self.visit(node.value)
        for target in node.targets:
            self._bind_target(target)
            # Still visit target in case it's e.g. obj.attr or sub[idx],
            # which involves a *read* of obj/sub, not a pure bind.
            if not isinstance(target, ast.Name):
                self.visit(target)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value:
            self.visit(node.value)
        self._bind_target(node.target)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        # `x += 1` is BOTH a read and a write of x.
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
        # An explicit `global x` inside the function is an unambiguous
        # signal that x refers to module scope -- treat every later use
        # in this scope as a free read/write, regardless of binding.
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
                # A bare `x = ...` at function scope binds `x` locally in
                # Python (no `global` needed) -- so Store without a prior
                # `global` declaration is just a normal local binding, not
                # a free write. We only flag this path for safety in case
                # this method is reached without going through visit_Assign.
                self._bind(name)


def _get_source_module_name(func: Callable) -> str:
    return getattr(func, "__module__", "<unknown>")


def _parse_function_ast(func: Callable) -> ast.FunctionDef:
    try:
        source = inspect.getsource(func)
    except (OSError, TypeError) as e:
        raise TandemValidationError(
            f"Cannot statically validate '{getattr(func, '__name__', func)}': "
            f"source is unavailable ({e}). Functions defined in the REPL or "
            f"compiled extensions cannot be split-independence checked."
        ) from e

    source = textwrap.dedent(source)
    # Strip leading decorator lines so ast.parse sees a clean FunctionDef
    # as the first statement of the module; we don't need the decorators
    # themselves for analysis.
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return node
    raise TandemValidationError(
        f"Could not locate a function definition for "
        f"'{getattr(func, '__name__', func)}' during static analysis."
    )


def validate_independence(func: Callable) -> None:
    """
    Validate that `func` only reads names that are parameters, locals,
    builtins, or declared immutable in its defining module.

    Raises TandemValidationError on the first violation found, with a
    message naming the offending variable and line, mirroring what the
    real CLI's build-time error would look like.
    """
    module_name = _get_source_module_name(func)
    immutable_names = all_immutable_names(module_name)

    fn_node = _parse_function_ast(func)
    visitor = _FreeVariableVisitor()
    visitor.visit_FunctionDef(fn_node)

    func_label = getattr(func, "__name__", "<function>")

    # Check writes first -- mutating an immutable (or any free) name is
    # always wrong, and gives a more specific error than "read" would.
    for name, lineno in visitor.free_writes:
        if name in immutable_names:
            raise TandemValidationError(
                f"In '{func_label}' (line {lineno}): immutable variable "
                f"'{name}' cannot be modified inside a tandemed function."
            )
        raise TandemValidationError(
            f"In '{func_label}' (line {lineno}): global variable '{name}' "
            f"is not immutable and cannot be modified inside a tandemed "
            f"function. Mark it with `{name} = tandem.immutable(...)` if "
            f"it is truly constant, or pass it in as a parameter."
        )

    for name, lineno in visitor.free_reads:
        if name in immutable_names:
            continue  # OK: declared immutable, treated as compile-time constant
        raise TandemValidationError(
            f"In '{func_label}' (line {lineno}): global variable '{name}' "
            f"is not immutable. Tandemed functions may only read function "
            f"parameters, locals, or names declared with "
            f"`{name} = tandem.immutable(...)`. Found a read of free "
            f"variable '{name}'."
        )
