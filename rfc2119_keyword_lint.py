# -*- coding: utf-8 -*-
"""rfc2119-keyword-lint: RFC 2119 normative-keyword consistency checks for
specification documents (boilerplate presence, case discipline, embedding,
fragments, justification hints).

Pure standard library. CLI via argparse.
Exit codes: 0 clean (per --fail-on), 1 findings at or above threshold,
2 usage error (argparse).
"""
import argparse
import json
import re
import sys
import time

KEYWORD_RE = re.compile(
    r"MUST NOT|SHALL NOT|SHOULD NOT|MUST|SHALL|SHOULD|RECOMMENDED|REQUIRED|"
    r"OPTIONAL|MAY")
LOWER_KEYWORDS = {"must", "shall", "should", "may", "required", "recommended",
                  "optional"}
WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)  # unicode word tokens
JUSTIFY_HINTS = ("unless", "because", "reason", "when", "if ")


def check(text):
    """Lint a spec document. Returns findings [{rule, severity, line, excerpt}]."""
    findings = []
    lines = text.splitlines()

    def add(rule, sev, line_no, excerpt):
        findings.append({"rule": rule, "severity": sev, "line": line_no,
                         "excerpt": excerpt[:80]})

    # K1: RFC 2119 boilerplate within the first quarter of the document
    quarter = max(1, len(lines) // 4)
    head = "\n".join(lines[:quarter]).lower()
    if "key words" not in head or not re.search(r"rfc\s?2119", head):
        add("K1", "error", None, "RFC 2119 boilerplate ('key words ... RFC 2119') "
                                 "not found in first quarter of document")

    # K2: lowercase / mixed-case keyword tokens are ambiguous
    n_lower = 0
    for i, line in enumerate(lines):
        for tok in WORD_RE.findall(line):
            tl = tok.lower()
            if tl in LOWER_KEYWORDS and tok != tok.upper():
                if n_lower < 20:
                    add("K2", "warn", i + 1,
                        "lower/mixed-case keyword %r (verify intent)" % tok)
                n_lower += 1
    if n_lower > 20:
        add("K2", "warn", None, "%d more lower/mixed-case keyword tokens" % (n_lower - 20))

    # K3: uppercase keyword embedded in a longer token (MUSTARD, OPTIONALLY)
    seen_embed = set()
    for kw in ("MUST", "SHALL", "SHOULD", "RECOMMENDED", "REQUIRED", "OPTIONAL", "MAY"):
        pat = re.compile(r"[^\W\d_]*" + kw + r"[^\W\d_]+", re.UNICODE)
        for i, line in enumerate(lines):
            for m in pat.finditer(line):
                tok = m.group(0)
                if (tok, i) in seen_embed:
                    continue
                seen_embed.add((tok, i))
                add("K3", "error", i + 1,
                    "keyword %s embedded in token %r" % (kw, tok))

    # K4: fragment lines — keyword used with too few words around it
    for i, line in enumerate(lines):
        if KEYWORD_RE.search(line) and len(line.split()) < 4:
            add("K4", "warn", i + 1, "possible fragment (<4 tokens around keyword)")

    # K5: SHOULD statements should carry a justification hint
    for i, line in enumerate(lines):
        if re.search(r"\bSHOULD\b", line) and not re.search(r"\bSHOULD NOT\b", line):
            sentence = line.split(".")[0].lower()
            if not any(h in sentence for h in JUSTIFY_HINTS):
                add("K5", "info", i + 1, "SHOULD without justification hint")

    # K6: MAY-heavy documents (ratio over all normative statements)
    statements = KEYWORD_RE.findall(text)
    may = sum(1 for s in statements if s == "MAY")
    if len(statements) >= 10 and may / len(statements) > 0.4:
        add("K6", "info", None, "%.0f%% of normative statements are MAY "
                                "(weak guidance density)" % (100.0 * may / len(statements)))
    return findings


def exit_code(findings, fail_on="error"):
    order = {"error": 0, "warn": 1, "info": 2}
    threshold = order.get(fail_on, 0)
    return 1 if any(order[f["severity"]] <= threshold for f in findings) else 0


def cmd_lint(args):
    try:
        with open(args.file, "r", encoding="utf-8", newline="") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError) as e:
        print("cannot read %s: %s" % (args.file, e), file=sys.stderr)
        return 1
    findings = check(text)
    if args.json:
        print(json.dumps({"findings": findings, "fail_on": args.fail_on},
                         ensure_ascii=False, indent=2))
    else:
        for f in findings:
            print("%s %s line=%s: %s" % (f["severity"], f["rule"], f["line"],
                                         f["excerpt"]))
        by = {}
        for f in findings:
            by[f["severity"]] = by.get(f["severity"], 0) + 1
        print("%d error(s), %d warn(s), %d info" %
              (by.get("error", 0), by.get("warn", 0), by.get("info", 0)))
    return exit_code(findings, fail_on=args.fail_on)


def cmd_bench(args):
    body = ["The gateway MUST reject requests older than %d seconds, because replay "
            "protection is REQUIRED for integrity." % i for i in range(args.lines)]
    text = "The key words MUST, MUST NOT are interpreted per RFC 2119.\n" + "\n".join(body)
    t0 = time.perf_counter()
    n = len(check(text))
    dt = time.perf_counter() - t0
    print("bench: %d lines (%d chars) linted in %.3fs (%.0f lines/s, %d findings)"
          % (args.lines, len(text), dt, args.lines / dt if dt > 0 else 0, n))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="rfc2119-keyword-lint",
        description="RFC 2119 keyword consistency linter: boilerplate presence, "
                    "case discipline, token embedding, fragments, MAY density.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    l = sub.add_parser("lint", help="lint a specification document")
    l.add_argument("file")
    l.add_argument("--fail-on", choices=("error", "warn", "info"), default="error")
    l.add_argument("--json", action="store_true")
    l.set_defaults(fn=cmd_lint)
    b = sub.add_parser("bench", help="synthetic benchmark")
    b.add_argument("--lines", type=int, default=10000)
    b.set_defaults(fn=cmd_bench)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
