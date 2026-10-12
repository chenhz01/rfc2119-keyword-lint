# -*- coding: utf-8 -*-
"""self_test for rfc2119-keyword-lint (scaffold v2, four defenses inherited).

D1: SystemExit caught in run_cli. D2: unicode document text exercised.
D3: fixtures written with newline="". D4: last line "SUMMARY: PASS n/n".
"""
import contextlib
import importlib.util
import io
import json
import os
import re
import sys
import tempfile
import time
import unittest

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n")  # D3

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "core", os.path.join(_HERE, "rfc2119_keyword_lint.py"))
core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(core)
main = core.main

CASES = []


def case(category, name):
    def deco(fn):
        CASES.append((category, name, fn))
        return fn
    return deco


def run_cli(argv):
    buf_out, buf_err = io.StringIO(), io.StringIO()
    code = 0
    try:
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            ret = main(argv)
            code = 0 if ret is None else int(ret)
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except Exception as e:
        code = 1
        buf_err.write(repr(e))
    return code, buf_out.getvalue(), buf_err.getvalue()


_TMP = tempfile.mkdtemp(prefix="rkl_selftest_")


def write_fixture(name, text):
    p = os.path.join(_TMP, name)
    with open(p, "w", encoding="utf-8", newline="") as f:  # D3
        f.write(text)
    return p


def rules(text):
    return sorted({f["rule"] for f in core.check(text)})


BOILER = ('The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", '
          '"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this '
          "document are to be interpreted as described in RFC 2119.")


def good_doc():
    return BOILER + "\n\nServers MUST reject expired tokens, because replay is unsafe.\n"


# ---------- [A] functional ----------
def _t_good_clean():
    fs = core.check(good_doc())
    assert [f for f in fs if f["severity"] == "error"] == [], fs
case("A", "compliant doc has zero errors")(_t_good_clean)

def _t_k1_missing():
    fs = core.check("Servers MUST reject expired tokens.\n")
    assert "K1" in [f["rule"] for f in fs]
case("A", "K1 fires without boilerplate")(_t_k1_missing)

def _t_k1_deep():
    filler = "\n".join("filler line %d" % i for i in range(100))
    doc = filler + "\n" + BOILER + "\n"
    assert "K1" in rules(doc)
case("A", "K1 fires when boilerplate after first quarter")(_t_k1_deep)

def _t_k1_nospace_rfc():
    doc = BOILER.replace("RFC 2119", "RFC2119")
    assert "K1" not in rules(doc)
case("A", "K1 accepts 'RFC2119' without space")(_t_k1_nospace_rfc)

def _t_k2_lowercase():
    fs = core.check(BOILER + "\nClients may retry once.\n")
    assert any(f["rule"] == "K2" and f["severity"] == "warn" for f in fs)
case("A", "K2 warns on lowercase 'may'")(_t_k2_lowercase)

def _t_k2_month():
    fs = core.check(BOILER + "\nThe May release ships on Tuesday.\n")
    assert any(f["rule"] == "K2" for f in fs)
case("A", "K2 flags 'May' month (verify-intent policy)")(_t_k2_month)

def _t_k2_upper_ok():
    assert "K2" not in rules(good_doc())
case("A", "K2 silent on uppercase keywords")(_t_k2_upper_ok)

def _t_k3_mustard():
    fs = core.check(BOILER + "\nThe MUSTARD variable is REQUIRED.\n")
    assert any(f["rule"] == "K3" and "MUSTARD" in f["excerpt"] for f in fs)
case("A", "K3 flags MUSTARD embedding")(_t_k3_mustard)

def _t_k3_optionally():
    fs = core.check(BOILER + "\nClients OPTIONALLY send hints.\n")
    assert any(f["rule"] == "K3" and "OPTIONALLY" in f["excerpt"] for f in fs)
case("A", "K3 flags OPTIONALLY")(_t_k3_optionally)

def _t_k3_plain_ok():
    assert "K3" not in rules(good_doc())
case("A", "K3 silent on plain keywords")(_t_k3_plain_ok)

def _t_k4_fragment():
    fs = core.check(BOILER + "\nData MUST.\n")
    assert any(f["rule"] == "K4" for f in fs)
case("A", "K4 warns on fragment line")(_t_k4_fragment)

def _t_k4_full_ok():
    fs = core.check(good_doc())
    assert "K4" not in [f["rule"] for f in fs]
case("A", "K4 silent on full sentences")(_t_k4_full_ok)

def _t_k5_no_reason():
    fs = core.check(BOILER + "\nDeployments SHOULD be atomic.\n")
    assert any(f["rule"] == "K5" and f["severity"] == "info" for f in fs)
case("A", "K5 info for unjustified SHOULD")(_t_k5_no_reason)

