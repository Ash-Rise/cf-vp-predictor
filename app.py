"""Codeforces VP Rating Simulator — historical counterfactual, not an official score."""

from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from cf_api import CFAPIError, clear_personal_cache, get_json, get_user_submissions
from chart_controls import PLOTLY_CONFIG, lock_rating_chart
from persistent_handle import persistent_handle_input
from predictor_core import build_official_events, modeled_vp_contribution, simulate
from unrated_storage import parse_saved_value, sync_unrated_storage
from vp_utils import group_vp_sessions, reconstruct_vp_result


st.set_page_config(page_title="CF VP Rating Simulator", layout="wide")
TEXT = {
    "English": {
        "title": "Codeforces VP Rating Simulator",
        "subtitle": "Explore an estimated rating path with your Virtual Participations (VPs). "
                    "These values are model estimates, not official Codeforces ratings.",
        "handle": "Codeforces Handle", "run": "Analyze / Refresh",
        "clear": "Refresh personal API cache",
        "official_toggle": "Compare with official rating",
        "unrated_toggle": "Show Unrated VPs on chart",
        "vp_section": "Virtual participation manager",
        "vp_help": "Tick Unrated for any VP session. The calculation updates without downloading data again. "
                   "For repeated VPs of one contest, each session has its own checkbox.",
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
        "incomplete": "Historical data is incomplete. Final simulated Rating and VP contribution are unavailable; the chart shows only the reliable prefix.",
        "missing_rounds": "Rating changes are missing from: {names}",
        "retry_failed": "Retry missing Rating data",
        "date": "Date (UTC)", "contest": "Contest", "rank": "Estimated rank",
        "excluded": "Unrated", "solved": "AC", "score": "Score",
        "config": "Configuration", "loading_history": "Loading contest and submission history…",
        "loading_vp": "Reconstructing VP results: {done}/{total}",
        "loading_rating": "Loading official Rating changes: {done}/{total}",
        "cache_cleared": "Personal data cache cleared. Analyze again to refresh.",
        "loading_analysis": "Analyzing Codeforces history…",
        "loading_error": "Could not load history: {error}",
        "time_fallback": "{count} contests have no start time; Rating update times were used.",
        "vp_unsupported": "Contest #{cid}: unsupported scoring mode",
        "vp_failed": "Contest #{cid}: {error}",
        "changes_missing": "Contest #{cid}: Rating changes unavailable",
        "chart_title": "Rating history", "chart_axis": "Contest time (UTC)",
        "legend_real_only": "REAL-only simulation", "legend_with_vp": "REAL + VP simulation",
        "legend_official": "Official Rating",
        "detail_select": "Select a VP session", "detail_delta": "Estimated Delta",
        "detail_unavailable": "Unavailable", "detail_solved": "Solved problems",
        "detail_empty": "No accepted submissions.", "detail_proxies": "Five nearest proxy participants",
        "detail_profile": "Profile",
        "detail_proxy_note": "The highest and lowest adjusted Deltas are removed before averaging when at least three proxies exist.",
        "detail_no_proxies": "No proxy estimate (Unrated or missing rating data).",
        "detail_penalty": "ICPC penalty: {minutes} min",
        "mobile_mode": "Mobile-friendly cards", "card_link": "Open contest",
        "preview_title": "Identified sessions: {total} (showing first 10 while loading Rating data)",
        "detail_problem": "Problem", "detail_minute": "AC minute",
        "detail_wa": "Wrong attempts", "proxy_rating": "Pre-contest Rating",
        "proxy_rank": "Rank", "proxy_official": "Official Delta",
        "proxy_adjustment": "Rank adjustment", "proxy_adjusted": "Adjusted Delta",
        "proxy_distance": "Distance", "proxy_handle": "Handle",
    },
    "中文": {
        "title": "Codeforces VP Rating 模拟器",
        "subtitle": "将虚拟参赛（VP）纳入历史时间线，估算 Rating 走势。结果仅供参考，不等同于官方 Rating。",
        "handle": "Codeforces Handle", "run": "开始分析 / 刷新数据",
        "clear": "刷新个人 API 缓存",
        "official_toggle": "对比官方 Rating",
        "unrated_toggle": "在图表显示 Unrated VP",
        "vp_section": "可交互的 VP 管理",
        "vp_help": "勾选 Unrated 后直接重新模拟，无需重新下载数据。同一比赛多次 VP 分别显示。",
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
        "incomplete": "历史数据不完整：不展示最终模拟 Rating 或 VP 贡献。曲线只绘制缺失数据之前的有效部分。",
        "missing_rounds": "以下比赛缺少 Rating 变化数据：{names}",
        "retry_failed": "重试缺失的 Rating 数据",
        "date": "日期（UTC）", "contest": "比赛", "rank": "估计排名",
        "excluded": "Unrated", "solved": "AC", "score": "得分",
        "config": "配置面板", "loading_history": "正在获取正式比赛与提交历史…",
        "loading_vp": "正在重建 VP 成绩：{done}/{total}",
        "loading_rating": "正在获取官方 Rating 数据：{done}/{total}",
        "cache_cleared": "个人数据缓存已清除，请重新点击开始分析。",
        "loading_analysis": "正在分析 Codeforces 历史记录…",
        "loading_error": "获取历史数据失败：{error}",
        "time_fallback": "有 {count} 场正式比赛缺少开始时间，已暂用 Rating 更新时间排序。",
        "vp_unsupported": "比赛 #{cid}：不支持的计分规则",
        "vp_failed": "比赛 #{cid}：{error}",
        "changes_missing": "比赛 #{cid}：官方 Rating 变化数据暂不可用",
        "chart_title": "Rating 走势", "chart_axis": "比赛时间（UTC）",
        "legend_real_only": "仅正式比赛（模拟）", "legend_with_vp": "正式比赛 + VP（模拟）",
        "legend_official": "官方实际 Rating",
        "detail_select": "选择一场 VP", "detail_delta": "预估 Delta",
        "detail_unavailable": "数据不可用", "detail_solved": "已通过的题目",
        "detail_empty": "暂无通过的题目。", "detail_proxies": "五名最近邻参考选手",
        "detail_profile": "选手主页",
        "detail_proxy_note": "至少有三名参考选手时，去掉调整后 Delta 的最大值与最小值，再对其余值取平均。",
        "detail_no_proxies": "暂无参考选手数据（Unrated 或官方历史数据缺失）。",
        "detail_penalty": "ICPC 罚时：{minutes} 分钟",
        "mobile_mode": "手机卡片视图", "card_link": "打开比赛",
        "preview_title": "已识别 {total} 场比赛（正在读取 Rating 数据，暂展示前 10 场）",
        "detail_problem": "题目", "detail_minute": "通过时间（分钟）",
        "detail_wa": "错误提交", "proxy_rating": "赛前 Rating",
        "proxy_rank": "排名", "proxy_official": "官方 Delta",
        "proxy_adjustment": "排名修正", "proxy_adjusted": "调整后 Delta",
        "proxy_distance": "距离", "proxy_handle": "选手",
    },
}

