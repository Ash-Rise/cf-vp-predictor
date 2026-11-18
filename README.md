# CF Rating Predictor

### 中文说明

这是一个基于 Streamlit 开发的 Codeforces 评分预测工具。它能够整合用户的实战历史与虚拟参赛（VP）记录，模拟出一条包含 VP 记录的潜在 Rating 走势曲线。

**核心功能**

* **存储架构优化**：重新设计了内存与硬盘的数据存储格式。通过精简 JSON 字段和采用紧凑型数据结构，显著缓解了处理大规模比赛数据时的系统资源压力。
* **智能并发查询**：引入了基于 ThreadPoolExecutor 的分批并发请求机制。在严格遵守 Codeforces API 频率限制的前提下，大幅提升了数据抓取的速度与稳定性。
* **时间轴可视化增强**：针对时间相近（如同日内进行多场比赛）的记录进行了坐标轴偏移优化。通过动态计算偏移量，确保密集的比赛数据点清晰可见，避免重叠。
* **Unrated 比赛管理**：对于无法自动确定 Rated 资格的 VP，可以手动输入多个比赛 ID 将其排除，并选择是否在图表中显示。
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
* **Unrated Contest Support**: Allows users to specify multiple Unrated VP contest IDs, since API data cannot universally determine historical eligibility. Includes a toggle to show or hide such events.
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

* **Initial Rating**: The chart always starts at **0**. The user cannot edit the initial Rating or toggle newcomer mode. Histories under the modern Codeforces newcomer policy start *internally* at 1400, while historical legacy simulations retain the previous internal starting approximation (100).
* **Data Caching**: Contest data is serialized and saved in the `data/` directory to enable near-instant loading during subsequent visits.
* **Clear Cache**: Use the "Clear Cache" button in the sidebar to refresh outdated data or reset storage.


### Fork-specific improvements / 本 Fork 新增功能

- **Remember CF Handle / 记住 Handle**: The Handle is stored in your current browser's `localStorage` and prefilled on later visits to the same app origin (no login or database). Clearing browser site data removes it. 当前浏览器再次访问同一网站会自动填入上次的 Handle。
- **Automatic newcomer handling / 自动新账号规则**: There is no checkbox. The first eligible rated contest on the merged REAL+VP timeline determines whether the modern (post-May-2020) newcomer policy is applicable (a conservative June 1, 2020 cutoff is used; transition-period accuracy is not guaranteed). The graph begins at 0. For modern newcomers, the calculation starts internally at 1400, with displayed bonuses 500, 350, 250, 150, 100, 50 over the first six **counted** rated events. Manually excluded VP events do not use a bonus. 不需要勾选，新人规则按比赛时间与实际计分场次自动应用，曲线起点显示 0。
- **Unrated VP override / Unrated 手动指定**: **Multiple contest IDs are supported**: enter e.g. `1084, 1200, 1350` (English or Chinese commas) to assign Delta 0 to every VP session for those contests. The app cannot infer all historical eligibility rules from the public API. **Unlisted VPs are estimates, not guaranteed rated.** 支持一次输入多场比赛 ID，用中英文逗号分隔；指定比赛的全部 VP 都不计分。
- **Regression tests / 简单测试**: `python -m unittest discover -v -p 'test_*.py'`. These are offline tests, not live API or end-to-end browser tests.

The five-nearest-proxy Rating estimator remains unchanged. Its results, and VP eligibility in unlisted contests, are still approximate.
