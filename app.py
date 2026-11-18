"""Codeforces VP Rating Simulator — historical counterfactual, not an official score."""

from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from cf_api import CFAPIError, clear_personal_cache, get_json, get_user_submissions
from persistent_handle import persistent_handle_input
from predictor_core import build_official_events, modeled_vp_contribution, simulate
from rating_rules import parse_unrated_vp_ids
from vp_utils import group_vp_sessions, reconstruct_vp_result


st.set_page_config(page_title="CF VP Rating Simulator", layout="wide")
TEXT = {
    "English": {
        "title": "Codeforces VP Rating Simulator",
        "subtitle": "Explore an estimated rating path with your Virtual Participations (VPs). "
                    "These values are model estimates, not official Codeforces ratings.",
        "handle": "Codeforces Handle", "run": "Analyze / Refresh",
        "clear": "Refresh personal API cache",
        "manual": "Unrated VP contest IDs (multiple; comma-separated)",
        "manual_help": "Optional bulk exclusion: enter 1084, 1200, 1350. "
                       "Use the VP table below to exclude individual sessions.",
        "official_toggle": "Compare with official rating",
        "unrated_toggle": "Show Unrated VPs on chart",
        "vp_section": "Virtual participation manager",
        "vp_help": "Tick Unrated for any VP session. The calculation updates without downloading data again. "
                   "For repeated VPs of one contest, each session has its own checkbox. "
                   "The optional ID field excludes all sessions of the specified contest.",
        "details": "Individual VP prediction details",
        "no_vps": "No supported virtual participation was found.",
        "metric_pred": "Simulated rating (with VP)",
        "metric_official": "Official rating",
        "metric_contribution": "VP modeled contribution",
        "metric_error": "Model vs. official (reference only)",
        "warning": "Incomplete historical data; some contests could not be simulated:",
        "note": "VP contribution compares two paths computed by the same approximation "
                "(with and without VP). It is not the official value of these VPs.",
        "no_data": "Enter a valid Codeforces Handle and click Analyze.",
        "date": "Date (UTC)", "contest": "Contest", "rank": "Estimated rank",
        "excluded": "Unrated", "solved": "AC", "score": "Score",
    },
    "中文": {
        "title": "Codeforces VP Rating 模拟器",
        "subtitle": "将虚拟参赛（VP）纳入历史时间线，估算 Rating 走势。结果仅供参考，不等同于官方 Rating。",
        "handle": "Codeforces Handle", "run": "开始分析 / 刷新数据",
        "clear": "刷新个人 API 缓存",
        "manual": "Unrated VP 比赛 ID（支持多个，逗号分隔）",
        "manual_help": "可批量输入 1084, 1200, 1350。也可以在下面的 VP 表格中逐场勾选，"
                       "同一比赛的多次 VP 可分别指定。",
        "official_toggle": "对比官方 Rating",
        "unrated_toggle": "在图表显示 Unrated VP",
        "vp_section": "可交互的 VP 管理",
        "vp_help": "勾选 Unrated 后直接重新模拟，无需重新下载数据。同一比赛多次 VP 分别显示。"
                   "上方输入的比赛 ID 会排除对应比赛的全部 VP。",
        "details": "每场比赛的预测详情",
        "no_vps": "没有找到支持的 VP 记录。",
        "metric_pred": "模拟 Rating（含 VP）",
        "metric_official": "官方实际 Rating",
        "metric_contribution": "VP 模拟贡献",
        "metric_error": "模拟与官方差距（仅参考）",
        "warning": "部分历史数据获取失败，以下比赛未能完整模拟：",
        "note": "VP 模拟贡献 = 含 VP 模拟结果 − 不含 VP 模拟结果，两条路线使用相同的近邻算法。"
                "该指标不是 VP 在官方规则下的真实收益。",
        "no_data": "输入 Codeforces Handle，再点击开始分析。",
        "date": "日期（UTC）", "contest": "比赛", "rank": "估计排名",
        "excluded": "Unrated", "solved": "AC", "score": "得分",
    },
}

lang = st.sidebar.selectbox("Language / 语言", ["English", "中文"])
T = TEXT[lang]
st.title(T["title"])
st.caption(T["subtitle"])

