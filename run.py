# run.py
import argparse
import asyncio
import os
import sys
import yaml
from datetime import datetime
from typing import Optional

# try import crawler.run_crawler and parser.parse_edges_to_excel
try:
    from crawler import run_crawler
except Exception as e:
    run_crawler = None
    _crawler_import_error = e

try:
    from parser import parse_edges_to_excel
except Exception as e:
    parse_edges_to_excel = None
    _parser_import_error = e

def load_config(path: str = "config.yaml") -> dict:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}

def parse_args():
    p = argparse.ArgumentParser(description="Kickstarter 评论爬虫（支持可选解析）")
    p.add_argument("--comments_page", type=str, default="config.yaml", help="配置文件路径（yaml）")
    p.add_argument("--url", type=str, help="覆盖配置：评论页面 URL")
    p.add_argument("--output_json", type=str, help="覆盖配置：输出 JSON 文件名（可不带 .json）")
    p.add_argument("--output_excel", type=str, help="覆盖配置：输出 Excel 文件名（.xlsx）")
    p.add_argument("--max_clicks", type=int, help="覆盖配置：最大点击次数")
    p.add_argument("--click_timeout_ms", type=int, help="覆盖配置：点击等待超时 毫秒")
    p.add_argument("--initial_wait_ms", type=int, help="覆盖配置：初始等待 毫秒")
    p.add_argument("--headless", type=str, choices=["true","false"], help="覆盖配置：headless（true/false）")
    p.add_argument("--window_width", type=int, help="覆盖配置：浏览器宽度")
    p.add_argument("--window_height", type=int, help="覆盖配置：浏览器高度")
    p.add_argument("--no-parse", action="store_true", help="只爬取 JSON，不解析导出 Excel")
    p.add_argument("--parse-only", action="store_true", help="只解析已有 JSON（跳过爬取）")
    p.add_argument("--input_json", type=str, help="parse-only 模式或解析指定输入 JSON 文件")
    p.add_argument("--no-timestamp", action="store_true", help="不要在输出文件名上加时间戳")
    return p.parse_args()

def str_to_bool(s: Optional[str], default: bool) -> bool:
    if s is None:
        return default
    return s.lower() == "true"

def make_output_names(base_json: str, add_ts: bool = True) -> (str, str): # type: ignore
    """返回 (json_file, excel_file)"""
    if add_ts:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        if base_json.endswith(".json"):
            json_file = base_json.replace(".json", f"_{ts}.json")
        else:
            json_file = f"{base_json}_{ts}.json"
    else:
        json_file = base_json if base_json.endswith(".json") else f"{base_json}.json"

    excel_file = json_file.replace(".json", ".xlsx")
    return json_file, excel_file

def ensure_crawler_available():
    if run_crawler is None:
        print("错误：无法导入 crawler.run_crawler。请确保 crawler.py 在项目根目录，且包含 run_crawler 函数。")
        print("导入错误详情：", repr(_crawler_import_error))
        sys.exit(1)

def ensure_parser_available():
    if parse_edges_to_excel is None:
        print("错误：无法导入 parser.parse_edges_to_excel。请确保 parser.py 在项目根目录，且包含 parse_edges_to_excel 函数。")
        print("导入错误详情：", repr(_parser_import_error))
        sys.exit(1)

if __name__ == "__main__":
    args = parse_args()
    cfg = load_config(args.config)

    # 合并配置 （CLI 优先 -> config.yaml -> 内置默认）
    url = args.url or cfg.get("comments_page") or cfg.get("url") or "https://www.kickstarter.com"
    raw_output_json_cfg = args.output_json or cfg.get("output_json") or "kickstarter_comments.json"
    append_ts = not args.no_timestamp and cfg.get("append_timestamp", True)

    # 输出文件名处理（带或不带时间戳）
    json_file, excel_file_default = make_output_names(raw_output_json_cfg, add_ts=append_ts)

    output_excel = args.output_excel or cfg.get("output_excel") or excel_file_default

    max_clicks = args.max_clicks if args.max_clicks is not None else cfg.get("max_clicks", 30)
    click_timeout_ms = args.click_timeout_ms if args.click_timeout_ms is not None else cfg.get("click_timeout_ms", 15000)
    initial_wait_ms = args.initial_wait_ms if args.initial_wait_ms is not None else cfg.get("initial_wait_ms", 6000)
    headless = str_to_bool(args.headless, cfg.get("headless", True))
    window_width = args.window_width if args.window_width is not None else cfg.get("window_width", 1400)
    window_height = args.window_height if args.window_height is not None else cfg.get("window_height", 900)

    scroll_min = cfg.get("scroll_min", 50)
    scroll_max = cfg.get("scroll_max", 150)
    scroll_sleep_min = cfg.get("scroll_sleep_min", 0.1)
    scroll_sleep_max = cfg.get("scroll_sleep_max", 0.4)

    print("=== 生效配置 ===")
    print(f"url: {url}")
    print(f"output json: {json_file}")
    print(f"output excel: {output_excel}")
    print(f"max_clicks: {max_clicks}")
    print(f"click_timeout_ms: {click_timeout_ms}")
    print(f"initial_wait_ms: {initial_wait_ms}")
    print(f"headless: {headless}")
    print("=================")

    # parse-only 模式：只做解析
    if args.parse_only:
        input_json = args.input_json or cfg.get("input_json") or cfg.get("output_json") or json_file
        if not os.path.exists(input_json):
            print(f"[错误] 指定的输入 JSON 文件不存在：{input_json}")
            sys.exit(1)
        ensure_parser_available()
        print(f"解析（parse-only）: {input_json} -> {output_excel}")
        parse_edges_to_excel(input_json, output_excel)
        print("解析完成。")
        sys.exit(0)

    # 正常流程：先爬取（除非用户指定只解析）
    ensure_crawler_available()
    asyncio.run(
        run_crawler(
            url=url,
            output_file=json_file,
            max_clicks=max_clicks,
            click_timeout_ms=click_timeout_ms,
            initial_wait_ms=initial_wait_ms,
            headless=headless,
            window_width=window_width,
            window_height=window_height,
            scroll_min=scroll_min,
            scroll_max=scroll_max,
            scroll_sleep_min=scroll_sleep_min,
            scroll_sleep_max=scroll_sleep_max,
        )
    )
    print(f"爬取完成，JSON 保存到: {json_file}")

    # 如用户要求只爬不解析，则退出
    if args.no_parse:
        print("[提示] 已选择 --no-parse（只爬取不解析）。")
        sys.exit(0)

    # 否则调用 parser
    ensure_parser_available()
    print(f"开始解析: {json_file} -> {output_excel}")
    parse_edges_to_excel(json_file, output_excel)
    print("全部完成。")
