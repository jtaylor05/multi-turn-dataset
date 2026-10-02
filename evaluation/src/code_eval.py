import ast
import contextlib, faulthandler, io, math
import multiprocessing, os, platform, re, subprocess, sys, threading
import tempfile, time, tqdm

from typing import Dict, Optional, List, Any
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed


def _combinations(n: int, k: int) -> float:
    """C(n, k) — returns 0.0 for invalid inputs instead of raising."""
    if k < 0 or k > n:
        return 0.0
    return math.comb(n, k)


def _pass_at_k_unbiased(n: int, c: int, k: int) -> float:
    """
    Unbiased estimator for pass@k.

    Parameters
    ----------
    n : total number of completions sampled
    c : number of completions that passed all tests
    k : the k in pass@k
    """
    if n < k:
        raise ValueError(f"k={k} cannot exceed n={n} (total samples).")
    if c > n:
        raise ValueError(f"c={c} (passing) cannot exceed n={n} (total).")
    if n == 0:
        return 0.0
    # Numerically stable: 1 - C(n-c, k) / C(n, k)
    num = _combinations(n - c, k)
    den = _combinations(n, k)
    if den == 0:
        return 1.0
    return 1.0 - num / den


# ---------------------------------------------------------------------------
# pytest-style test-suite detection & entry-point name resolution
#
# Two independent problems these solve:
#   1. Some test_cases are pytest-style (fixtures, @pytest.mark.*, `class
#      Test...`, several standalone `test_*` functions with no self-
#      invocation). Those can't be exec'd inline the way a self-contained
#      "def check(): ...; check()" script can -- they need to be written to
#      a file and collected/run by pytest itself.
#   2. The function name a test suite expects to call ("constraints_to_check"
#      in the dataset's final_ground_truth) may not match the name the
#      candidate `code` actually defines. We resolve this by aliasing rather
#      than guessing blindly.
# ---------------------------------------------------------------------------

_PYTEST_MARKERS = re.compile(
    r"^\s*(import pytest\b|from pytest\b|@pytest\.|class\s+Test\w*\s*[:(])",
    re.MULTILINE,
)


def _is_pytest_style(test_cases: str) -> bool:
    """Heuristically detect pytest-style test code (imports, markers, Test classes)."""
    return bool(_PYTEST_MARKERS.search(test_cases))


