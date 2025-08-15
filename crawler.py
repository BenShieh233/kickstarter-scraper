# crawler.py
import asyncio
import json
import hashlib
import random
import time
import os
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth
import yaml

def _commentable_hash(obj):
    """对 commentable 对象生成稳定哈希（JSON 排序）"""
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def add_commentable(commentable, graphql_pages, seen_endcursors, seen_hashes, source="unknown"):
    """
    统一去重并保存 commentable（仅由 on_response 调用）。
    返回 True 表示新加入，False 表示重复跳过。
    """
    try:
        page_info = (commentable.get("comments", {}) or {}).get("pageInfo", {}) or {}
        end_cursor = page_info.get("endCursor")
        print(f"[{source}] raw endCursor repr: {repr(end_cursor)}")

        token = end_cursor.strip() if isinstance(end_cursor, str) and end_cursor.strip() else None
        h = _commentable_hash(commentable)

        if token:
            if token in seen_endcursors:
                print(f"[{source}] token 已见，跳过: {repr(token)}")
                if h not in seen_hashes:
                    graphql_pages.append(commentable)
                    seen_hashes.add(h)
                    print(f"[{source}] token 已见但 hash 新，补存。hash={h}")
                    return True
                return False
            graphql_pages.append(commentable)
            seen_endcursors.add(token)
            seen_hashes.add(h)
            print(f"[{source}] 新 page 保存：token={repr(token)} hash={h}")
            return True
        else:
            if h in seen_hashes:
                print(f"[{source}] 无 token，hash 已见，跳过。hash={h}")
                return False
            graphql_pages.append(commentable)
            seen_hashes.add(h)
            print(f"[{source}] 无 token，按 hash 保存。hash={h}")
            return True
    except Exception as e:
        print(f"[{source}] add_commentable 异常: {repr(e)}")
        return False

async def human_like_scroll(page, scroll_min=50, scroll_max=150, sleep_min=0.1, sleep_max=0.4):
    """模拟人类滚动（小幅度抖动）"""
    try:
        viewport_height = await page.evaluate("() => window.innerHeight")
    except Exception:
        viewport_height = 900
    scroll_y = 0
    while scroll_y < viewport_height * 0.5:
        scroll_y += random.randint(scroll_min, scroll_max)
        await page.evaluate(f"window.scrollBy(0, {scroll_y})")
        await asyncio.sleep(random.uniform(sleep_min, sleep_max))

