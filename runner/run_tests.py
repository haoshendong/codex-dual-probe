#!/usr/bin/env python3
"""每 30 分钟调用一次 Codex 跑两个测试，判定结果并更新网站数据。

测试一：逻辑答题 · 糖果题（预期答案 21，取末行「答案：<数字>」比对）
测试二：HTML 生成 · 鹈鹕骑行（返回可渲染 HTML 即记为已生成）
"""
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_JSON = ROOT / "data" / "results.json"
DATA_JS = ROOT / "data" / "data.js"
PREVIEWS = ROOT / "previews"
LOGS = ROOT / "logs"

MODEL = "gpt-6-astra"
REASONING_EFFORT = "medium"
EXPECTED_ANSWER = 21
PER_TEST_TIMEOUT_S = 900
MAX_RUNS_KEPT = 500

CST = timezone(timedelta(hours=8))


def run_codex(prompt: str, out_file: Path):
    """调用 codex exec，返回 (ok, error)。模型最终回复写入 out_file。"""
    cmd = [
        "codex", "exec",
        "-m", MODEL,
        "-c", f'model_reasoning_effort="{REASONING_EFFORT}"',
        "-s", "read-only",
        "--skip-git-repo-check",
        "--ephemeral",
        "--color", "never",
        "-o", str(out_file),
        "-C", str(ROOT),
        prompt,
    ]
    try:
        proc = subprocess.run(
            cmd, cwd=ROOT, capture_output=True, text=True,
            timeout=PER_TEST_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return False, f"timeout after {PER_TEST_TIMEOUT_S}s"
    except FileNotFoundError:
        return False, "codex CLI not found"
    if not out_file.exists() or not out_file.read_text(encoding="utf-8", errors="replace").strip():
        tail = (proc.stderr or proc.stdout or "")[-500:]
        return False, f"empty output (exit {proc.returncode}): {tail}"
    return True, None


def judge_candy(text: str):
    """取末行「答案：<数字>」比对，不在全文里搜数字。"""
    answer = None
    for line in reversed(text.strip().splitlines()):
        m = re.match(r"^\s*答案：\s*(\d+)\s*$", line)
        if m:
            answer = int(m.group(1))
            break
    if answer is None:
        return False, None, "未找到末行「答案：<数字>」"
    return answer == EXPECTED_ANSWER, answer, None


def extract_html(text: str):
    """从模型回复中提取可渲染 HTML：去掉 markdown 围栏，截取 doctype/<html 到 </html>。"""
    s = text.strip()
    fence = re.search(r"```(?:html)?\s*\n(.*?)```", s, re.S)
    if fence:
        s = fence.group(1).strip()
    low = s.lower()
    start = low.find("<!doctype")
    if start == -1:
        start = low.find("<html")
    if start == -1:
        start = low.find("<svg")
    if start == -1:
        return None
    end = low.rfind("</html>")
    if end != -1:
        return s[start:end + len("</html>")]
    return s[start:]


def main():
    now = datetime.now(CST)
    run_id = now.strftime("%Y%m%d-%H%M%S")
    ts = now.isoformat()
    run = {"id": run_id, "ts": ts, "model": MODEL,
           "reasoning_effort": REASONING_EFFORT, "test1": {}, "test2": {}}

    prompt1 = (ROOT / "prompts" / "test1_candy.txt").read_text(encoding="utf-8")
    prompt2 = (ROOT / "prompts" / "test2_pikachu.txt").read_text(encoding="utf-8")
    # 运行环境是只读沙箱，模型写文件会被拒绝；要求把 HTML 直接输出在回复里。
    prompt2 += (
        "\n\n注意：运行环境为只读沙箱，无法创建或修改任何文件。"
        "请不要尝试写文件，直接把完整的 HTML 代码输出在最终回复的正文里。"
    )

    # 测试一
    out1 = LOGS / f"{run_id}-test1.md"
    t0 = time.monotonic()
    ok, err = run_codex(prompt1, out1)
    dur1 = round(time.monotonic() - t0, 1)
    if ok:
        text = out1.read_text(encoding="utf-8", errors="replace")
        passed, answer, jerr = judge_candy(text)
        run["test1"] = {"passed": passed, "answer": answer,
                        "expected": EXPECTED_ANSWER, "duration_s": dur1,
                        "error": jerr}
    else:
        run["test1"] = {"passed": False, "answer": None,
                        "expected": EXPECTED_ANSWER, "duration_s": dur1,
                        "error": err}

    # 测试二
    out2 = LOGS / f"{run_id}-test2.md"
    t0 = time.monotonic()
    ok, err = run_codex(prompt2, out2)
    dur2 = round(time.monotonic() - t0, 1)
    if ok:
        text = out2.read_text(encoding="utf-8", errors="replace")
        html = extract_html(text)
        if html:
            preview_rel = f"previews/{run_id}.html"
            (PREVIEWS / f"{run_id}.html").write_text(html, encoding="utf-8")
            run["test2"] = {"passed": True, "preview": preview_rel,
                            "bytes": len(html.encode("utf-8")),
                            "duration_s": dur2, "error": None}
        else:
            run["test2"] = {"passed": False, "preview": None,
                            "duration_s": dur2,
                            "error": "回复中未找到可渲染 HTML"}
    else:
        run["test2"] = {"passed": False, "preview": None,
                        "duration_s": dur2, "error": err}

    # 合并历史并写出
    if DATA_JSON.exists():
        data = json.loads(DATA_JSON.read_text(encoding="utf-8"))
    else:
        data = {"version": 1, "runs": []}
    data["runs"].append(run)
    data["runs"] = data["runs"][-MAX_RUNS_KEPT:]
    DATA_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                         encoding="utf-8")
    DATA_JS.write_text(
        "window.MONITOR_DATA = " + json.dumps(data, ensure_ascii=False) + ";\n",
        encoding="utf-8")

    t1 = "PASS" if run["test1"]["passed"] else "FAIL"
    t2 = "PASS" if run["test2"]["passed"] else "FAIL"
    print(f"[{ts}] run={run_id} test1={t1} (answer={run['test1']['answer']}) "
          f"test2={t2} dur={dur1}s/{dur2}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