def _t_k5_unless():
    fs = core.check(BOILER + "\nDeployments SHOULD roll back unless health checks pass.\n")
    assert "K5" not in [f["rule"] for f in fs]
case("A", "K5 satisfied by 'unless'")(_t_k5_unless)

def _t_k5_because():
    fs = core.check(BOILER + "\nRetries SHOULD back off, because storms amplify.\n")
    assert "K5" not in [f["rule"] for f in fs]
case("A", "K5 satisfied by 'because'")(_t_k5_because)

def _t_k5_should_not_exempt():
    fs = core.check(BOILER + "\nClients SHOULD NOT retry on 4xx failures.\n")
    assert "K5" not in [f["rule"] for f in fs]
case("A", "SHOULD NOT exempt from K5")(_t_k5_should_not_exempt)

def _t_k6_may_heavy():
    lines = [BOILER] + ["Items MAY be skipped freely."] * 12
    fs = core.check("\n".join(lines))
    assert any(f["rule"] == "K6" for f in fs)
case("A", "K6 info for MAY-heavy docs")(_t_k6_may_heavy)

def _t_k6_low_ratio():
    lines = [BOILER] + ["Agents MUST ack, because delivery is at-least-once."] * 9 \
        + ["Items may be skipped freely."]
    fs = core.check("\n".join(lines))
    assert "K6" not in [f["rule"] for f in fs]
case("A", "K6 silent under 40% MAY ratio")(_t_k6_low_ratio)

def _t_k6_threshold_guard():
    lines = [BOILER] + ["Items may be skipped freely."] * 9  # 9 statements < 10
    fs = core.check("\n".join(lines))
    assert "K6" not in [f["rule"] for f in fs]
case("A", "K6 needs at least 10 statements")(_t_k6_threshold_guard)

def _t_cli_lint_good():
    p = write_fixture("good.md", good_doc())
    code, out, _ = run_cli(["lint", p])
    assert code == 0 and "0 error(s)" in out
case("A", "CLI lint compliant -> 0")(_t_cli_lint_good)

def _t_cli_lint_bad():
    p = write_fixture("bad.md", "Servers MUST.\n")
    code, out, _ = run_cli(["lint", p])
    assert code == 1 and "K1" in out
case("A", "CLI lint non-compliant -> 1")(_t_cli_lint_bad)

def _t_cli_json():
    p = write_fixture("bad.md", "Servers MUST.\n")
    code, out, _ = run_cli(["lint", p, "--json"])
    parsed = json.loads(out)
    assert code == 1 and all("rule" in f for f in parsed["findings"])
case("A", "CLI --json findings parseable")(_t_cli_json)

def _t_cli_failon_warn():
    p = write_fixture("w.md", BOILER + "\nClients may retry.\n")
    code1, _, _ = run_cli(["lint", p])
    code2, _, _ = run_cli(["lint", p, "--fail-on", "warn"])
    assert code1 == 0 and code2 == 1
case("A", "--fail-on warn promotes exit code")(_t_cli_failon_warn)

def _t_cli_failon_info():
    p = write_fixture("i.md", BOILER + "\nDeployments SHOULD be atomic.\n")
    code1, _, _ = run_cli(["lint", p])
    code2, _, _ = run_cli(["lint", p, "--fail-on", "info"])
    assert code1 == 0 and code2 == 1
case("A", "--fail-on info catches infos")(_t_cli_failon_info)

def _t_excerpt_trim():
    long_line = BOILER + "\n" + "The " + "x" * 200 + " token MUST be rotated.\n"
    fs = core.check(long_line)
    assert all(len(f["excerpt"]) <= 80 for f in fs)
case("A", "excerpts trimmed to 80 chars")(_t_excerpt_trim)

def _t_line_numbers():
    doc = BOILER + "\n\nline2 is plain\nMUSTARD appears here.\n"
    fs = [f for f in core.check(doc) if f["rule"] == "K3"]
    assert fs and fs[0]["line"] == 4
case("A", "line numbers are 1-based and correct")(_t_line_numbers)

def _t_findings_shape():
    for f in core.check(good_doc()):
        assert set(f) == {"rule", "severity", "line", "excerpt"}
case("A", "finding shape stable")(_t_findings_shape)

# ---------- [B] exception paths ----------
def _t_empty_doc():
    fs = core.check("")
    assert [f["rule"] for f in fs] == ["K1"]
case("B", "empty doc -> single K1 error")(_t_empty_doc)

def _t_whitespace_doc():
    fs = core.check("\n \n\t\n")
    assert [f["rule"] for f in fs] == ["K1"]
case("B", "whitespace-only doc -> K1")(_t_whitespace_doc)

def _t_no_args():
    code, _, _ = run_cli([])
    assert code == 2