def _top_level_function_names(code: str) -> List[str]:
    """Names of all top-level (async) function defs in `code`. [] if unparsable."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    return [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def _resolve_entry_point(code: str, expected_name: str) -> Dict[str, Any]:
    """
    Determine how to make `expected_name` callable against `code`.

    Returns either:
        {"ok": True,  "alias_line": Optional[str]}
            alias_line is None if expected_name is already defined verbatim,
            otherwise a line like "expected_name = actual_name" to append.
        {"ok": False, "reason": str}
            could not resolve unambiguously; caller should skip this problem
            rather than guess and silently corrupt the pass/fail signal.
    """
    names = _top_level_function_names(code)
    
    names = [n for n in names if not n.startswith("_")]

    if expected_name in names:
        return {"ok": True, "alias_line": None}

    if not names:
        return {"ok": False, "reason": "no top-level functions found in code"}

    if len(names) == 1:
        return {"ok": True, "alias_line": f"{expected_name} = {names[0]}"}

    # Simple attempt: does exactly one candidate's name contain (or get
    # contained by) the expected name, ignoring case/underscores? e.g.
    # expected "topological_sort" matching a candidate
    # "topological_sort_with_times".
    def _norm(s: str) -> str:
        return s.lower().replace("_", "")

    expected_norm = _norm(expected_name)
    contains_matches = [
        n for n in names if expected_norm in _norm(n) or _norm(n) in expected_norm
    ]

    if len(contains_matches) == 1:
        return {"ok": True, "alias_line": f"{expected_name} = {contains_matches[0]}"}

    return {
        "ok": False,
        "reason": (
            f"ambiguous entry point: {len(names)} candidate function(s) found "
            f"({', '.join(names)}), none uniquely matches '{expected_name}'"
        ),
    }


def _run_pytest_case(script_text: str, timeout: float) -> Dict[str, Any]:
    """Write `script_text` to a temp file and run it under pytest as a subprocess."""
    start = time.perf_counter()
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "test_solution.py")
        with open(path, "w") as f:
            f.write(script_text)
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", path, "-q", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            passed = proc.returncode == 0
            result = "passed" if passed else (proc.stdout + proc.stderr)[-4000:]
        except subprocess.TimeoutExpired:
            passed, result = False, "timed out"
        except Exception as e:  # defensive: never let this crash the batch
            passed, result = False, f"error running pytest: {e}"
    exe_time = time.perf_counter() - start
    return {"passed": passed, "result": result, "exe_time": exe_time}


# ---------------------------------------------------------------------------
# Sandboxed execution
# ---------------------------------------------------------------------------


def unsafe_execute(code: str, timeout: float, result, maximum_memory_bytes: Optional[int] = None, with_guard: bool = True):
    with create_tempdir():

        # These system calls are needed when cleaning up tempdir.
        import os
        import shutil

        rmtree = shutil.rmtree
        rmdir = os.rmdir
        chdir = os.chdir

        check_program = code

        try:
            if with_guard:
                # Disable functionalities that can make destructive changes to
                # the test, and cap memory if requested. Kept inside the try
                # block so a guard failure is reported as a normal "failed:"
                # result instead of crashing the child process before it can
                # append anything -- which check_correctness would otherwise
                # silently mislabel as "timed out".
                reliability_guard(maximum_memory_bytes=maximum_memory_bytes)

            exec_globals: Dict[str, Any] = {}
            with swallow_io():
                start = time.perf_counter()
                with time_limit(timeout + 2.0):
                    # WARNING
                    # This program exists to execute untrusted model-generated code. Although
                    # it is highly unlikely that model-generated code will do something overtly
                    # malicious in response to this test suite, model-generated code may act
                    # destructively due to a lack of model capability or alignment.
                    # Users are strongly encouraged to sandbox this evaluation suite so that it
                    # does not perform destructive actions on their host or network. For more
                    # information on how OpenAI sandboxes its code, see the accompanying paper.
                    # Once you have read this disclaimer and taken appropriate precautions,
                    # uncomment the following line and proceed at your own risk:
                    exec(check_program, exec_globals)
            end = time.perf_counter()
            result.append(("passed", end - start))
        except TimeoutException:
            result.append(("timed out", timeout))
        except BaseException as e:
            result.append((f"failed: {e}", -1))

        # Needed for cleaning up.
        shutil.rmtree = rmtree
        os.rmdir = rmdir
        os.chdir = chdir


def check_correctness(
    code: str,
    timeout: float,
    completion_id: Optional[int] = None,
    manager: Optional["multiprocessing.managers.SyncManager"] = None,
    maximum_memory_bytes: Optional[int] = None,
) -> Dict:
    """
    Evaluates the functional correctness of a completion by running the test
    suite provided in the problem.

    :param manager: an existing multiprocessing.Manager to host the shared
        result list. Pass one in when calling this many times (e.g. from
        evaluate_functional_correctness) so we don't fork a new Manager
        server process per sample. If omitted, a manager is created and
        torn down locally (fine for one-off calls).
    :param completion_id: an optional completion ID so we can match
        the results later even if execution finishes asynchronously.
    """
    owns_manager = manager is None
    if owns_manager:
        manager = multiprocessing.Manager()

    try:
        result = manager.list()

        p = multiprocessing.Process(
            target=unsafe_execute, args=(code, timeout, result, maximum_memory_bytes)
        )
        p.start()
        p.join(timeout=timeout + 1)
        if p.is_alive():
            p.kill()
            p.join()  # reap the process so it doesn't linger as a zombie

        if not result:
            result.append(("timed out", -1))

        return dict(
            code=code,
            passed=result[0][0] == "passed",
            result=result[0][0],
            completion_id=completion_id,
            exe_time=result[0][1],
        )
    finally:
        if owns_manager:
            manager.shutdown()


@contextlib.contextmanager
def time_limit(seconds: float):
    def signal_handler():
        raise TimeoutException("Timed out!")
    timer = threading.Timer(seconds, signal_handler)
    timer.start()
    try:
        yield
    finally:
        timer.cancel()


@contextlib.contextmanager
def swallow_io():
    stream = WriteOnlyStringIO()
    with contextlib.redirect_stdout(stream):
        with contextlib.redirect_stderr(stream):
            with redirect_stdin(stream):
                yield


@contextlib.contextmanager
def create_tempdir():
    with tempfile.TemporaryDirectory() as dirname:
        with chdir(dirname):
            yield dirname


class TimeoutException(Exception):
    pass


class WriteOnlyStringIO(io.StringIO):
    """StringIO that throws an exception when it's read from"""

    def read(self, *args, **kwargs):
        raise IOError

    def readline(self, *args, **kwargs):
        raise IOError

    def readlines(self, *args, **kwargs):
        raise IOError

    def readable(self, *args, **kwargs):
        """Returns True if the IO object can be read."""
        return False