async def run_crawler(
    url,
    output_file="kickstarter_comments.json",
    max_clicks=30,
    click_timeout_ms=15000,
    initial_wait_ms=6000,
    headless=True,
    window_width=1400,
    window_height=900,
    scroll_min=50,
    scroll_max=150,
    scroll_sleep_min=0.1,
    scroll_sleep_max=0.4,
):
    """
    运行爬虫，参数全部可传入（run.py 将调用此函数）。
    返回保存的 output_file 路径。
    """
    graphql_pages = []      # 保存被捕获的 commentable 对象（每页）
    seen_endcursors = set() # 用 endCursor 去重
    seen_hashes = set()     # 回退去重

    async with Stealth().use_async(async_playwright()) as pw:
        browser = await pw.chromium.launch(
            headless=headless,
            args=[f"--window-size={window_width},{window_height}"]
        )
        context = await browser.new_context()
        page = await context.new_page()

        # 全局响应监听器
        async def on_response(response):
            try:
                if "/graph" not in response.url or response.status != 200:
                    return
                try:
                    body = await response.json()
                except Exception:
                    return
                if not isinstance(body, (list, tuple)) or len(body) == 0:
                    return
                first_item = body[0]
                commentable = first_item.get("data", {}).get("commentable")
                if not commentable:
                    return
                add_commentable(commentable, graphql_pages, seen_endcursors, seen_hashes, source="on_response")
            except Exception as e:
                print("on_response 捕获异常:", repr(e))

        page.on("response", on_response)

        # 打开页面并等待初始化（Cloudflare JS challenge)
        print("goto:", url)
        await page.goto(url)
        await asyncio.sleep(initial_wait_ms / 1000)  # 毫秒->秒

        try:
            async with page.expect_response(lambda r: "/graph" in r.url and r.status == 200, timeout=5000) as resp_ctx:
                pass
            print("Initial /graph response observed.")
        except PlaywrightTimeoutError:
            print("No initial /graph response observed within timeout; continuing.")

        for attempt in range(1, max_clicks + 1):
            print(f"\nAttempt {attempt}/{max_clicks} to click Load more... (time {time.strftime('%X')})")

            button = await page.query_selector('button:has-text("Load more")')
            if not button:
                button = await page.query_selector('button.kds-button[data-rac]')

            if not button:
                print("Load more 按钮未找到，可能已到底或页面结构变化。退出循环。")
                break

            response = None
            try:
                await button.evaluate("(el) => el.scrollIntoView({block: 'center', behavior: 'auto'})")
                await human_like_scroll(page, scroll_min, scroll_max, scroll_sleep_min, scroll_sleep_max)

                visible = await button.is_visible()
                enabled = await button.is_enabled()
                box = await button.bounding_box()
                print("button visible/enabled/box:", visible, enabled, box)

                if not visible or not enabled or not box:
                    print("按钮可能不可点击，尝试用 JS click。")
                    try:
                        async with page.expect_response(lambda r: "/graph" in r.url and r.status == 200, timeout=click_timeout_ms) as resp_ctx:
                            await button.evaluate("(el) => el.click()")
                        response = await resp_ctx.value
                    except PlaywrightTimeoutError:
                        print("JS click 等待 /graph 超时，跳过本次尝试。")
                        continue
                else:
                    await page.mouse.move(box["x"] + box["width"]/2, box["y"] + box["height"]/2)
                    await asyncio.sleep(random.uniform(0.15, 0.5))
                    try:
                        async with page.expect_response(lambda r: "/graph" in r.url and r.status == 200, timeout=click_timeout_ms) as resp_ctx:
                            await button.click()
                        response = await resp_ctx.value
                    except PlaywrightTimeoutError:
                        print(f"等待 /graph 响应超时（{click_timeout_ms}ms）。尝试 force click 或 JS click。")
                        try:
                            async with page.expect_response(lambda r: "/graph" in r.url and r.status == 200, timeout=click_timeout_ms) as resp_ctx:
                                await button.click(force=True)
                            response = await resp_ctx.value
                        except PlaywrightTimeoutError:
                            print("force click 也超时，继续下次尝试。")
                            await page.wait_for_timeout(800)
                            continue

            except Exception as e:
                print("点击或滚动阶段抛出异常:", repr(e))
                await page.wait_for_timeout(800)
                continue

            if response is None:
                print("本次点击未捕获到 /graph response，跳过解析。")
                await page.wait_for_timeout(800)
                continue

            # 只用于判断是否继续（不保存）
            try:
                body = await response.json()
            except Exception:
                print("本次 /graph 响应不是 JSON，跳过 hasNextPage 判断。")
                await page.wait_for_timeout(800)
                continue

            if not isinstance(body, (list, tuple)) or len(body) == 0:
                print("响应 body 不是预期的列表，跳过 hasNextPage 判断。")
                await page.wait_for_timeout(800)
                continue

            first_item = body[0]
            commentable = first_item.get("data", {}).get("commentable")
            if not commentable:
                print("本次 /graph 响应无 commentable 字段，跳过 hasNextPage 判断。")
                await page.wait_for_timeout(800)
                continue

            page_info = commentable.get("comments", {}).get("pageInfo", {}) or {}
            has_next = bool(page_info.get("hasNextPage"))
            end_cursor = page_info.get("endCursor")
            print(f"[click-path#{attempt}] hasNextPage={has_next}, endCursor repr: {repr(end_cursor)}")

            if not has_next:
                print("hasNextPage == False -> 到达最后一页，停止翻页。")
                break

            await page.wait_for_timeout(800)

        # 保存结果
        print(f"\n抓取完成，总共捕获 {len(graphql_pages)} pages (去重后)。")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(graphql_pages, f, ensure_ascii=False, indent=2)

        await browser.close()

    return output_file

# 当直接运行 crawler.py 时从 config.yaml 读取参数并运行
if __name__ == "__main__":
    cfg_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    if not os.path.exists(cfg_path):
        # 允许根目录的 config.yaml
        cfg_path = "config.yaml"

    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
    else:
        raise RuntimeError("找不到 config.yaml，请在项目根目录放置 config.yaml 或指定参数运行。")

    # 从 config 读取或使用默认
    url = cfg.get("comments_page")
    output = cfg.get("output_json", "kickstarter_comments.json")
    max_clicks = cfg.get("max_clicks", 30)
    click_timeout_ms = cfg.get("click_timeout_ms", 15000)
    initial_wait_ms = cfg.get("initial_wait_ms", 6000)
    headless = cfg.get("headless", True)
    window_width = cfg.get("window_width", 1400)
    window_height = cfg.get("window_height", 900)
    scroll_min = cfg.get("scroll_min", 50)
    scroll_max = cfg.get("scroll_max", 150)
    scroll_sleep_min = cfg.get("scroll_sleep_min", 0.1)
    scroll_sleep_max = cfg.get("scroll_sleep_max", 0.4)

    asyncio.run(run_crawler(
        url=url,
        output_file=output,
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
    ))