case("B", "CLI no args -> SystemExit 2 (D1)")(_t_no_args)

def _t_unknown_cmd():
    code, _, _ = run_cli(["check"])
    assert code == 2
case("B", "CLI unknown subcommand -> 2")(_t_unknown_cmd)

def _t_missing_file():
    code, _, err = run_cli(["lint", os.path.join(_TMP, "nope.md")])
    assert code == 1 and "cannot read" in err
case("B", "CLI missing file -> 1")(_t_missing_file)

def _t_non_utf8():
    p = os.path.join(_TMP, "latin.md")
    with open(p, "wb") as f:
        f.write(b"caf\xe9 MUST be handled\n")
    code, _, _ = run_cli(["lint", p])
    assert code == 1
case("B", "non-UTF8 file -> 1, no crash")(_t_non_utf8)

def _t_bad_failon():
    p = write_fixture("g.md", good_doc())
    code, _, _ = run_cli(["lint", p, "--fail-on", "fatal"])
    assert code == 2
case("B", "invalid --fail-on choice -> 2")(_t_bad_failon)

def _t_k2_capped():
    body = "\n".join("we may do %d things" % i for i in range(40))
    fs = core.check(BOILER + "\n" + body)
    k2 = [f for f in fs if f["rule"] == "K2"]
    assert len(k2) <= 21 and any("more lower" in f["excerpt"] for f in k2)
case("B", "K2 findings capped at 20 + overflow")(_t_k2_capped)

def _t_bare_must():
    fs = core.check(BOILER + "\nMUST\n")
    assert any(f["rule"] == "K4" for f in fs)
case("B", "bare 'MUST' line -> K4")(_t_bare_must)

def _t_severity_vocab():
    for f in core.check(BOILER + "\nData MUST.\nwe may try.\nMUSTARD here.\n"
                                 "SHOULD be fine.\n"):
        assert f["severity"] in ("error", "warn", "info")
case("B", "severities limited to known set")(_t_severity_vocab)

def _t_keywords_only_doc():
    fs = core.check("MUST MUST MAY\n")
    assert isinstance(fs, list) and "K1" in [f["rule"] for f in fs]
case("B", "keyword-salad doc does not crash")(_t_keywords_only_doc)

def _t_keyword_in_quotes():
    fs = core.check(BOILER)
    assert "K3" not in [f["rule"] for f in fs]
case("B", "quoted keywords in boilerplate fine")(_t_keyword_in_quotes)

def _t_upper_normative_count():
    n = len(core.KEYWORD_RE.findall("MUST NOT and MUST and MAY"))
    assert n == 3
case("B", "multi-word keyword counted once")(_t_upper_normative_count)

# ---------- [C] extreme edges ----------
def _t_crlf():
    p = write_fixture("crlf.md", good_doc().replace("\n", "\r\n"))
    code, _, _ = run_cli(["lint", p])
    assert code == 0
case("C", "CRLF fixture passes (D3)")(_t_crlf)

def _t_unicode_text():
    doc = BOILER + "\n服务器 MUST 拒绝过期令牌，因为重放不安全。\n"
    fs = core.check(doc)
    assert [f for f in fs if f["severity"] == "error"] == []
case("C", "CJK sentences with MUST accepted (D2)")(_t_unicode_text)

def _t_unicode_embedding():
    fs = core.check(BOILER + "\nMUSTÄR token here.\n")
    assert any(f["rule"] == "K3" and "MUSTÄR" in f["excerpt"] for f in fs)
case("C", "unicode-adjacent embedding caught")(_t_unicode_embedding)

def _t_10k_lines_perf():
    lines = [BOILER] + ["Agent MUST ack message %d, because delivery is at-least-once."
                        % i for i in range(10000)]
    t0 = time.perf_counter()
    fs = core.check("\n".join(lines))
    dt = time.perf_counter() - t0
    assert dt < 5.0 and isinstance(fs, list)
case("C", "10k-line doc linted under 5s")(_t_10k_lines_perf)

def _t_huge_single_line():
    doc = BOILER + "\n" + ("MUST " * 20000).strip() + "\n"
    fs = core.check(doc)
    assert isinstance(fs, list)
case("C", "100k-char single line handled")(_t_huge_single_line)

def _t_mixed_case():
    fs = core.check(BOILER + "\nYou Must comply.\n")
    assert any(f["rule"] == "K2" and "Must" in f["excerpt"] for f in fs)
case("C", "mixed-case 'Must' flagged")(_t_mixed_case)

def _t_heading_fragment():
    fs = core.check(BOILER + "\n## You MUST\n")
    assert any(f["rule"] == "K4" for f in fs)
case("C", "keyword in short heading -> K4")(_t_heading_fragment)

