import json
import pandas as pd
from datetime import datetime, timezone

def parse_edges_to_excel(input_file, output_file):
    with open(input_file, "r", encoding="utf-8") as f:
        pages = json.load(f)

    all_comments = []

    def safe_timestamp(ts):
        """把时间戳转换为 datetime（UTC），无效则返回 None"""
        try:
            return datetime.fromtimestamp(ts)
        except Exception:
            return None

    def process_comment_node(node, parent_id=None):
        if not node:
            return

        comment = {
            "comment_id": node.get("id"),
            "parent_id": parent_id or node.get("parentId"),
            "body": node.get("body"),
            "created_at": safe_timestamp(node.get("createdAt")),
            "removed": node.get("removedPerGuidelines"),
            "author_badges": node.get("authorBadges"),
            "deleted": node.get("deleted"),
            "pinned_at": safe_timestamp(node.get("pinnedAt")),
            "author_canceled_pledge": node.get("authorCanceledPledge"),
            "author_backing": node.get("authorBacking"),
        }

        author = node.get("author") or {}
        comment.update({
            "author_id": author.get("id"),
            "author_name": author.get("name"),
            "author_url": author.get("url"),
            "author_avatar": author.get("imageUrl"),
            "author_blocked": author.get("isBlocked"),
        })

        all_comments.append(comment)

        # 递归解析 replies
        for reply_node in (node.get("replies") or {}).get("nodes") or []:
            process_comment_node(reply_node, parent_id=node.get("id"))

    for page in pages:
        edges = (page.get("comments") or {}).get("edges") or []
        for edge in edges:
            process_comment_node(edge.get("node"))

    df = pd.DataFrame(all_comments)
    df.to_excel(output_file, index=False)
    print(f"[解析完成] {len(df)} 条评论已保存到 {output_file}")

if __name__ == "__main__":
    # 单独运行时的默认值
    parse_edges_to_excel("test.json", "kickstarter_comments.xlsx")