class redirect_stdin(contextlib._RedirectStream):  # type: ignore
    _stream = "stdin"


@contextlib.contextmanager
def chdir(root):
    if root == ".":
        yield
        return
    cwd = os.getcwd()
    os.chdir(root)
    try:
        yield
    except BaseException as exc:
        raise exc
    finally:
        os.chdir(cwd)


def reliability_guard(maximum_memory_bytes: Optional[int] = None):
    """
    This disables various destructive functions and prevents the generated code
    from interfering with the test (e.g. fork bomb, killing other processes,
    removing filesystem files, etc.)

    WARNING
    This function is NOT a security sandbox. Untrusted code, including, model-
    generated code, should not be blindly executed outside of one. See the
    Codex paper for more information about OpenAI's code sandbox, and proceed
    with caution.
    """

    if maximum_memory_bytes is not None:
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (maximum_memory_bytes, maximum_memory_bytes))
        resource.setrlimit(resource.RLIMIT_DATA, (maximum_memory_bytes, maximum_memory_bytes))
        if not platform.uname().system == "Darwin":
            resource.setrlimit(resource.RLIMIT_STACK, (maximum_memory_bytes, maximum_memory_bytes))

    faulthandler.disable()

    import builtins

    builtins.exit = None
    builtins.quit = None

    import os

    os.environ["OMP_NUM_THREADS"] = "1"

    os.kill = None
    os.system = None
    os.putenv = None
    os.remove = None
    os.removedirs = None
    os.rmdir = None
    os.fchdir = None
    os.setuid = None
    os.fork = None
    os.forkpty = None
    os.killpg = None
    os.rename = None
    os.renames = None
    os.truncate = None
    os.replace = None
    os.unlink = None
    os.fchmod = None
    os.fchown = None
    os.chmod = None
    os.chown = None
    os.chroot = None
    os.fchdir = None
    os.lchflags = None
    os.lchmod = None
    os.lchown = None
    os.getcwd = None
    os.chdir = None

    import shutil

    shutil.rmtree = None
    shutil.move = None
    shutil.chown = None

    import subprocess

    subprocess.Popen = None  # type: ignore

    # __builtins__ is a dict in imported modules but the *module* object
    # itself when the running script is __main__ -- handle both so this
    # doesn't raise TypeError and get mistaken for a timeout upstream.
    if isinstance(__builtins__, dict):
        __builtins__["help"] = None
    else:
        __builtins__.help = None

    import sys

    sys.modules["ipdb"] = None
    sys.modules["joblib"] = None
    sys.modules["resource"] = None
    sys.modules["psutil"] = None
    sys.modules["tkinter"] = None


# ---------------------------------------------------------------------------
# pass@k over many completions of ONE problem
# ---------------------------------------------------------------------------