lang = st.sidebar.selectbox("Language / 语言", ["中文", "English"])
T = TEXT[lang]
st.title(T["title"])
st.caption(T["subtitle"])

with st.sidebar:
    st.header(T["config"])
    HANDLE = persistent_handle_input(T["handle"])
    show_official = st.checkbox(T["official_toggle"], value=True)
    show_unrated = st.checkbox(T["unrated_toggle"], value=True)
    run_clicked = st.button(T["run"], type="primary")
    clear_clicked = st.button(T["clear"], disabled=not HANDLE)


def _date(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def load_analysis(handle):
    """Load network-derived data once; keep it independent of UI VP exclusions."""
    status = st.empty()
    progress = st.progress(0)
    preview = st.empty()
    warnings = []
    blocking_issues = []

    status.info(T["loading_history"])
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
        warnings.append(T["time_fallback"].format(count=missing_start))

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
        status.info(T["loading_vp"].format(done=n, total=total))
        try:
            standings = get_json("contest.standings", {"contestId": cid})
            if not standings:
                raise CFAPIError("Empty standings")
            name = standings["contest"].get("name", f"Contest {cid}")
            for start, items in sessions:
                detail = reconstruct_vp_result(items, start, standings)
                if detail is None:
                    warning = T["vp_unsupported"].format(cid=cid)
                    warnings.append(warning)
                    blocking_issues.append(warning)
                    continue
                events.append({
                    "key": f"VP:{cid}:{start}",
                    "cid": cid, "ts": start, "type": "VP",
                    "rank": detail["rank"], "name": name,
                    "vp_details": detail,
                })
        except (CFAPIError, KeyError, TypeError, ValueError) as exc:
            warning = T["vp_failed"].format(cid=cid, error=exc)
            warnings.append(warning)
            blocking_issues.append(warning)
        progress.progress(14 + int(37 * n / max(total, 1)))

    events.sort(key=lambda event: (event["ts"], event["key"]))
    if events:
        with preview.container():
            st.caption(T["preview_title"].format(total=len(events)))
            st.dataframe(
                pd.DataFrame([
                    {
                        T["contest"]: row["name"],
                        T["date"]: _date(row["ts"]),
                        T["rank"]: row["rank"],
                        "VP": row["type"] == "VP",
                    }
                    for row in events[:10]
                ]),
                hide_index=True, width="stretch",
            )
    contest_ids = sorted({event["cid"] for event in events})
    changes_by_cid = {}
    for n, cid in enumerate(contest_ids, 1):
        status.info(T["loading_rating"].format(done=n, total=len(contest_ids)))
        try:
            changes_by_cid[cid] = get_json(
                "contest.ratingChanges", {"contestId": cid}
            )
            if not changes_by_cid[cid]:
                warnings.append(T["changes_missing"].format(cid=cid))
        except CFAPIError as exc:
            changes_by_cid[cid] = None
            warnings.append(str(exc))
        progress.progress(52 + int(48 * n / max(len(contest_ids), 1)))

    progress.empty()
    status.empty()
    preview.empty()
    return {
        "handle": handle,
        "events": events,
        "changes": changes_by_cid,
        "real_history": real_history,
        "warnings": warnings,
        "blocking_issues": blocking_issues,
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
            mode="lines", name=T["legend_real_only"],
            line=dict(color="#8894A7", dash="dash", width=2),
            hovertemplate="%{y} Rating<extra></extra>",
        ))
    if shown:
        fig.add_trace(go.Scatter(
            x=[h["date"] for h in shown], y=[h["rating"] for h in shown],
            mode="lines", name=T["legend_with_vp"],
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
            mode="lines+markers", name=T["legend_official"],
            line=dict(color="#4389e4", dash="dot", width=2),
            marker=dict(size=6),
        ))
    fig.update_layout(
        title=f"{T['chart_title']} ({HANDLE})",
        yaxis_title="Rating", xaxis_title=T["chart_axis"],
        legend=dict(orientation="h", y=1.12, x=0),
        height=540, hovermode="closest",
    )
    st.plotly_chart(lock_rating_chart(fig), width="stretch", config=PLOTLY_CONFIG)


