# Kickstarter Scraper

© 2025 Ben Xie  
作者：Ben Xie

## 项目简介
本项目用于 **自动化抓取 Kickstarter 项目的评论和回复**，支持异步爬虫，高效抓取大量数据，同时提供 **灵活的参数配置**，方便自定义抓取行为。

主要功能：
- 自动抓取项目评论及回复
- 异步爬取，提高抓取效率
- 支持自定义抓取参数（点击次数、等待时间、滚动范围等）
- 输出 JSON 和 Excel 两种格式，方便后续分析

适用场景：
- 自动化数据收集和分析
- 团队内部使用或开源共享  

---

## 安装与运行

### 1. 克隆仓库
```bash
git clone https://github.com/BenShieh233/kickstarter-scraper.git
cd kickstarter-scraper
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置参数
项目支持两种方式配置参数：

方式A: 通过 config.yaml 修改
1. 打开 config.yaml 文件
2. 根据需求修改配置项，例如：
```yaml
comments_page: "https://www.kickstarter.com/projects/libernovo/libernovo-omni-worlds-first-dynamic-ergonomic-chair/comments"
output_json: "kickstarter_comments.json"   # 输出 JSON 文件
output_excel: "kickstarter_comments.xlsx"  # 输出 Excel 文件
max_clicks: 30                              # 最大点击“加载更多”次数
click_timeout_ms: 15000                      # 点击超时时间（毫秒）
initial_wait_ms: 6000                        # 初始等待时间（毫秒）
headless: true                               # 是否无头模式运行
window_width: 1400                           # 浏览器窗口宽度
window_height: 900                           # 浏览器窗口高度
user_agent: null                             # 自定义 User-Agent，可为空
scroll_min: 50                               # 滚动最小步长
scroll_max: 150                              # 滚动最大步长
scroll_sleep_min: 0.1                        # 滚动最小间隔（秒）
scroll_sleep_max: 0.4                        # 滚动最大间隔（秒）

```
方式B: 直接在命令行导入参数
```bash
python run.py \
  --comments_page https://www.kickstarter.com/projects/libernovo/libernovo-omni-worlds-first-dynamic-ergonomic-chair/comments \
  --output_json custom_output.json \
  --output_excel custom_output.xlsx \
  --max_clicks 5

```
·命令行参数会覆盖 config.yaml 中对应的配置
·支持灵活调用不同配置，无需修改文件

### 4. 启动项目
使用默认配置：
```bash
python run.py
```

使用命令行参数覆盖配置：
#### 常用命令行参数（CLI Arguments）

- `--url`：Kickstarter 评论页面的 URL。
- `--output_json`：输出的 JSON 文件名。
- `--output_excel`：输出的 Excel 文件名。
- `--max_clicks`：点击“加载更多评论”的最大次数。
- `--headless true/false`：是否以无头模式运行浏览器。
- `--no-parse`：只爬取数据，不解析生成 Excel。
- `--parse-only`：只解析已有 JSON 文件生成 Excel。
- `--input_json`：要解析的 JSON 文件（与 `--parse-only` 一起使用）。


许可证

本项目开源，采用 MIT 许可证。
你可以自由使用、修改和分发本项目代码，但 必须保留原作者 (Ben Xie) 的署名。

详情请参阅 LICENSE 文件。

---

# Kickstarter Scraper

A Python tool for scraping Kickstarter project comments and exporting them to JSON/Excel.

## Features

- Scrape comments from a Kickstarter project page.
- Save results as JSON.
- Parse and export JSON to Excel (.xlsx).
- Configurable via `config.yaml` or CLI arguments.
- Supports headless browser operation and customizable scraping behavior.

## Quick Start

### 1. Install Requirements

Make sure you have Python 3.7+ installed.

Install required Python packages:
```sh
pip install -r requirements.txt
```
Or, at minimum:
```sh
pip install pyyaml
```
Other dependencies may be needed (e.g., Selenium, pandas) – see `requirements.txt` or project files.

### 2. Prepare Files

Ensure the following files are present in the project root:
- `run.py`
- `crawler.py` (with `run_crawler` function)
- `parser.py` (with `parse_edges_to_excel` function)
- (Optional) `config.yaml`

### 3. Configuration

You can provide configuration in a `config.yaml` file or via CLI arguments.

Example `config.yaml`:
```yaml
comments_page: "https://www.kickstarter.com/projects/xxxxx/comments"
output_json: "kickstarter_comments.json"
output_excel: "kickstarter_comments.xlsx"
max_clicks: 30
headless: true
append_timestamp: true
# ... more options available, see run.py
```

### 4. Usage

Run the scraper with default settings:
```sh
python run.py
```

#### Common CLI Arguments

- `--url`: Kickstarter comments page URL.
- `--output_json`: Output JSON filename.
- `--output_excel`: Output Excel filename.
- `--max_clicks`: Max clicks for "Load more" comments.
- `--headless true/false`: Run browser headless or not.
- `--no-parse`: Only crawl, don't parse to Excel.
- `--parse-only`: Only parse existing JSON to Excel.
- `--input_json`: JSON file to parse (used with `--parse-only`).

#### Examples

**Crawl and parse (default):**
```sh
python run.py --url "https://www.kickstarter.com/projects/xxxxx/comments"
```

**Only crawl, don't parse:**
```sh
python run.py --no-parse
```

**Only parse an existing JSON file:**
```sh
python run.py --parse-only --input_json "kickstarter_comments_20250814_235106.json"
```

**Specify output Excel file:**
```sh
python run.py --output_excel "my_comments.xlsx"
```

### 5. Output

- JSON file: Scraped comments.
- Excel file: Parsed comments in tabular format.

### 6. Troubleshooting

- If you see errors about missing modules or functions (`run_crawler`, `parse_edges_to_excel`), ensure `crawler.py` and `parser.py` exist and have the required functions.
- The script prints effective configuration at runtime for verification.

### 7. License

MIT License

---

## Project Structure

```
run.py
crawler.py
parser.py
config.yaml (optional)
requirements.txt
README.md
```

## Contributing

Feel free to open issues or pull requests!