with st.sidebar:
    st.header("Configuration" if lang == "English" else "配置面板")
    HANDLE = persistent_handle_input(T["handle"])
    bulk_text = st.text_input(
        T["manual"], value="", placeholder="",
        help=T["manual_help"],
    )
    show_official = st.checkbox(T["official_toggle"], value=True)
    show_unrated = st.checkbox(T["unrated_toggle"], value=True)
    try:
        bulk_excluded = parse_unrated_vp_ids(bulk_text)
        bulk_valid = True
    except ValueError as exc:
        st.error(str(exc))
        bulk_excluded = frozenset()
        bulk_valid = False
    run_clicked = st.button(T["run"], type="primary", disabled=not bulk_valid)
    clear_clicked = st.button(T["clear"], disabled=not HANDLE)


def _date(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def load_analysis(handle):
    """Load network-derived data once; keep it independent of UI VP exclusions."""
    status = st.empty()
    progress = st.progress(0)
    warnings = []

    status.info("Fetching rated history and recent submissions...")
    real_data = get_json("user.rating", {"handle": handle}) or []
    submissions = get_user_submissions(handle)
    progress.progress(8)

    try:
        contests = get_json("contest.list", {"gym": "false"}) or []
        start_map = {
            c["id"]: c.get("startTimeSeconds")
            for c in contests if c.get("startTimeSeconds")
        }
    except CFAPIError as exc:
        start_map = {}
        warnings.append(f"contest.list unavailable: {exc}")
    progress.progress(14)

    events, real_history, missing_start = build_official_events(real_data, start_map)
    if missing_start:
        warnings.append(
            f"{missing_start} official contests lack startTimeSeconds; "
            "using their Rating update times as a fallback."
        )

    vp_sessions = [
        (cid, start, items)
        for cid, start, items in group_vp_sessions(submissions)
        if cid < 100000
    ]
    by_contest = {}
    for cid, start, items in vp_sessions:
        by_contest.setdefault(cid, []).append((start, items))

    total = len(by_contest)
    for n, (cid, sessions) in enumerate(by_contest.items(), 1):
        status.info(f"Reconstructing VPs: contest {n}/{total}...")
        try:
            standings = get_json("contest.standings", {"contestId": cid})
            if not standings:
                raise CFAPIError("Empty standings")
            name = standings["contest"].get("name", f"Contest {cid}")
            for start, items in sessions:
                detail = reconstruct_vp_result(items, start, standings)
                if detail is None:
                    warnings.append(f"VP contest {cid}: unsupported scoring format")
                    continue
                events.append({
                    "key": f"VP:{cid}:{start}",
                    "cid": cid, "ts": start, "type": "VP",
                    "rank": detail["rank"], "name": name,
                    "vp_details": detail,
                })
        except (CFAPIError, KeyError, TypeError, ValueError) as exc:
            warnings.append(f"VP contest {cid}: {exc}")
        progress.progress(14 + int(37 * n / max(total, 1)))

    events.sort(key=lambda event: (event["ts"], event["key"]))
    contest_ids = sorted({event["cid"] for event in events})
    changes_by_cid = {}
    for n, cid in enumerate(contest_ids, 1):
        status.info(f"Loading historical Rating results: {n}/{len(contest_ids)}...")
        try:
            changes_by_cid[cid] = get_json(
                "contest.ratingChanges", {"contestId": cid}
            )
            if not changes_by_cid[cid]:
                warnings.append(f"contest {cid}: official rating changes unavailable")
        except CFAPIError as exc:
            changes_by_cid[cid] = None
            warnings.append(str(exc))
        progress.progress(52 + int(48 * n / max(len(contest_ids), 1)))

    progress.empty()
    status.empty()
    return {
        "handle": handle,
        "events": events,
        "changes": changes_by_cid,
        "real_history": real_history,
        "warnings": warnings,
    }


def render_chart(with_vp, baseline, real_history, *, include_official, include_unrated):
    shown = (
        with_vp if include_unrated
        else [row for row in with_vp if not row.get("unrated", False)]
    )
    fig = go.Figure()
    if baseline:
        fig.add_trace(go.Scatter(
            x=[h["date"] for h in baseline], y=[h["rating"] for h in baseline],
            mode="lines", name="Simulated REAL only",
            line=dict(color="#8894A7", dash="dash", width=2),
            hovertemplate="%{y} Rating<extra>REAL-only model</extra>",
        ))
    if shown:
        fig.add_trace(go.Scatter(
            x=[h["date"] for h in shown], y=[h["rating"] for h in shown],
            mode="lines", name="Simulated REAL + VP",
            line=dict(color="#343434", width=2),
            hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=[h["date"] for h in shown],
            y=[h["rating"] for h in shown], mode="markers",
            marker=dict(
                color=["#DC5757" if h["type"] == "VP" else "#333333" for h in shown],
                symbol=["star" if h["type"] == "VP" else "circle" for h in shown],
                size=[12 if h["type"] == "VP" else 7 for h in shown],
            ),
            text=[
                f"{h['name']}<br>{h['type']} | Rank: {h['rank']}"
                f"<br>Rating: {h['rating']} | Δ: {h['delta']:+d}"
                for h in shown
            ],
            hovertemplate="%{text}<extra></extra>", showlegend=False,
        ))
    if include_official and real_history:
        fig.add_trace(go.Scatter(
            x=[h["date"] for h in real_history],
            y=[h["rating"] for h in real_history],
            mode="lines+markers", name="Official Rating",
            line=dict(color="#4389e4", dash="dot", width=2),
            marker=dict(size=6),
        ))
    fig.update_layout(
        title=f"Rating trajectory ({HANDLE})",
        yaxis_title="Rating", xaxis_title="Contest start / official update time (UTC)",
        legend=dict(orientation="h", y=1.12, x=0),
        height=540, hovermode="closest",
    )
    st.plotly_chart(fig, width="stretch")


if clear_clicked:
    clear_personal_cache(HANDLE.strip())
    st.session_state.pop("analysis_data", None)
    st.success("Personal API cache cleared. Click Analyze to reload.")

if run_clicked:
    clean_handle = HANDLE.strip()
    if not clean_handle:
        st.warning(T["no_data"])
    else:
        try:
            with st.spinner("Loading Codeforces history..."):
                st.session_state["analysis_data"] = load_analysis(clean_handle)
        except (CFAPIError, ValueError, KeyError) as exc:
            st.error(f"Cannot load Codeforces history: {exc}")

raw = st.session_state.get("analysis_data")
if not raw or raw["handle"].casefold() != HANDLE.strip().casefold():
    st.info(T["no_data"])
    st.stop()

if raw["warnings"]:
    with st.expander(f"{T['warning']} ({len(raw['warnings'])})"):
        for warning in raw["warnings"]:
            st.write(warning)

vp_events = [event for event in raw["events"] if event["type"] == "VP"]
st.subheader(T["vp_section"])
st.caption(T["vp_help"])

handle_key = HANDLE.strip().casefold()
override_store = st.session_state.setdefault("unrated_vp_sessions", {})
existing = override_store.get(handle_key, set())
event_by_key = {event["key"]: event for event in vp_events}
selected_keys = set(existing)
if vp_events:
    preview_exclusions = frozenset(
        existing | {event["key"] for event in vp_events
                    if event["cid"] in bulk_excluded}
    )
    preview_history, _ = simulate(
        raw["events"], raw["changes"], preview_exclusions
    )
    preview_by_key = {row["key"]: row for row in preview_history}
    editor_rows = []
    for event in vp_events:
        detail = event["vp_details"]
        editor_rows.append({
            "Session": event["key"],
            T["excluded"]: event["key"] in existing,
            T["contest"]: event["name"],
            T["date"]: _date(event["ts"]),
            T["rank"]: event["rank"],
            "Est. Δ": preview_by_key.get(event["key"], {}).get("model_delta"),
            "Bulk ID excluded": event["cid"] in bulk_excluded,
            T["solved"]: detail["solved"],
            T["score"]: detail["score"],
            "Link": f"https://codeforces.com/contest/{event['cid']}",
        })
    table = pd.DataFrame(editor_rows)
    edited = st.data_editor(
        table, width="stretch", hide_index=True, num_rows="fixed",
        column_config={
            "Session": None,
            T["excluded"]: st.column_config.CheckboxColumn(T["excluded"]),
            "Link": st.column_config.LinkColumn("Codeforces", display_text="Open"),
        },
        disabled=[T["contest"], T["date"], T["rank"], "Est. Δ", "Bulk ID excluded", T["solved"], T["score"], "Link"],
        key=f"vp_editor_{handle_key}",
    )
    selected_keys = {
        row["Session"] for _, row in edited.iterrows()
        if bool(row[T["excluded"]])
    }
    override_store[handle_key] = selected_keys
else:
    st.info(T["no_vps"])

# A contest-ID bulk exclusion always applies to all of its VP sessions.
excluded_keys = frozenset(
    selected_keys | {
        event["key"] for event in vp_events if event["cid"] in bulk_excluded
    }
)
with_vp, missing_with = simulate(raw["events"], raw["changes"], excluded_keys)
baseline, missing_real = simulate(
    raw["events"], raw["changes"], excluded_keys, include_vp=False
)
if missing_with or missing_real:
    st.warning(
        f"{len(set(missing_with + missing_real))} contest sessions were missing "
        "Rating-change data. Displayed estimates may be incomplete."
    )

last_rating = with_vp[-1]["rating"] if with_vp else 0
baseline_rating = baseline[-1]["rating"] if baseline else 0
official_rating = (
    raw["real_history"][-1]["rating"] if raw["real_history"] else 0
)
contribution = modeled_vp_contribution(with_vp, baseline)
a, b, c, d = st.columns(4)
a.metric(T["metric_pred"], last_rating)
b.metric(T["metric_official"], official_rating)
c.metric(T["metric_contribution"], f"{contribution:+d}")
d.metric(T["metric_error"], f"{baseline_rating - official_rating:+d}")
st.caption(T["note"])
render_chart(
    with_vp, baseline, raw["real_history"],
    include_official=show_official, include_unrated=show_unrated,
)

st.subheader(T["details"])
if vp_events:
    choices = [e["key"] for e in vp_events]
    key = st.selectbox(
        "Select VP" if lang == "English" else "选择一场 VP",
        choices, format_func=lambda ident: (
            f"{event_by_key[ident]['name']} — {_date(event_by_key[ident]['ts'])}"
        ),
        key=f"vp_inspect_{handle_key}",
    )
    event = event_by_key[key]
    item = next((x for x in with_vp if x["key"] == key), None)
    stats = event["vp_details"]
    st.markdown(
        f"**[{event['name']}](https://codeforces.com/contest/{event['cid']})**"
        f" · {_date(event['ts'])}"
    )
    first, second, third, fourth = st.columns(4)
    first.metric(T["rank"], stats["rank"])
    second.metric(T["solved"], stats["solved"])
    third.metric(T["score"], stats["score"])
    fourth.metric("Estimated model Δ", "Unrated" if item and item.get("unrated")
                  else (f"{item['model_delta']:+d}" if item and not item.get("unavailable")
                        else "Unavailable"))
    if stats.get("penalty") is not None:
        st.caption(f"ICPC penalty: {stats['penalty']} min")
    with st.expander("Solved problems / 已通过题目", expanded=False):
        if stats["problems"]:
            st.dataframe(pd.DataFrame(stats["problems"]), hide_index=True,
                         width="stretch")
        else:
            st.write("No accepted submissions.")
    st.markdown("**Five nearest proxies / 五名参考选手**")
    if item and item["proxies"]:
        st.dataframe(
            pd.DataFrame(item["proxies"]), hide_index=True, width="stretch",
            column_config={"Profile": st.column_config.LinkColumn(
                "Codeforces profile", display_text="Open"
            )},
        )
        st.caption("Proxy rows come from the original contest. The model trims the largest "
                   "and smallest adjusted Deltas before averaging (when at least 3 exist).")
    else:
        st.info("No proxy estimate (Unrated or unavailable historical rating data).")
