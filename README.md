# Codeforces VP Rating Simulator

**简体中文** · [English](README_EN.md)

[在线体验](https://ashrise-cf-vp-predictor.streamlit.app/) · [GitHub 仓库](https://github.com/Ash-Rise/cf-vp-predictor) · [Codeforces API](https://codeforces.com/apiHelp)

一个基于 **Streamlit** 的 Codeforces Rating 模拟工具：读取用户的正式比赛记录和虚拟参赛（VP）提交，重建 VP 成绩，并估算将这些 VP 计入 Rated 历史之后的 Rating 走势。

> [!IMPORTANT]
> **本项目不是 Codeforces 官方 Rating 计算器。** VP 排名和 Rating 变化均为估算结果；历史比赛的特殊规则、Hack、Rated 资格及 API 数据缺失都可能导致偏差。

## 功能

- **自动整理历史比赛**：读取 `user.rating` 与 `user.status`，优先按正式比赛和 VP 各自的**开始时间**排序，而非使用较晚的 Rating 更新时间。
- **可交互的 VP 管理**：表格按每次 VP 会话展示比赛、日期、估计排名、预估内部 Delta、AC 数及 Codeforces 链接。勾选某行的 `Unrated` 即可重新计算，无需重新下载数据。同一比赛的多次 VP 可以单独管理。
- **单场预测详情**：查看 VP 的估计排名、得分、解出题目、ICPC 罚时（如适用），以及预测 Delta 使用的最多五名真实参考选手：Handle、主页、赛前 Rating、排名、实际 Delta 与调整后 Delta。
- **对比两种模拟路径**：同时绘制“仅正式比赛”和“正式比赛 + VP”的模拟曲线，并可叠加官方实际 Rating。两种模拟最终值之差显示为 **VP 模拟贡献**；另外显示模型相对于官方 Rating 的偏差，避免将估算误差误称为 VP 收益。
- **自动应用新人显示规则**：适用新版规则的账号使用内部起始 Rating 1400、初始显示分 0；前六场有效 Rated 比赛依次使用 500、350、250、150、100、50 的显示分补偿。无需手动勾选新账号选项。旧账号与规则过渡期采用近似处理。
- **记住 Handle**：最近使用的 Handle 会保存在当前浏览器的 `localStorage`，再次访问同一网址可自动填入。

**注意：** 所有 VP 的 Unrated 状态统一通过管理表格逐次设置；每次勾选后会本地重新模拟，不需要输入 Contest ID。勾选保存在当前 Streamlit 会话中，尚未跨会话持久化。未排除的 VP 不代表一定符合官方 Rated 资格。

## 预测方法

1. 从 `user.rating` 取得正式 Rated 比赛历史；从 `user.status` 识别 VP 提交。
2. 优先使用 `author.startTimeSeconds` 区分同一比赛的不同 VP，会话内按比赛时长过滤有效提交，并利用 `contest.standings` 估计名次。主要支持 CF 和 ICPC 计分；未支持的模式不会冒充 CF 计分。
3. 通过 `contest.ratingChanges` 获取同场真实选手的赛前 Rating、名次和实际 Delta，使用近邻成本
   `cost = 0.8 × |R_i − R| + 1.5 × |rank_i − rank|`
   选取最多五名参考选手；当至少有三名参考选手时，去掉调整后 Delta 的最大、最小值，再对其余值取均值。
4. 按比赛开始时间顺序模拟两条 Rating 路径。**VP 模拟贡献 = 含 VP 模拟末尾 Rating − 仅正式比赛模拟末尾 Rating**。它是两种模型情景的差值，**不是** Codeforces 官方会授予的分数。
5. 如果比赛开始时间、榜单或 Rating 变化记录不可用，页面会提供警告。部分缺失数据可能使结果不完整。

当前保留原项目的五邻居 Delta 近似算法，未宣称已经精确复现 Codeforces 官方 Rating 计算。不同历史时期、特殊赛制及新人机制仍可能有系统性误差。

## 缓存与请求频率

- 所有 Codeforces API 请求经过**进程内统一节流器**，设置至少约 2.1 秒的请求起始间隔，并带有限次重试。
- 比赛目录、榜单和 `contest.ratingChanges` 使用服务端共享缓存，降低不同用户查询同一比赛时的重复请求。
- 个人提交首次读取全部历史；后续使用 `user.status` 分页增量获取，并覆盖更新最近的判题状态。个人数据缓存有短期有效期。
- 调整 Unrated 勾选时仅重新执行本地模拟，不会为每次勾选重新下载 API 数据。
- 本地缓存位于 `data/cf_api_v2/`。**Streamlit Community Cloud 上的本地磁盘不能保证永久持久化**；服务重启或重新部署可能需要重新获取。
- 浏览器记住 Handle 与服务器缓存是两个独立机制。

## 本地运行

建议 Python 3.11 或更新版本。

```bash
git clone https://github.com/Ash-Rise/cf-vp-predictor.git
cd cf-vp-predictor
python -m pip install -r requirements.txt
streamlit run app.py
```

运行小范围离线测试及 Streamlit 启动冒烟测试：

```bash
python -m unittest discover -v -p "test_*.py"
```

GitHub Actions 会安装真实运行依赖、检查 Python 模块导入并运行测试。**目前尚不能替代真实浏览器交互及实际 Codeforces API 的端到端验证**。

## 项目结构

| 文件 | 作用 |
|---|---|
| `app.py` | Streamlit 页面、VP 编辑表格、单场详情与图表 |
| `cf_api.py` | Codeforces API、请求节流、共享缓存及个人提交增量更新 |
| `vp_utils.py` | VP 会话划分、得分与排名重建 |
| `predictor_core.py` | 五邻居 Delta 估算、双路径模拟与预测详情 |
| `rating_rules.py` | 新人显示分规则 |
| `persistent_handle.py` | 浏览器本地 Handle 保存 |

## 致谢与来源

本项目 Fork 自 [vividStareium/cf-vp-predictor](https://github.com/vividStareium/cf-vp-predictor)。保留其基于同场参考选手估算 Rating Delta 的核心思路，在此基础上改进了数据处理、交互管理和预测结果解释。

---

[Read this documentation in English](README_EN.md)