if clear_clicked:
    clear_personal_cache(HANDLE.strip())
    st.session_state.pop("analysis_data", None)
    st.success(T["cache_cleared"])

if run_clicked:
    clean_handle = HANDLE.strip()
    if not clean_handle:
        st.warning(T["no_data"])
    else:
        try:
            with st.spinner(T["loading_analysis"]):
                st.session_state["analysis_data"] = load_analysis(clean_handle)
        except (CFAPIError, ValueError, KeyError) as exc:
            st.error(T["loading_error"].format(error=exc))

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
valid_keys = {event["key"] for event in vp_events}
hydrated = st.session_state.setdefault("unrated_storage_hydrated", set())
writes = st.session_state.setdefault("unrated_storage_writes", {})
browser_read = sync_unrated_storage(
    handle_key, write=writes.get(handle_key)
)
if handle_key not in hydrated:
    restored = parse_saved_value(browser_read, handle_key, valid_keys)
    if restored is not None:
        existing = restored
        override_store[handle_key] = restored
        hydrated.add(handle_key)
        st.session_state.setdefault("vp_editor_epochs", {})[handle_key] = (
            st.session_state.setdefault("vp_editor_epochs", {}).get(handle_key, 0) + 1
        )
event_by_key = {event["key"]: event for event in vp_events}
selected_keys = set(existing)
if vp_events:
    preview_exclusions = frozenset(existing)
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
            T["detail_delta"]: preview_by_key.get(event["key"], {}).get("model_delta"),
            T["solved"]: detail["solved"],
            "Link": f"https://codeforces.com/contest/{event['cid']}",
        })
    # The table is efficient on desktop; stacked cards avoid horizontal scroll
    # on narrow mobile screens. Both views modify the same per-session settings.
    card_view = st.toggle(T["mobile_mode"], value=False, key=f"vp_card_mode_{handle_key}")
    epochs = st.session_state.setdefault("vp_editor_epochs", {})
    previous_modes = st.session_state.setdefault("vp_previous_modes", {})
    if handle_key in previous_modes and previous_modes[handle_key] != card_view:
        epochs[handle_key] = epochs.get(handle_key, 0) + 1
    previous_modes[handle_key] = card_view
    epoch = epochs.get(handle_key, 0)
    if card_view:
        selected_keys = set()
        for event in vp_events:
            detail = event["vp_details"]
            estimate = preview_by_key.get(event["key"], {}).get("model_delta")
            with st.container(border=True):
                st.markdown(f"**{event['name']}**")
                st.caption(f"{_date(event['ts'])} · #{event['cid']}")
                st.write(
                    f"{T['rank']}: {event['rank']}　"
                    f"{T['solved']}: {detail['solved']}　"
                    f"{T['detail_delta']}: {estimate if estimate is not None else '—'}"
                )
                if st.checkbox(
                    T["excluded"], value=event["key"] in existing,
                    key=f"vp_card_{handle_key}_{epoch}_{event['key']}"
                ):
                    selected_keys.add(event["key"])
                st.link_button(T["card_link"], f"https://codeforces.com/contest/{event['cid']}")
    else:
        table = pd.DataFrame(editor_rows)
        edited = st.data_editor(
            table, width="stretch", hide_index=True, num_rows="fixed",
            column_config={
                "Session": None,
                T["excluded"]: st.column_config.CheckboxColumn(T["excluded"]),
                "Link": st.column_config.LinkColumn("Codeforces", display_text=T["card_link"]),
            },
            disabled=[T["contest"], T["date"], T["rank"], T["detail_delta"], T["solved"], "Link"],
            key=f"vp_editor_{handle_key}_{epoch}",
        )
        selected_keys = {
            row["Session"] for _, row in edited.iterrows()
            if bool(row[T["excluded"]])
        }
    if selected_keys != set(existing):
        override_store[handle_key] = selected_keys
        if handle_key in hydrated:
            version = st.session_state.setdefault("unrated_write_versions", {}).get(handle_key, 0) + 1
            st.session_state["unrated_write_versions"][handle_key] = version
            writes[handle_key] = {
                "handle": handle_key,
                "keys": sorted(selected_keys),
                "nonce": f"{handle_key}:{version}",
            }
            st.rerun()
    else:
        override_store[handle_key] = selected_keys
