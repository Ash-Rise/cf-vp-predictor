# Codeforces VP Rating Simulator

[Live app](https://ashrise-cf-vp-predictor.streamlit.app/) · [Source](https://github.com/Ash-Rise/cf-vp-predictor) · [Codeforces API](https://codeforces.com/apiHelp)

A Streamlit tool that reconstructs **Codeforces Virtual Participation (VP)** results from submission history and estimates a hypothetical Rating timeline alongside officially rated contests.

> **Not an official Rating calculator.** It compares historical virtual scores with real participants and uses a five-nearest-proxy heuristic. Some contest rules and Rated eligibility conditions cannot be verified from public API data. All Rating and VP-effect numbers are estimates.

## 中文说明

### 主要功能

- **自动读取比赛历史**：通过 Handle 获取正式 Rated 比赛和可识别的 VP，按比赛实际开始时间合并排序，而不是依照官方 Rating 的更新时刻。
- **可交互的 VP 管理**：表格按每次 VP 会话展示比赛、时间、估计排名、AC、得分和 Codeforces 链接；逐行勾选 `Unrated` 即可重新计算，不必重新下载历史数据。同一场比赛的多次 VP 可以分别管理。
- **批量 Unrated**：输入多个 Contest ID，如 `1084, 1200, 1350`（中英文逗号均支持），对应比赛的全部 VP Delta 归零，且不会占用新人前六场名额。未手动排除的 VP 不保证一定具备 Rated 资格。
- **单场预测详情**：查看 VP 得分、AC、罚时（如适用）、解出的题目，以及估算 Delta 使用的五名真实参考选手及其历史 Rating、排名、Delta 和距离权重。
- **两条模拟曲线**：同时模拟「含 VP」和「不含 VP（仅正式比赛）」。两者的末尾 Rating 之差称为**VP 模拟贡献**。另外展示官方 Rating 及「只模拟正式比赛」相对官方值的误差，避免把模型自身误差全部归因于 VP。
- **新账号规则自动应用**：对于适用 2020 年后新人规则的历史，内部从 1400 开始估算，显示曲线从 0 开始；前六场有效 Rated 比赛依次应用 500、350、250、150、100、50 的显示分补偿。界面不需要 New Account 勾选。对于旧比赛使用近似兼容策略，过渡期的精确性没有保证。
- **浏览器记住 Handle**：利用本机浏览器 `localStorage` 自动填入最近使用的 Handle，无需注册或登录。

### 预测原理与局限

1. `user.rating` 读取真实 Rated 比赛；`user.status` 读取或增量更新提交记录。
2. 依照 VP 的 `author.startTimeSeconds` 分组，通过 `contest.standings` 重建成绩并估计同场排名。不同比赛的 CF / ICPC 规则尽可能分别处理；IOI 等不支持的计分不会伪装成 CF。
3. 对每个可能计分的比赛，读取 `contest.ratingChanges`，以「赛前 Rating 差 × 0.8 + 排名差 × 1.5」挑选最多五名参考选手，并对其实际 Delta 计算截尾均值。
4. 依序模拟两条路径。**VP 模拟贡献 = 含 VP 的模型最终 Rating − 仅正式比赛的模型最终 Rating**，不是 VP 的官方真实收益。
5. 如果缺少比赛开始时间或 Rating 变化数据，页面明确显示警告。Hack、特殊计分规则、无 Rated 资格的 VP、完整历史新人政策等仍可能影响准确性。

### 缓存和限流

所有 Codeforces API 请求由进程内统一调度器控制，按官方 **不超过每两秒一次**的节奏请求。正式比赛榜单、Rating 变化和比赛目录复用服务器缓存；个人提交首次获取完整历史，之后通过 `user.status?from=...&count=...` 增量读取新提交并刷新最新的判题结果。

缓存存放在 `data/cf_api_v2/`，只是**临时服务器缓存**，Streamlit Community Cloud 重启或重新部署后不保证持久存在。切换 Unrated 设置不会重新下载比赛数据。浏览器保存的 Handle 与服务器 API 缓存彼此独立。

## English

**Features:** chronological official+VP reconstruction; session-level Unrated checkboxes and comma-separated bulk exclusions; inspectable per-contest score and five-proxy Delta explanation; official vs. simulated Rating lines; a more meaningful VP contribution computed by subtracting two **simulated** scenarios; browser-persistent Handle; shared contest caches, incremental submission refresh and strict API pacing.

**Important limitations:** This is a counterfactual approximation, not a reimplementation of Codeforces' complete Rating engine. Historical newcomer rules, contests with hacks or unusual scoring, missing ratings, and VP Rated eligibility can produce errors. Unrated rows only represent explicit user exclusions.

## Local development

Python 3.11+ is recommended.

```bash
git clone https://github.com/Ash-Rise/cf-vp-predictor.git
cd cf-vp-predictor
python -m pip install -r requirements.txt
streamlit run app.py
```

To run the small offline regression and startup checks:

```bash
python -m unittest discover -v -p "test_*.py"
```

GitHub Actions installs the app's actual dependencies, compiles the modules, runs pure-function tests, and renders the initial Streamlit page through AppTest. These checks do **not** replace browser-based or real Codeforces API smoke tests.

## Source files

| Path | Responsibility |
|---|---|
| `app.py` | Streamlit UI, VP editor, detail inspector and plotting |
| `cf_api.py` | API client, request pacing, shared and incremental caches |
| `vp_utils.py` | VP session grouping and score/rank reconstruction |
| `predictor_core.py` | Five-proxy estimation, two counterfactual paths and evidence |
| `rating_rules.py` | New-account display behavior and manual Unrated ID parsing |
| `persistent_handle.py` | Browser-local Handle persistence |

This fork is based on [vividStareium/cf-vp-predictor](https://github.com/vividStareium/cf-vp-predictor). Its five-proxy Rating estimator remains deliberately close to the original pending proper historical backtesting.
