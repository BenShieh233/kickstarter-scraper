import asyncio
import json
from playwright.async_api import async_playwright

COMMENTS_PAGE = "https://www.kickstarter.com/projects/libernovo/libernovo-omni-worlds-first-dynamic-ergonomic-chair/comments"
OUT_JSON = "commentable_all.json"
GRAPHQL_URL = "https://www.kickstarter.com/graph"

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False, args=["--window-size=1400,900"])
        context = await browser.new_context()
        page = await context.new_page()

        # 先从第一页真实请求里获取 commentableId
        graphql_bodies = []

        # 拦截并记录所有 /graph 的 response
        async def handle_response(response):
            try:
                url = response.url
                status = response.status
                if "/graph" in url and status == 200:
                    body = await response.json()  # Playwright 支持直接 .json()
                    first_item = body[0]
                    commentable = first_item.get("data", {}).get("commentable")
                    if commentable:
                        graphql_bodies.append(commentable)
            except Exception as e:
                print("handle_response error:", e)

        page.on("response", handle_response)

        # 触发一次第一页加载
        await page.goto(COMMENTS_PAGE)
        await page.wait_for_timeout(3000)

        if not graphql_bodies:
            print("没有捕获到第一页 commentable 数据")
            await browser.close()
            return

        commentable_id = graphql_bodies[-1]["id"]
        commentable = graphql_bodies[-1]
        page_info = commentable["comments"]["pageInfo"]
        # print(f"抓取到 {len(commentable['comments']['edges'])} 条评论, hasNext={page_info['hasNextPage']}")
        next_cursor = page_info["endCursor"]
        print(next_cursor)

        # 1. 读取 payload.json
        with open("payload.json", "r", encoding="utf-8") as f:
            payload = json.load(f)
        # 读取 headers.json
        with open("headers.json", "r", encoding="utf-8") as f:
            headers = json.load(f)        
        # 2. 修改 nextCursor
        payload[0]["variables"]["nextCursor"] = next_cursor    
        # 3. 用 playwright 发送请求
        # 3. 用 playwright 发送请求，并返回 status + data


        print("Status:", result["status"])
        # # 翻页抓取
        # all_pages = []
        # next_cursor = None
        # i = 0

        # while i < 1:
        #     data = await fetch_comments(page, commentable_id, next_cursor)
        #     commentable = data[0]["data"]["commentable"]
        #     all_pages.append(commentable)

        #     page_info = commentable["comments"]["pageInfo"]
        #     print(f"抓取到 {len(commentable['comments']['edges'])} 条评论, hasNext={page_info['hasNextPage']}")
        #     i += 1
        #     if not page_info["hasNextPage"]:
        #         break
        #     next_cursor = page_info["endCursor"]

        # 保存
        # with open(OUT_JSON, "w", encoding="utf-8") as f:
        #     json.dump(all_pages, f, ensure_ascii=False, indent=2)

        # print(f"共保存 {len(all_pages)} 页数据到 {OUT_JSON}")
        await browser.close()


asyncio.run(main())
