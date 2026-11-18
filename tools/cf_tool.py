#!/usr/bin/env python3
"""Codeforces signed API CLI & problem-sync toolkit for X230 / HK."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import html as html_lib
import json
import os
import pathlib
import random
import re
import shutil
import string
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DEFAULT_SECRET_PATH = pathlib.Path.home() / ".config" / "secrets" / "codeforces.json"
DEFAULT_SHITI_DIR = pathlib.Path(__file__).resolve().parent.parent
API_BASE = "https://codeforces.com/api"
USER_AGENT = "StillFloatingCF/1.0 (+https://stillfloating.top)"
TZ_CST = datetime.timezone(datetime.timedelta(hours=8))


def load_credentials(secret_path: pathlib.Path | None = None) -> dict[str, str]:
    """Load Codeforces API credentials from env vars or secret JSON file."""
    env_key = os.environ.get("CF_API_KEY", "").strip()
    env_sec = os.environ.get("CF_API_SECRET", "").strip()
    env_handle = os.environ.get("CF_HANDLE", "").strip()

    data: dict[str, Any] = {}
    path = secret_path or pathlib.Path(os.environ.get("CF_SECRET_FILE", str(DEFAULT_SECRET_PATH)))
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        except Exception:
            data = {}

    return {
        "handle": env_handle or str(data.get("handle", "")).strip(),
        "api_key": env_key or str(data.get("api_key", "")).strip(),
        "api_secret": env_sec or str(data.get("api_secret", "")).strip(),
    }


def fmt_ts(epoch_sec: int | float | None) -> str:
    """Format unix epoch seconds as CST string."""
    if not epoch_sec or int(epoch_sec) <= 0:
        return ""
    return datetime.datetime.fromtimestamp(int(epoch_sec), tz=TZ_CST).strftime("%Y-%m-%d %H:%M")


def _local_proxy_url() -> str:
    proxy = (
        os.environ.get("HTTPS_PROXY")
        or os.environ.get("https_proxy")
        or os.environ.get("HTTP_PROXY")
        or os.environ.get("http_proxy")
        or ""
    ).strip()
    if proxy:
        return proxy
    import socket
    try:
        with socket.create_connection(("127.0.0.1", 7897), timeout=0.25):
            return "http://127.0.0.1:7897"
    except OSError:
        return ""


def _build_opener() -> urllib.request.OpenerDirector:
    proxy = _local_proxy_url()
    if proxy:
        return urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    return urllib.request.build_opener()


def api_call(
    method: str,
    params: dict[str, Any] | None = None,
    *,
    signed: bool = True,
    timeout: float = 15.0,
    creds: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Call a Codeforces API method, signing with apiKey/apiSig when credentials exist."""
    creds = creds or load_credentials()
    clean_params: dict[str, str] = {}
    for k, v in (params or {}).items():
        if v is not None and str(v) != "":
            clean_params[str(k)] = str(v)

    if signed and creds.get("api_key") and creds.get("api_secret"):
        clean_params["apiKey"] = creds["api_key"]
        clean_params["time"] = str(int(datetime.datetime.now(datetime.timezone.utc).timestamp()))
        rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
        sorted_items = sorted(clean_params.items(), key=lambda kv: (kv[0], kv[1]))
        param_str = "&".join(f"{k}={v}" for k, v in sorted_items)
        sig_base = f"{rand}/{method}?{param_str}#{creds['api_secret']}"
        clean_params["apiSig"] = rand + hashlib.sha512(sig_base.encode("utf-8")).hexdigest()

    qs = urllib.parse.urlencode(clean_params)
    url = f"{API_BASE}/{method}" + (f"?{qs}" if qs else "")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    opener = _build_opener()
    try:
        with opener.open(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
    except urllib.error.HTTPError as err:
        raw = err.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw)
        except Exception:
            raise RuntimeError(f"HTTP {err.code}: {raw[:300]}") from err
    except Exception as exc:
        raise RuntimeError(f"请求 Codeforces API 失败: {exc}") from exc

    if not isinstance(data, dict) or data.get("status") != "OK":
        comment = data.get("comment") if isinstance(data, dict) else str(data)
        raise RuntimeError(f"Codeforces API 错误 ({method}): {comment}")
    return data


