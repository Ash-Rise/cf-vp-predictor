# CF Rating Predictor

### 中文说明

这是一个基于 Streamlit 开发的 Codeforces 评分预测工具。它能够整合用户的实战历史与虚拟参赛（VP）记录，模拟出一条包含 VP 记录的潜在 Rating 走势曲线。

**核心功能**

* **存储架构优化**：重新设计了内存与硬盘的数据存储格式。通过精简 JSON 字段和采用紧凑型数据结构，显著缓解了处理大规模比赛数据时的系统资源压力。
* **智能并发查询**：引入了基于 ThreadPoolExecutor 的分批并发请求机制。在严格遵守 Codeforces API 频率限制的前提下，大幅提升了数据抓取的速度与稳定性。
* **时间轴可视化增强**：针对时间相近（如同日内进行多场比赛）的记录进行了坐标轴偏移优化。通过动态计算偏移量，确保密集的比赛数据点清晰可见，避免重叠。
* **Unrated 比赛管理**：系统能自动识别由于分站限制或其他规则导致的 Unrated 比赛。侧边栏设有开关，允许用户自主选择是否在图表中显示这些非计分场次。
* **科学模拟算法**：根据用户当时的 Rating，在同场比赛中匹配表现相近的真实选手作为代理，通过加权算法计算出最符合实际情况的 Delta 增量。

**在线体验**

您可以通过以下链接直接在线使用：
[https://cf-vp-predictor-7pgzwzseurssuzy5uqktit.streamlit.app/#codeforces-rating-simulator]

---

### English Description

A Codeforces rating prediction tool built with Streamlit. It integrates official contest history with Virtual Participation (VP) records to simulate a potential rating trajectory as if VPs were official contests.

**Key Features**

* **Storage Architecture Optimization**: Refactored data storage formats for both memory and disk. By streamlining JSON fields and utilizing compact data structures, it significantly reduces system resource pressure when handling large-scale contest datasets.
* **Smart Concurrency**: Implemented a batched concurrency mechanism using ThreadPoolExecutor. This maximizes data fetching speed and stability while strictly adhering to Codeforces API rate limits.
* **Visualization Enhancement**: Optimized axis offsets for matches occurring close in time (such as multiple contests on the same day). By dynamically calculating offsets, it ensures that dense data points remain clear and readable without overlapping.
* **Unrated Contest Support**: Automatically identifies Unrated contests based on rating caps or specific rules. Includes a toggle in the sidebar to show or hide non-rated events in the chart.
* **Simulation Algorithm**: Finds proxy participants in the same contest with similar historical ratings to calculate the most realistic rating Delta using weighted algorithms.

**Live Demo**

You can access the tool online at:
[https://cf-vp-predictor-7pgzwzseurssuzy5uqktit.streamlit.app/#codeforces-rating-simulator]

---

### Installation and Usage

1. **Clone the repository**:
`git clone https://github.com/vividStareium/cf-vp-predictor.git`
`cd cf-vp-predictor`
2. **Install dependencies**:
`pip install streamlit requests plotly`
3. **Run the application**:
`streamlit run app.py`

**Usage Notes**

* **Initial Rating**: The starting Rating is fixed to 100 in regular mode; there is no editable input. New-account mode instead starts from Codeforces' internal 1400 baseline (initial displayed rating 0).
* **Data Caching**: Contest data is serialized and saved in the `data/` directory to enable near-instant loading during subsequent visits.
* **Clear Cache**: Use the "Clear Cache" button in the sidebar to refresh outdated data or reset storage.


### Fork-specific improvements / 本 Fork 新增功能

- **Remember CF Handle / 记住 Handle**: The Handle is stored in your current browser's `localStorage` and prefilled on later visits to the same app origin (no login or database). Clearing browser site data removes it. 当前浏览器再次访问同一网站会自动填入上次的 Handle。
- **New account mode / 新账号模式**: Enable this *only when simulating a new account from its first rated contest* (2020+ rules). Internal starting rating is 1400, displayed initial rating is 0, and the first six rated contests add visible bonuses of 500, 350, 250, 150, 100, and 50 on top of estimated internal Delta. **Do not enable it to start from an established account's current Rating.** 只在从新账号第一场比赛开始完整模拟时开启。
- **Unrated VP override / Unrated 手动指定**: Codeforces' API does not provide a universal historical rating-eligibility cutoff. The old `max(oldRating)` cutoff guess was removed because it incorrectly marked actual rated rounds as unrated. If a VP contest should not count, enter its contest ID in the sidebar (multiple IDs separated by commas); all VP sessions in that contest will have Delta 0. **Unlisted VPs are estimates, not guaranteed rated.** 无法自动可靠判定的比赛请按实际资格手动排除。
- **Regression tests / 简单测试**: `python -m unittest discover -v -p 'test_*.py'`. These are offline tests, not live API or end-to-end browser tests.

The five-nearest-proxy Rating estimator remains unchanged. Its results, and VP eligibility in unlisted contests, are still approximate.
