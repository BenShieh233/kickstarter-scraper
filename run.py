# run.py
import argparse
import asyncio
import os
import sys
import yaml
from datetime import datetime
from typing import Optional, Tuple, Dict, Any

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


def load_config(path: str = "config.yaml") -> Dict[str, Any]:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Kickstarter 评论爬虫（支持 config.yaml 与命令行覆盖）")
    # config 文件（仅用于指定配置文件路径）
    p.add_argument("--config", type=str, default="config.yaml", help="配置文件路径（yaml），默认为 ./config.yaml")

    # URL（覆盖 config.yaml 中的 comments_page）
    p.add_argument("--comments_page", "--url", dest="comments_page", type=str,
                   help="覆盖配置中的 comments_page（即要爬取的评论页面 URL）")

    # run_crawler 需要的参数（命令行覆盖）
    p.add_argument("--output_json", type=str, help="覆盖配置：输出 JSON 文件名（可不带 .json）")
    p.add_argument("--output_excel", type=str, help="覆盖配置：输出 Excel 文件名（.xlsx）")  # <-- 新增
    p.add_argument("--max_clicks", type=int, help="覆盖配置：最大点击次数")
    p.add_argument("--click_timeout_ms", type=int, help="覆盖配置：点击等待超时 毫秒")
    p.add_argument("--initial_wait_ms", type=int, help="覆盖配置：初始等待 毫秒")
    p.add_argument("--headless", type=str, choices=["true", "false"], help="覆盖配置：headless（true/false）")
    p.add_argument("--window_width", type=int, help="覆盖配置：浏览器宽度")
    p.add_argument("--window_height", type=int, help="覆盖配置：浏览器高度")

    # 滚动相关
    p.add_argument("--scroll_min", type=int, help="滚动最小像素/步数")
    p.add_argument("--scroll_max", type=int, help="滚动最大像素/步数")
    p.add_argument("--scroll_sleep_min", type=float, help="滚动间隔最小秒数")
    p.add_argument("--scroll_sleep_max", type=float, help="滚动间隔最大秒数")

    # 解析控制
    p.add_argument("--no-parse", action="store_true", help="只爬取 JSON，不解析导出 Excel")
    p.add_argument("--parse-only", action="store_true", help="只解析已有 JSON（跳过爬取）")
    p.add_argument("--input_json", type=str, help="parse-only 模式或解析指定输入 JSON 文件")
    p.add_argument("--no-timestamp", action="store_true", help="不要在输出文件名上加时间戳")

    return p.parse_args()


def str_to_bool(s: Optional[str], default: bool) -> bool:
    if s is None:
        return default
    return s.lower() == "true"


def make_output_names(base_json: str, add_ts: bool = True) -> Tuple[str, str]:
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


def build_effective_config(args: argparse.Namespace, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    优先级：命令行 > config.yaml > 内置默认
    仅保留 run_crawler 所需字段 + 输出/解析 控制
    """
    defaults = {
        "comments_page": "https://www.kickstarter.com",
        "output_json": "kickstarter_comments.json",
        "output_excel": "kickstarter_comments.xlsx",
        "max_clicks": 30,
        "click_timeout_ms": 15000,
        "initial_wait_ms": 6000,
        "headless": True,
        "window_width": 1400,
        "window_height": 900,
        "scroll_min": 50,
        "scroll_max": 150,
        "scroll_sleep_min": 0.1,
        "scroll_sleep_max": 0.4,
        "append_timestamp": True,
    }

    eff = {**defaults, **(cfg or {})}

    # URL 覆盖
    if getattr(args, "comments_page", None):
        eff["comments_page"] = args.comments_page
    else:
        eff["comments_page"] = eff.get("comments_page") or eff.get("url") or defaults["comments_page"]

    # 文件名覆盖（包括 output_excel）
    if getattr(args, "output_json", None):
        eff["output_json"] = args.output_json
    if getattr(args, "output_excel", None):
        eff["output_excel"] = args.output_excel

    # numeric overrides
    if getattr(args, "max_clicks", None) is not None:
        eff["max_clicks"] = args.max_clicks
    if getattr(args, "click_timeout_ms", None) is not None:
        eff["click_timeout_ms"] = args.click_timeout_ms
    if getattr(args, "initial_wait_ms", None) is not None:
        eff["initial_wait_ms"] = args.initial_wait_ms
    if getattr(args, "window_width", None) is not None:
        eff["window_width"] = args.window_width
    if getattr(args, "window_height", None) is not None:
        eff["window_height"] = args.window_height

    # headless：命令行用 "true"/"false" 字符串覆盖
    eff["headless"] = str_to_bool(getattr(args, "headless", None), bool(eff.get("headless", True)))

    # scroll overrides
    if getattr(args, "scroll_min", None) is not None:
        eff["scroll_min"] = args.scroll_min
    if getattr(args, "scroll_max", None) is not None:
        eff["scroll_max"] = args.scroll_max
    if getattr(args, "scroll_sleep_min", None) is not None:
        eff["scroll_sleep_min"] = args.scroll_sleep_min
    if getattr(args, "scroll_sleep_max", None) is not None:
        eff["scroll_sleep_max"] = args.scroll_sleep_max

    # timestamp flag
    eff["append_timestamp"] = (not args.no_timestamp) and bool(eff.get("append_timestamp", True))

    return eff


if __name__ == "__main__":
    args = parse_args()
    cfg = load_config(args.config)

    eff = build_effective_config(args, cfg)

    json_file, excel_file_default = make_output_names(eff["output_json"], add_ts=eff["append_timestamp"])
    # 优先级：命令行 --output_excel > config.yaml output_excel > 根据 json 生成的默认 excel 文件名
    output_excel = args.output_excel or eff.get("output_excel") or excel_file_default

    # visibility
    print("=== 生效配置 ===")
    print(f"config file: {args.config}")
    print(f"comments_page(url): {eff['comments_page']}")
    print(f"output json (with ts if enabled): {json_file}")
    print(f"output excel: {output_excel}")
    print(f"max_clicks: {eff['max_clicks']}")
    print(f"click_timeout_ms: {eff['click_timeout_ms']}")
    print(f"initial_wait_ms: {eff['initial_wait_ms']}")
    print(f"headless: {eff['headless']}")
    print(f"window_width: {eff['window_width']}, window_height: {eff['window_height']}")
    print(f"scroll_min: {eff['scroll_min']}, scroll_max: {eff['scroll_max']}")
    print(f"scroll_sleep_min: {eff['scroll_sleep_min']}, scroll_sleep_max: {eff['scroll_sleep_max']}")
    print("=================")

    # parse-only 模式：只解析
    if args.parse_only:
        input_json = args.input_json or cfg.get("input_json") or eff.get("output_json") or json_file
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
    try:
        asyncio.run(
            run_crawler(
                url=eff["comments_page"],
                output_file=json_file,
                max_clicks=eff["max_clicks"],
                click_timeout_ms=eff["click_timeout_ms"],
                initial_wait_ms=eff["initial_wait_ms"],
                headless=eff["headless"],
                window_width=eff["window_width"],
                window_height=eff["window_height"],
                scroll_min=eff["scroll_min"],
                scroll_max=eff["scroll_max"],
                scroll_sleep_min=eff["scroll_sleep_min"],
                scroll_sleep_max=eff["scroll_sleep_max"],
            )
        )
    except KeyboardInterrupt:
        print("\n[中断] 用户取消运行。")
        sys.exit(1)
    except Exception as e:
        print("运行爬虫时发生未处理异常：", repr(e))
        raise

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