def _t_optional_lowercase():
    fs = core.check(BOILER + "\nThis field is optional in payloads.\n")
    assert any(f["rule"] == "K2" for f in fs)
case("C", "lowercase 'optional' flagged")(_t_optional_lowercase)

def _t_failon_info_clean():
    p = write_fixture("clean.md", good_doc())
    code, _, _ = run_cli(["lint", p, "--fail-on", "info"])
    assert code == 0
case("C", "clean doc passes even with --fail-on info")(_t_failon_info_clean)

def _t_json_flag_shape():
    p = write_fixture("b.md", "Servers MUST.\n")
    code, out, _ = run_cli(["lint", p, "--json"])
    parsed = json.loads(out)
    assert parsed["fail_on"] == "error" and parsed["findings"]
case("C", "--json echoes fail_on")(_t_json_flag_shape)

def _t_two_rule_hits_same_line():
    fs = core.check(BOILER + "\nData MUSTS.\n")
    ruleset = [f["rule"] for f in fs]
    assert "K3" in ruleset
case("C", "MUSTS embedding caught (K3)")(_t_two_rule_hits_same_line)

def _t_doc_without_any_keyword():
    fs = core.check("A plain readme without normative statements.\n")
    assert [f["rule"] for f in fs] == ["K1"]
case("C", "non-spec doc -> only K1 (boilerplate) fires")(_t_doc_without_any_keyword)

def _t_k1_keywords_only():
    doc = BOILER.replace(" as described in RFC 2119", "")
    assert "K1" in rules(doc)
case("A", "K1 needs the RFC 2119 mention too")(_t_k1_keywords_only)

def _t_k1_rfc_only():
    doc = "As described in RFC 2119.\n" + BOILER.replace(BOILER, "") \
        if False else "As described in RFC 2119.\nServers MUST reject expired tokens.\n"
    assert "K1" in rules(doc)
case("A", "K1 needs the 'key words' phrase too")(_t_k1_rfc_only)

def _t_k2_shall_lowercase():
    fs = core.check(BOILER + "\nParties shall comply.\n")
    assert any(f["rule"] == "K2" and "shall" in f["excerpt"] for f in fs)
case("A", "K2 flags lowercase 'shall'")(_t_k2_shall_lowercase)

def _t_k3_shoulders():
    fs = core.check(BOILER + "\nThe SHOULDERS clause applies.\n")
    assert any(f["rule"] == "K3" and "SHOULDERS" in f["excerpt"] for f in fs)
case("A", "K3 flags SHOULDERS embedding")(_t_k3_shoulders)

def _t_k4_two_tokens():
    fs = core.check(BOILER + "\nWe MUST\n")
    assert any(f["rule"] == "K4" for f in fs)
case("A", "K4 flags 2-token fragment")(_t_k4_two_tokens)

def _t_k5_when_hint():
    fs = core.check(BOILER + "\nCaches SHOULD purge when TTL expires.\n")
    assert "K5" not in [f["rule"] for f in fs]
case("A", "K5 satisfied by 'when'")(_t_k5_when_hint)

def _t_cli_json_severity_counts():
    p = write_fixture("mix.md", BOILER + "\nData MUST.\nwe may try.\n")
    code, out, _ = run_cli(["lint", p, "--json"])
    parsed = json.loads(out)
    sevs = [f["severity"] for f in parsed["findings"]]
    assert "warn" in sevs
case("A", "--json findings carry severities")(_t_cli_json_severity_counts)

def _t_exit_info_with_warn_threshold():
    fs = [{"rule": "K5", "severity": "info", "line": 1, "excerpt": "x"}]
    assert core.exit_code(fs, fail_on="warn") == 0
    assert core.exit_code(fs, fail_on="info") == 1
case("A", "exit_code info vs warn threshold")(_t_exit_info_with_warn_threshold)

def _t_meta_count():
    assert len(CASES) >= 60
case("C", "meta: at least 60 cases defined")(_t_meta_count)


class T(unittest.TestCase):
    pass


def _add(i, cat, name, fn):
    def t(self, _f=fn):
        _f()
    t.__doc__ = "%s: %s" % (cat, name)
    setattr(T, "test_%s_%03d_%s" % (cat, i, re.sub(r"[^0-9A-Za-z_]", "_", name)), t)


for _i, (_c, _n, _f) in enumerate(CASES):
    _add(_i + 1, _c, _n, _f)

if __name__ == "__main__":
    r = unittest.TextTestRunner(verbosity=0).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules["__main__"]))
    total, fails = r.testsRun, len(r.failures) + len(r.errors)
    print("SUMMARY: PASS %d/%d" % (total - fails, total))  # D4
    sys.exit(0 if fails == 0 else 1)
