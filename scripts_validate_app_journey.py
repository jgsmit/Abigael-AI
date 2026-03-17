from __future__ import annotations

import ast
import hashlib
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def compile_python() -> list[str]:
    failures: list[str] = []
    for py in ROOT.rglob('*.py'):
        if '__pycache__' in py.parts:
            continue
        try:
            py_compile.compile(str(py), doraise=True)
        except Exception as exc:  # pragma: no cover
            failures.append(f"{py.relative_to(ROOT)}: {exc}")
    return failures


def missing_render_templates() -> list[str]:
    missing: list[str] = []
    for py in ROOT.rglob('*.py'):
        if '__pycache__' in py.parts:
            continue
        try:
            tree = ast.parse(py.read_text())
        except Exception:
            continue

        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'render'):
                continue
            if len(node.args) < 2 or not isinstance(node.args[1], ast.Constant) or not isinstance(node.args[1].value, str):
                continue
            tpl = node.args[1].value
            candidates = [
                ROOT / 'templates' / tpl,
                ROOT / 'tasks' / 'templates' / tpl,
                ROOT / 'emotion_detection' / 'templates' / tpl,
            ]
            if not any(c.exists() for c in candidates):
                missing.append(f"{py.relative_to(ROOT)}:{node.lineno} -> {tpl}")
    return missing


def duplicate_templates() -> list[list[str]]:
    templates = [p for p in ROOT.rglob('*.html') if '/templates/' in str(p)]
    by_hash: dict[str, list[Path]] = {}
    for p in templates:
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        by_hash.setdefault(digest, []).append(p)

    groups: list[list[str]] = []
    for grp in by_hash.values():
        if len(grp) > 1:
            groups.append([str(p.relative_to(ROOT)) for p in grp])
    return groups


def verify_unified_dashboard_endpoints() -> list[str]:
    issues: list[str] = []
    dashboard = ROOT / 'tasks' / 'templates' / 'dashboard' / 'unified_dashboard.html'
    content = dashboard.read_text()

    required_strings = [
        "fetch('/companion/api/user/complete/')",
        "fetch('/api/tasks/analytics/')",
        "fetch('/api/tasks/recommendations/')",
        'href="/hud/"',
        'href="/analytics/"',
        'href="/chat/"',
        'href="/biofeedback/"',
        'href="/companion/"',
    ]
    for item in required_strings:
        if item not in content:
            issues.append(f"Missing expected route in unified dashboard: {item}")
    return issues


def main() -> int:
    failures = compile_python()
    missing_templates = missing_render_templates()
    duplicate_tpls = duplicate_templates()
    dashboard_issues = verify_unified_dashboard_endpoints()

    if failures:
        print('PYTHON_COMPILE_FAILURES:')
        for item in failures:
            print('-', item)
    if missing_templates:
        print('MISSING_RENDER_TEMPLATES:')
        for item in missing_templates:
            print('-', item)
    if duplicate_tpls:
        print('DUPLICATE_TEMPLATES:')
        for grp in duplicate_tpls:
            print('-', ', '.join(grp))
    if dashboard_issues:
        print('DASHBOARD_ROUTE_ISSUES:')
        for item in dashboard_issues:
            print('-', item)

    ok = not (failures or missing_templates or duplicate_tpls or dashboard_issues)
    print('VALIDATION_STATUS:', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