def evaluate_functional_correctness(
    code_list: List[str],
    test_cases: str,
    entry_point: str,
    constraints_to_check: Optional[List[str]] = None,
    k: List[int] = [1, 10, 100],
    n_workers: int = 4,
    timeout: float = 3.0,
    maximum_memory_bytes: Optional[int] = None,
) -> Dict:
    """
    Evaluates the functional correctness of generated samples based on
    test_cases and entry_point and returns the results and pass@k scores.

    All `code_list` entries are assumed to be candidate solutions for the
    SAME problem (this is what makes pass@k meaningful here).

    Delegates execution to evaluate_functional_correctness_batch so both
    functions share one code path: pytest-style test_cases, entry-point
    name aliasing (via `constraints_to_check`), and applicable/skip
    handling now all apply here too, and every candidate runs under one
    shared Manager/ThreadPoolExecutor instead of one spun up per candidate.
    """
    problems = [
        {
            "code": code,
            "test_cases": test_cases,
            "entry_point": entry_point,
            "constraints_to_check": constraints_to_check,
            "applicable": True,
        }
        for code in code_list
    ]

    results = evaluate_functional_correctness_batch(
        problems, n_workers=n_workers, timeout=timeout, maximum_memory_bytes=maximum_memory_bytes
    )

    if len(results) == 1:
        return {"passed": results[0]["passed"], "result": results[0]["result"]}

    passed = [r["passed"] for r in results]
    total = len(passed)
    correct = sum(passed)
    reasons = [r["result"] for r in results]

    pass_at_k = {
        f"pass@{kk}": _pass_at_k_unbiased(total, correct, kk)
        for kk in k
        if total >= kk
    }
    pass_at_k["reasons"] = reasons

    return pass_at_k


# ---------------------------------------------------------------------------
# many INDEPENDENT problems, one candidate each
# ---------------------------------------------------------------------------


