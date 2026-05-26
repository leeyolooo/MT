import json, urllib.request, os
from logger import logger

WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK_URL", "")
APP_ID = os.environ.get("FEISHU_APP_ID", "")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
RECEIVE_ID = os.environ.get("FEISHU_RECEIVE_ID", "")
ID_TYPE = os.environ.get("FEISHU_ID_TYPE", "open_id")


def build_card(results):
    from datetime import datetime
    import pytz

    tz = pytz.timezone("Asia/Shanghai")
    now = datetime.now(tz).strftime("%Y/%m/%d %H:%M:%S")
    all_ok = len(results) > 0 and all(r.get("success") for r in results)

    elements = []
    if not results:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "⚠️ 无签到数据"},
        })
    else:
        for r in results:
            if r.get("success"):
                elements.append({
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": f"📧 **{r['user']}**\n✅ {r['msg']}"},
                })
            else:
                elements.append({
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": f"📧 **{r['user']}**\n❌ {r['msg']}"},
                })
            elements.append({"tag": "hr"})
        if elements and elements[-1]["tag"] == "hr":
            elements.pop()

    elements.append({
        "tag": "note",
        "elements": [{"tag": "plain_text", "content": f"⏰ {now}"}],
    })

    return {
        "header": {
            "title": {"tag": "plain_text", "content": "✅ MT论坛签到成功" if all_ok else "⚠️ MT论坛签到结果"},
            "template": "green" if all_ok else "orange",
        },
        "elements": elements,
    }


def api_request(url, data=None, headers=None, method=None):
    body = json.dumps(data).encode() if data else None
    h = {"Content-Type": "application/json", "User-Agent": "python"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    with urllib.request.urlopen(req) as resp:
        b = resp.read()
        return json.loads(b) if b else {}


def send_webhook(card):
    if not WEBHOOK_URL:
        logger.info("未配置飞书Webhook，跳过")
        return
    try:
        api_request(WEBHOOK_URL, {"msg_type": "interactive", "card": card})
        logger.info("飞书Webhook推送成功")
    except Exception as e:
        logger.error(f"飞书Webhook推送失败: {e}")


def send_app(card):
    if not APP_ID or not APP_SECRET or not RECEIVE_ID:
        logger.info("未配置飞书应用机器人，跳过")
        return
    try:
        token_resp = api_request(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            {"app_id": APP_ID, "app_secret": APP_SECRET},
        )
        token = token_resp.get("tenant_access_token")
        if not token:
            logger.error("飞书应用获取token失败")
            return
        api_request(
            f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={ID_TYPE}",
            {"receive_id": RECEIVE_ID, "msg_type": "interactive", "content": json.dumps(card)},
            {"Authorization": f"Bearer {token}"},
        )
        logger.info("飞书应用推送成功")
    except Exception as e:
        logger.error(f"飞书应用推送失败: {e}")


def push_feishu(results):
    card = build_card(results)
    send_webhook(card)
    send_app(card)