else:
    st.info(T["no_vps"])

# Only the explicit per-session checkboxes control Rated eligibility.
excluded_keys = frozenset(selected_keys)
with_vp, missing_with = simulate(raw["events"], raw["changes"], excluded_keys)
baseline, missing_real = simulate(
    raw["events"], raw["changes"], excluded_keys, include_vp=False
)
missing_keys = set(missing_with + missing_real)
incomplete = bool(missing_keys or raw.get("blocking_issues"))
if incomplete:
    st.error(T["incomplete"])
    if missing_keys:
        failed = [e for e in raw["events"] if e["key"] in missing_keys]
        st.caption(T["missing_rounds"].format(
            names=", ".join(f"{e['name']} (#{e['cid']})" for e in failed)
        ))
        if st.button(T["retry_failed"]):
            failures = []
            for cid in sorted({e["cid"] for e in failed}):
                try:
                    raw["changes"][cid] = get_json(
                        "contest.ratingChanges", {"contestId": cid}, force=True
                    )
                except CFAPIError as exc:
                    failures.append(str(exc))
            if failures:
                st.error("; ".join(failures))
            else:
                st.rerun()

last_rating = with_vp[-1]["rating"] if with_vp else 0
baseline_rating = baseline[-1]["rating"] if baseline else 0
official_rating = (
    raw["real_history"][-1]["rating"] if raw["real_history"] else 0
)
contribution = modeled_vp_contribution(with_vp, baseline) if not incomplete else None
a, b, c, d = st.columns(4)
a.metric(T["metric_pred"], "—" if incomplete else last_rating)
b.metric(T["metric_official"], official_rating)
c.metric(T["metric_contribution"], "—" if incomplete else f"{contribution:+d}")
d.metric(T["metric_error"], "—" if incomplete else f"{baseline_rating - official_rating:+d}")
st.caption(T["note"])
render_chart(
    with_vp, baseline, raw["real_history"],
    include_official=show_official, include_unrated=show_unrated,
)

st.subheader(T["details"])
if vp_events:
    choices = [e["key"] for e in vp_events]
    key = st.selectbox(
        T["detail_select"],
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
    fourth.metric(T["detail_delta"], "Unrated" if item and item.get("unrated")
                  else (f"{item['model_delta']:+d}" if item and not item.get("unavailable")
                        else T["detail_unavailable"]))
    if stats.get("penalty") is not None:
        st.caption(T["detail_penalty"].format(minutes=stats["penalty"]))
    with st.expander(T["detail_solved"], expanded=False):
        if stats["problems"]:
            st.dataframe(
                pd.DataFrame(stats["problems"]).rename(columns={
                    "problem": T["detail_problem"],
                    "minute": T["detail_minute"],
                    "wrong_attempts": T["detail_wa"],
                }),
                hide_index=True, width="stretch"
            )
        else:
            st.write(T["detail_empty"])
    st.markdown(f"**{T['detail_proxies']}**")
    if item and item["proxies"]:
        st.dataframe(
            pd.DataFrame(item["proxies"]).rename(columns={
                "Handle": T["proxy_handle"], "Profile": T["detail_profile"],
                "Pre-contest Rating": T["proxy_rating"], "Rank": T["proxy_rank"],
                "Official Delta": T["proxy_official"],
                "Rank adjustment": T["proxy_adjustment"],
                "Adjusted Delta": T["proxy_adjusted"],
                "Distance": T["proxy_distance"],
            }), hide_index=True, width="stretch",
            column_config={T["detail_profile"]: st.column_config.LinkColumn(
                T["detail_profile"], display_text=T["card_link"]
            )},
        )
        st.caption(T["detail_proxy_note"])
    else:
        st.info(T["detail_no_proxies"])