def _fetch_html(url: str, timeout: float = 12.0) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    opener = _build_opener()
    with opener.open(req, timeout=timeout) as resp:
        return resp.read(1_500_000).decode("utf-8", errors="replace")


def parse_problem_ref(target: str) -> tuple[int, str]:
    """Parse '2037C', '2037 C', '2037/C', or CF problem URL into (contest_id, index)."""
    s = target.strip()
    m = re.search(r"codeforces\.com/(?:contest|gym)/(\d+)/problem/([A-Za-z0-9]+)", s, re.I)
    if m:
        return int(m.group(1)), m.group(2).upper()
    m = re.search(r"codeforces\.com/problemset/problem/(\d+)/([A-Za-z0-9]+)", s, re.I)
    if m:
        return int(m.group(1)), m.group(2).upper()
    m = re.fullmatch(r"(?:CF)?\s*(\d+)\s*[-_/:\s]?\s*([A-Za-z][0-9A-Za-z]*)", s, re.I)
    if m:
        return int(m.group(1)), m.group(2).upper()
    raise ValueError(f"无法识别的 Codeforces 题号或链接: {target}")


def _clean_cf_html_fragment(fragment: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.I)
    text = re.sub(r"</(?:p|div|li|tr)>", "\n", text, flags=re.I)
    text = re.sub(r"<li>", "- ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_lib.unescape(text)
    text = text.replace("\xa0", " ")
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(lines).strip()


def _extract_pre_text(pre_html: str) -> str:
    lines = re.findall(r'<div[^>]*class="[^"]*test-example-line[^"]*"[^>]*>(.*?)</div>', pre_html, re.I | re.S)
    if lines:
        cleaned = [html_lib.unescape(re.sub(r"<[^>]+>", "", ln)).rstrip("\r") for ln in lines]
        return "\n".join(cleaned).strip() + "\n"
    txt = re.sub(r"<br\s*/?>", "\n", pre_html, flags=re.I)
    txt = re.sub(r"<[^>]+>", "", txt)
    txt = html_lib.unescape(txt).replace("\r\n", "\n").strip()
    return (txt + "\n") if txt else ""


def scrape_problem_page(contest_id: int, index: str) -> dict[str, Any]:
    """Fetch problem statement and samples from CF webpage (best-effort)."""
    urls = [
        f"https://codeforces.com/contest/{contest_id}/problem/{index}",
        f"https://codeforces.com/problemset/problem/{contest_id}/{index}",
    ]
    last_err = ""
    for url in urls:
        try:
            page = _fetch_html(url, timeout=12.0)
        except Exception as exc:
            last_err = str(exc)
            continue
        if "problem-statement" not in page:
            last_err = "页面未包含题面（可能触发 Cloudflare 验证或题目不存在）"
            continue

        title_m = re.search(r'<div class="title">(.*?)</div>', page, re.S)
        time_m = re.search(r'<div class="time-limit">.*?</div>(.*?)</div>', page, re.S)
        if not time_m:
            time_m = re.search(r'<div class="time-limit">(.*?)</div>', page, re.S)
        mem_m = re.search(r'<div class="memory-limit">(.*?)</div>', page, re.S)

        inputs = re.findall(r'<div class="input">\s*<div class="title">.*?</div>\s*<pre[^>]*>(.*?)</pre>', page, re.S)
        outputs = re.findall(r'<div class="output">\s*<div class="title">.*?</div>\s*<pre[^>]*>(.*?)</pre>', page, re.S)
        samples = []
        for idx, (inp, outp) in enumerate(zip(inputs, outputs), start=1):
            samples.append({
                "case": idx,
                "input": _extract_pre_text(inp),
                "output": _extract_pre_text(outp),
            })

        stmt_m = re.search(r'<div class="problem-statement">(.*?)<script type="text/javascript">', page, re.S)
        stmt_text = _clean_cf_html_fragment(stmt_m.group(1)) if stmt_m else ""

        return {
            "scraped": True,
            "url": url,
            "page_title": _clean_cf_html_fragment(title_m.group(1)) if title_m else "",
            "time_limit": _clean_cf_html_fragment(time_m.group(1)) if time_m else "",
            "memory_limit": _clean_cf_html_fragment(mem_m.group(1)) if mem_m else "",
            "samples": samples,
            "statement_text": stmt_text[:6000],
        }
    return {"scraped": False, "error": last_err or "抓取失败", "samples": []}


def get_user_info(handle: str, creds: dict[str, str] | None = None) -> dict[str, Any]:
    res = api_call("user.info", {"handles": handle}, signed=True, creds=creds)["result"]
    if not res:
        raise RuntimeError(f"未找到用户: {handle}")
    u = res[0]
    return {
        "handle": u.get("handle", handle),
        "rating": u.get("rating"),
        "maxRating": u.get("maxRating"),
        "rank": u.get("rank") or "unrated",
        "maxRank": u.get("maxRank") or "unrated",
        "contribution": u.get("contribution", 0),
        "friendOfCount": u.get("friendOfCount", 0),
        "lastOnline": fmt_ts(u.get("lastOnlineTimeSeconds")),
        "registered": fmt_ts(u.get("registrationTimeSeconds")),
        "avatar": u.get("avatar", ""),
        "titlePhoto": u.get("titlePhoto", ""),
        "profileUrl": f"https://codeforces.com/profile/{u.get('handle', handle)}",
    }


def get_user_rating(handle: str, limit: int = 15, creds: dict[str, str] | None = None) -> list[dict[str, Any]]:
    res = api_call("user.rating", {"handle": handle}, signed=True, creds=creds)["result"]
    out = []
    for row in reversed(res[-limit:]):
        old_r = int(row.get("oldRating", 0))
        new_r = int(row.get("newRating", 0))
        out.append({
            "contestId": row.get("contestId"),
            "contestName": row.get("contestName", ""),
            "rank": row.get("rank"),
            "oldRating": old_r,
            "newRating": new_r,
            "delta": new_r - old_r,
            "time": fmt_ts(row.get("ratingUpdateTimeSeconds")),
            "url": f"https://codeforces.com/contest/{row.get('contestId')}",
        })
    return out


def get_user_submissions(
    handle: str,
    count: int = 20,
    verdict: str = "ALL",
    creds: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    fetch_count = max(count, 100) if verdict.upper() != "ALL" else count
    res = api_call("user.status", {"handle": handle, "from": 1, "count": min(fetch_count, 500)}, signed=True, creds=creds)["result"]
    target_v = verdict.upper()
    out = []
    for sub in res:
        v = str(sub.get("verdict") or "TESTING")
        if target_v != "ALL":
            if target_v == "NON_AC" and v == "OK":
                continue
            elif target_v != "NON_AC" and v != target_v:
                continue
        prob = sub.get("problem") or {}
        cid = prob.get("contestId")
        idx = str(prob.get("index", ""))
        out.append({
            "id": sub.get("id"),
            "contestId": cid,
            "index": idx,
            "code": f"{cid}{idx}" if cid else idx,
            "name": prob.get("name", ""),
            "rating": prob.get("rating"),
            "tags": prob.get("tags") or [],
            "verdict": v,
            "language": sub.get("programmingLanguage", ""),
            "timeConsumedMs": sub.get("timeConsumedMillis", 0),
            "memoryConsumedKB": round(int(sub.get("memoryConsumedBytes", 0)) / 1024),
            "passedTestCount": sub.get("passedTestCount", 0),
            "participantType": (sub.get("author") or {}).get("participantType", ""),
            "time": fmt_ts(sub.get("creationTimeSeconds")),
            "problemUrl": f"https://codeforces.com/contest/{cid}/problem/{idx}" if cid else "",
            "submissionUrl": f"https://codeforces.com/contest/{cid}/submission/{sub.get('id')}" if cid else "",
        })
        if len(out) >= count:
            break
    return out


def get_wrong_problems(
    handle: str,
    limit: int = 20,
    include_solved: bool = False,
    creds: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    res = api_call("user.status", {"handle": handle, "from": 1, "count": 500}, signed=True, creds=creds)["result"]
    ac_keys: set[str] = set()
    grouped: dict[str, dict[str, Any]] = {}
    for sub in res:
        prob = sub.get("problem") or {}
        cid = prob.get("contestId")
        idx = str(prob.get("index", ""))
        key = f"{cid}:{idx}" if cid else str(prob.get("name", ""))
        v = str(sub.get("verdict") or "TESTING")
        if v == "OK":
            ac_keys.add(key)
            continue
        if key not in grouped:
            grouped[key] = {
                "contestId": cid,
                "index": idx,
                "code": f"{cid}{idx}" if cid else idx,
                "name": prob.get("name", ""),
                "rating": prob.get("rating"),
                "tags": prob.get("tags") or [],
                "lastVerdict": v,
                "lastTime": fmt_ts(sub.get("creationTimeSeconds")),
                "attempts": 1,
                "problemUrl": f"https://codeforces.com/contest/{cid}/problem/{idx}" if cid else "",
            }
        else:
            grouped[key]["attempts"] += 1

    out = []
    for key, item in grouped.items():
        is_solved = key in ac_keys
        if not include_solved and is_solved:
            continue
        item["eventuallySolved"] = is_solved
        out.append(item)
        if len(out) >= limit:
            break
    return out


def _get_contest_standings_meta(contest_id: int, creds: dict[str, str] | None = None) -> dict[str, Any]:
    cache_path = pathlib.Path(f"/tmp/cf-contest-meta-{contest_id}.json")
    if cache_path.is_file():
        try:
            age = datetime.datetime.now().timestamp() - cache_path.stat().st_mtime
            if age < 1800:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
                if isinstance(cached, dict) and "problems" in cached:
                    return cached
        except Exception:
            pass
    st = api_call(
        "contest.standings",
        {"contestId": contest_id},
        signed=False,
        timeout=30.0,
        creds=creds,
    )["result"]
    meta = {
        "contest": st.get("contest") or {},
        "problems": st.get("problems") or [],
    }
    try:
        cache_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    return meta


def get_contest_detail(
    contest_id: int,
    handle: str = "",
    creds: dict[str, str] | None = None,
) -> dict[str, Any]:
    st = _get_contest_standings_meta(contest_id, creds=creds)
    contest = st.get("contest") or {}
    probs = []
    for p in st.get("problems") or []:
        idx = str(p.get("index", ""))
        probs.append({
            "index": idx,
            "name": str(p.get("name", "")),
            "rating": p.get("rating"),
            "tags": p.get("tags") or [],
            "points": p.get("points"),
            "url": f"https://codeforces.com/contest/{contest_id}/problem/{idx}",
        })

    my_perf: dict[str, Any] | None = None
    if handle:
        try:
            subs = api_call("contest.status", {"contestId": contest_id, "handle": handle, "from": 1, "count": 200}, signed=True, creds=creds)["result"]
        except Exception:
            subs = []
        if subs:
            by_idx: dict[str, dict[str, Any]] = {}
            for sub in subs:
                p = sub.get("problem") or {}
                idx = str(p.get("index", ""))
                v = str(sub.get("verdict") or "")
                cur = by_idx.setdefault(idx, {"index": idx, "solved": False, "attempts": 0, "lastVerdict": v, "lastLanguage": sub.get("programmingLanguage", ""), "lastTime": fmt_ts(sub.get("creationTimeSeconds"))})
                cur["attempts"] += 1
                if v == "OK":
                    cur["solved"] = True
            my_perf = {
                "handle": handle,
                "submissionCount": len(subs),
                "solvedIndexes": sorted(k for k, v in by_idx.items() if v["solved"]),
                "problemSummary": [by_idx[k] for k in sorted(by_idx.keys())],
            }

    return {
        "id": contest.get("id", contest_id),
        "name": contest.get("name", ""),
        "type": contest.get("type", ""),
        "phase": contest.get("phase", ""),
        "startTime": fmt_ts(contest.get("startTimeSeconds")),
        "durationMin": int(contest.get("durationSeconds", 0)) // 60,
        "url": f"https://codeforces.com/contest/{contest_id}",
        "problems": probs,
        "myPerformance": my_perf,
    }


def resolve_contest_id(query: str, creds: dict[str, str] | None = None) -> int:
    q = query.strip()
    m = re.search(r"codeforces\.com/(?:contest|gym)/(\d+)", q, re.I)
    if m:
        return int(m.group(1))
    if q.isdigit():
        return int(q)
    contests = api_call("contest.list", {"gym": "false"}, signed=False, creds=creds)["result"]
    tokens = [t.lower() for t in re.split(r"[\s\-_/(),]+", q) if t and t.lower() not in {"cf", "codeforces"}]
    best_id = 0
    best_score = 0
    for c in contests:
        name_low = str(c.get("name", "")).lower()
        score = 0
        for tok in tokens:
            if re.fullmatch(r"\d+", tok) and re.search(rf"\b{re.escape(tok)}\b", name_low):
                score += 5
            elif tok in name_low:
                score += 2
        if score > best_score:
            best_score = score
            best_id = int(c["id"])
    if not best_id:
        raise RuntimeError(f"未找到匹配的 Codeforces 比赛: {query}")
    return best_id


def get_problem_detail(contest_id: int, index: str, creds: dict[str, str] | None = None) -> dict[str, Any]:
    detail = get_contest_detail(contest_id, handle="", creds=creds)
    meta = next((p for p in detail["problems"] if p["index"].upper() == index.upper()), None)
    scraped = scrape_problem_page(contest_id, index.upper())
    return {
        "contestId": contest_id,
        "contestName": detail["name"],
        "index": index.upper(),
        "code": f"{contest_id}{index.upper()}",
        "name": (meta or {}).get("name") or scraped.get("page_title") or f"{contest_id}{index.upper()}",
        "rating": (meta or {}).get("rating"),
        "tags": (meta or {}).get("tags") or [],
        "url": f"https://codeforces.com/contest/{contest_id}/problem/{index.upper()}",
        "timeLimit": scraped.get("time_limit", ""),
        "memoryLimit": scraped.get("memory_limit", ""),
        "samples": scraped.get("samples", []),
        "statement": scraped.get("statement_text", ""),
        "scraped": scraped.get("scraped", False),
        "scrapeError": scraped.get("error", ""),
    }


def sync_problem_to_shiti(
    target: str,
    shiti_dir: pathlib.Path | None = None,
    overwrite_sol: bool = False,
    creds: dict[str, str] | None = None,
) -> dict[str, Any]:
    cid, idx = parse_problem_ref(target)
    prob = get_problem_detail(cid, idx, creds=creds)
    base = shiti_dir or DEFAULT_SHITI_DIR
    prob_dir = base / "problems" / f"cf-{cid}{idx}"
    prob_dir.mkdir(parents=True, exist_ok=True)

    sol_path = prob_dir / "sol.cpp"
    tpl_path = base / "template.cpp"
    if overwrite_sol or not sol_path.exists():
        header = (
            f"// Codeforces {cid}{idx}: {prob['name']}\n"
            f"// URL: {prob['url']}\n"
            f"// Rating: {prob['rating'] or 'Unknown'} | Tags: {', '.join(prob['tags']) or 'None'}\n\n"
        )
        body = tpl_path.read_text(encoding="utf-8") if tpl_path.is_file() else "#include <bits/stdc++.h>\nusing namespace std;\nint main(){return 0;}\n"
        sol_path.write_text(header + body, encoding="utf-8")

    samples = prob.get("samples") or []
    in_path = prob_dir / "in.txt"
    exp_path = prob_dir / "expected.txt"
    if samples:
        in_path.write_text(samples[0]["input"], encoding="utf-8")
        exp_path.write_text(samples[0]["output"], encoding="utf-8")
        (prob_dir / "samples.json").write_text(json.dumps(samples, ensure_ascii=False, indent=2), encoding="utf-8")
    elif not in_path.exists():
        in_path.write_text("", encoding="utf-8")

    md_lines = [
        f"# {cid}{idx}. {prob['name']}",
        "",
        f"- 比赛：{prob['contestName']}",
        f"- 链接：{prob['url']}",
        f"- 难度：{prob['rating'] or '未知'}",
        f"- 标签：{', '.join(prob['tags']) or '无'}",
    ]
    if prob.get("timeLimit"):
        md_lines.append(f"- 限制：{prob['timeLimit']} / {prob.get('memoryLimit', '')}")
    if samples:
        md_lines.append("")
        for s in samples:
            md_lines.extend([
                f"## 样例 {s['case']}",
                "```text",
                s["input"].rstrip("\n"),
                "```",
                "输出：",
                "```text",
                s["output"].rstrip("\n"),
                "```",
            ])
    if prob.get("statement"):
        md_lines.extend(["", "## 题面摘录", "", prob["statement"]])
    elif prob.get("scrapeError"):
        md_lines.extend(["", f"> 注：题面网页抓取未成功（{prob['scrapeError']}），已同步 API 元信息。"])

    (prob_dir / "problem.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return {
        "dir": str(prob_dir),
        "sol": str(sol_path),
        "in": str(in_path),
        "samplesCount": len(samples),
        "problem": prob,
    }


def _print_json(obj: Any) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cf", description="Codeforces API CLI (signed)")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_me = sub.add_parser("me", aliases=["info"], help="查看账号信息与 Rating")
    p_me.add_argument("handle", nargs="?", default="", help="CF handle（默认读凭据）")

    p_rat = sub.add_parser("rating", help="查看 Rating 变化记录")
    p_rat.add_argument("handle", nargs="?", default="")
    p_rat.add_argument("-n", "--limit", type=int, default=15)

    p_subs = sub.add_parser("subs", help="查看近期提交记录")
    p_subs.add_argument("handle", nargs="?", default="")
    p_subs.add_argument("-n", "--count", type=int, default=20)
    p_subs.add_argument("--verdict", default="ALL", help="ALL / OK / NON_AC / WRONG_ANSWER 等")

    p_wr = sub.add_parser("wrongs", help="查看近期错题/未过题")
    p_wr.add_argument("handle", nargs="?", default="")
    p_wr.add_argument("-n", "--limit", type=int, default=20)
    p_wr.add_argument("--all", action="store_true", help="包含后来已 AC 的错题")

    p_con = sub.add_parser("contest", help="查看比赛题单与个人表现")
    p_con.add_argument("query", help="比赛编号、链接或名称关键字")
    p_con.add_argument("--handle", default="")

    p_prob = sub.add_parser("problem", help="查看单题详情与样例")
    p_prob.add_argument("target", nargs="+", help="如 2037C 或 2037 C 或题目链接")

    p_sync = sub.add_parser("sync", help="同步题目到刷题工作区 problems/cf-<题号>/")
    p_sync.add_argument("target", nargs="+", help="如 2037C 或 2037 C 或题目链接")
    p_sync.add_argument("--dir", default="", help="刷题工作区根目录")
    p_sync.add_argument("--force", action="store_true", help="覆盖已存在的 sol.cpp")

    p_call = sub.add_parser("call", help="直接调用任意签名 Codeforces API")
    p_call.add_argument("method", help="如 user.info / contest.hacks")
    p_call.add_argument("kv", nargs="*", help="key=value 参数")

    args = parser.parse_args(argv)
    creds = load_credentials()
    default_handle = creds.get("handle", "")

    if args.cmd in ("me", "info"):
        h = args.handle or default_handle
        if not h:
            raise SystemExit("缺少 handle")
        info = get_user_info(h, creds=creds)
        if args.json:
            _print_json(info)
        else:
            print(f"{info['handle']}  |  Rating: {info['rating'] or 'Unrated'} (max {info['maxRating'] or '-'})  |  Rank: {info['rank']}")
            print(f"最近在线: {info['lastOnline']}  |  注册: {info['registered']}  |  主页: {info['profileUrl']}")
        return 0

    if args.cmd == "rating":
        h = args.handle or default_handle
        rows = get_user_rating(h, limit=args.limit, creds=creds)
        if args.json:
            _print_json(rows)
        elif not rows:
            print(f"{h} 暂无 Rating 比赛记录。")
        else:
            for r in rows:
                sign = "+" if r["delta"] >= 0 else ""
                print(f"[{r['contestId']}] {r['contestName']} | #{r['rank']} | {r['oldRating']} -> {r['newRating']} ({sign}{r['delta']}) | {r['time']}")
        return 0

    if args.cmd == "subs":
        h = args.handle or default_handle
        rows = get_user_submissions(h, count=args.count, verdict=args.verdict, creds=creds)
        if args.json:
            _print_json(rows)
        elif not rows:
            print(f"{h} 暂无符合条件的提交记录。")
        else:
            for s in rows:
                print(f"{s['time']} | {s['code']:<7} {s['name'][:32]:<32} | {s['verdict']:<20} | {s['timeConsumedMs']}ms {s['memoryConsumedKB']}KB | {s['language']}")
        return 0

    if args.cmd == "wrongs":
        h = args.handle or default_handle
        rows = get_wrong_problems(h, limit=args.limit, include_solved=args.all, creds=creds)
        if args.json:
            _print_json(rows)
        elif not rows:
            print(f"{h} 暂无未解决的错题记录。")
        else:
            for w in rows:
                solved_tag = " [已补过]" if w["eventuallySolved"] else ""
                print(f"{w['code']:<7} {w['name']} (难度:{w['rating'] or '?'}) | 尝试 {w['attempts']} 次 · 最后 {w['lastVerdict']}{solved_tag} | {w['problemUrl']}")
        return 0

    if args.cmd == "contest":
        cid = resolve_contest_id(args.query, creds=creds)
        detail = get_contest_detail(cid, handle=args.handle or default_handle, creds=creds)
        if args.json:
            _print_json(detail)
        else:
            print(f"[{detail['id']}] {detail['name']} ({detail['type']} · {detail['phase']})")
            print(f"时间: {detail['startTime']} · {detail['durationMin']} 分钟 | {detail['url']}")
            if detail["myPerformance"]:
                mp = detail["myPerformance"]
                print(f"我的提交: {mp['submissionCount']} 次 | AC 题号: {', '.join(mp['solvedIndexes']) or '无'}")
            for p in detail["problems"]:
                print(f"  {p['index']:<3} {p['name']} (rating:{p['rating'] or '?'}) [{', '.join(p['tags'])}]")
        return 0

    if args.cmd == "problem":
        cid, idx = parse_problem_ref(" ".join(args.target))
        prob = get_problem_detail(cid, idx, creds=creds)
        if args.json:
            _print_json(prob)
        else:
            print(f"{prob['code']}. {prob['name']} (Rating: {prob['rating'] or '?'})")
            print(f"标签: {', '.join(prob['tags']) or '无'} | 链接: {prob['url']}")
            if prob["samples"]:
                for s in prob["samples"]:
                    print(f"--- 样例 {s['case']} 输入 ---\n{s['input'].rstrip()}\n--- 输出 ---\n{s['output'].rstrip()}")
            elif prob.get("scrapeError"):
                print(f"提示: {prob['scrapeError']}")
        return 0

    if args.cmd == "sync":
        shiti = pathlib.Path(args.dir) if args.dir else None
        res = sync_problem_to_shiti(" ".join(args.target), shiti_dir=shiti, overwrite_sol=args.force, creds=creds)
        if args.json:
            _print_json(res)
        else:
            print(f"已同步 {res['problem']['code']} ({res['problem']['name']}) -> {res['dir']}")
            print(f"样例数: {res['samplesCount']} | 源文件: {res['sol']}")
        return 0

    if args.cmd == "call":
        kv: dict[str, str] = {}
        for item in args.kv:
            if "=" not in item:
                raise SystemExit(f"参数格式应为 key=value: {item}")
            k, v = item.split("=", 1)
            kv[k] = v
        _print_json(api_call(args.method, kv, signed=True, creds=creds))
        return 0

    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"错误: {exc}", file=sys.stderr)
        raise SystemExit(1)