def evaluate_functional_correctness_batch(
    problems: List[Dict[str, Any]],
    n_workers: int = 8,
    timeout: float = 3.0,
    maximum_memory_bytes: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Evaluates many independent (code, test_cases, entry_point) problems
    concurrently, sharing one Manager and one thread pool across the whole
    batch instead of spinning both up per-entry.

    Each item in `problems` is a dict with keys:
        "code"                 : str or None  — candidate solution
        "test_cases"           : str or None  — the check() body/program, or
                                  a pytest-style test module
        "entry_point"          : str          — function to call, e.g.
                                  "check" (ignored for pytest-style
                                  test_cases, which pytest collects itself)
        "constraints_to_check" : list[str], optional — expected name(s) of
                                  the function under test inside `code`. The
                                  first element is used to align `code`'s
                                  function name with what `test_cases`
                                  expects to call. Omit/None to skip this
                                  step entirely (previous behavior).
        "applicable"            : bool, optional (default True) — set False
                                  to skip entries that aren't executable-code
                                  tasks (e.g. code-review tasks with no test
                                  suite) without crashing the batch.

    Returns a list of result dicts, one per input problem, in the same
    order as `problems`. Skipped/invalid entries get
    passed=False, result="skipped: <reason>" instead of raising.
    """
    manager = multiprocessing.Manager()
    results: List[Optional[Dict[str, Any]]] = [None] * len(problems)

    try:
        with ThreadPoolExecutor(max_workers=n_workers) as executor:
            futures = {}

            for idx, problem in enumerate(problems):
                code = problem.get("code")
                test_cases = problem.get("test_cases")
                entry_point = problem.get("entry_point", "check")
                applicable = problem.get("applicable", True)
                constraints = problem.get("constraints_to_check") or []
                expected_name = constraints[0] if constraints else None

                if not applicable:
                    results[idx] = dict(
                        code=code, passed=False, result="skipped: not an executable-code task",
                        completion_id=idx, exe_time=-1,
                    )
                    continue
                if code is None:
                    results[idx] = dict(
                        code=code, passed=False, result="skipped: no code_snippet found",
                        completion_id=idx, exe_time=-1,
                    )
                    continue
                if not isinstance(code, str):
                    results[idx] = dict(
                        code=code, passed=False, result=f"skipped: code_snippet is {type(code)}, not str.",
                        completion_id=idx, exe_time=-1,
                    )
                    continue
                if test_cases is None:
                    results[idx] = dict(
                        code=code, passed=False, result="skipped: no test cases provided",
                        completion_id=idx, exe_time=-1,
                    )
                    continue

                # Align code's function name with what test_cases expects to
                # call, when the dataset tells us what name to expect.
                alias_line = None
                if expected_name:
                    resolution = _resolve_entry_point(code, expected_name)
                    if not resolution["ok"]:
                        results[idx] = dict(
                            code=code, passed=False,
                            result=f"skipped: {resolution['reason']}",
                            completion_id=idx, exe_time=-1,
                        )
                        continue
                    alias_line = resolution["alias_line"]

                pytest_style = _is_pytest_style(test_cases)

                script_parts = [code]
                if alias_line:
                    print(alias_line)
                    script_parts.append(alias_line)
                script_parts.append(test_cases)
                if not pytest_style:
                    script_parts.append(f"{entry_point}()")
                alg = "\n\n".join(script_parts)

                if pytest_style:
                    print("Used pytest style")
                    future = executor.submit(_run_pytest_case, alg, timeout)
                else:
                    future = executor.submit(
                        check_correctness, alg, timeout, idx, manager, maximum_memory_bytes
                    )
                futures[future] = (idx, code, pytest_style)

            if futures:
                print(f"Running {len(futures)} test suite(s)...")
                for future in tqdm.tqdm(as_completed(futures), total=len(futures)):
                    idx, code, pytest_style = futures[future]
                    outcome = future.result()
                    if pytest_style:
                        # _run_pytest_case returns {"passed","result","exe_time"};
                        # normalize to the same shape check_correctness produces.
                        results[idx] = dict(
                            code=code,
                            passed=outcome["passed"],
                            result=outcome["result"],
                            completion_id=idx,
                            exe_time=outcome["exe_time"],
                        )
                    else:
                        results[idx] = outcome
    finally:
        manager.shutdown()

    return results  # type: ignore[return-value]


def _last_assistant_message(turn: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Last message in a turn that was actually sent by the assistant,
    rather than assuming messages[-1] is always the assistant's."""
    for message in reversed(turn.get("messages", [])):
        if message.get("role") == "assistant":
            return message
    return None


def evaluate_code_running(
    *inputs: Dict[str, Any],
    n_workers: int = 8,
    timeout: float = 3.0,
    maximum_memory_bytes: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Takes dataset entries and functionally tests each one's final assistant
    code_snippet against its ground-truth test cases, concurrently across
    the whole batch.

    Entries without an executable test suite (test_cases_to_pass is None —
    e.g. code-review/CCA tasks) or without a code_snippet on the final
    assistant message are marked "skipped" rather than crashing the run.

    If test_cases_to_pass is itself pytest-style (imports pytest, uses
    @pytest.mark.*, defines a Test class, or has several standalone test_*
    functions), it is passed through to pytest as-is instead of being
    wrapped in a "def check(): <indented body>" -- wrapping would nest the
    test_* functions inside check(), where pytest can never discover or
    call them. final_ground_truth's "constraints_to_check", when present,
    is used to align the candidate code's function name with the name the
    test suite expects to call.
    """
    problems = []
    for entry in inputs:
        last_turn = entry.get("turns", [{}])[-1]
        assistant_msg = _last_assistant_message(last_turn)
        code = assistant_msg.get("code_snippet") if assistant_msg else None

        ground_truth = entry.get("final_ground_truth", {})
        raw_test_cases = ground_truth.get("test_cases_to_pass")
        constraints_to_check = ground_truth.get("constraints_to_check")

        if raw_test_cases is not None and _is_pytest_style(raw_test_cases):
            test_cases = raw_test_cases
        elif raw_test_cases is not None:
            test_cases = "def check():\n    " + "\n    ".join(raw_test_cases.split("\n"))
        else:
            test_cases = None

        problems.append({
            "code": code,
            "test_cases": test_cases,
            "entry_point": "check",
            "constraints_to_check": constraints_to_check,
            "applicable": raw_test_cases is not None,
        })

    return evaluate_functional_correctness_batch(
        problems, n_workers=n_workers, timeout=timeout, maximum_memory_bytes=maximum_memory_bytes
    )


if __name__ == "__main__":
    # Example usage
    code_list = [
        "def add(a, b):\n    return a + b",
        "def add(a, b):\n    return a - b",
        "def add(num1, num2):\n    summation = sum([num1, num2])\n    return summation",
    ]
    test_cases = """
def check():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
"""
    entry_point = "check"
    results = evaluate_functional_correctness(code_list, test_cases, entry_point, timeout=5.0)
    print(results)