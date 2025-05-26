from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FlexSendMessage

import schedule
import time
from threading import Thread
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials

import json
import os


def get_latest_form_url():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    json_str = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
    service_account_info = json.loads(json_str)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
    client = gspread.authorize(creds)
    
    client = gspread.authorize(creds)

    # スプレッドシート名は正確に！例：「ご飯フォーム管理」
    sheet = client.open("ご飯フォーム管理").sheet1

    # 最終行の1列目（最新URL）
    values = sheet.col_values(1)
    if len(values) > 1:
        return values[-1]
    else:
        return None

app = Flask(__name__)

# あなたのLINE Botの情報
LINE_CHANNEL_ACCESS_TOKEN = 'OXLBklHGyTCJVZ5JZVsuYmnsIh1Mb7sinqGn9aeBA75kfvuGEcPoyXQ9XB2Ce/iSp8Fifnsa4NMJiBt2J0upDnZ8VOXx7dEC+qZEwTHTkpfTWg4HW3h8d+7HJjbkVX7X4KjdyAmlk3KGBJBXzWBYtgdB04t89/1O/w1cDnyilFU='
LINE_CHANNEL_SECRET = 'd8a07bd4a2a132ab342f22a7eb65221a'

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Webhookルート
@app.route("/callback", methods=['GET', 'POST'])
def callback():
    if request.method == 'GET':
        return "GET OK", 200

    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)

    print("==== Webhook受信 ====")
    print(f"Signature: {signature}")
    print(f"Body: {body}")
    print("=====================")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("❌ 署名が一致しませんでした。")
        return "署名不正", 400

    return 'OK', 200

# メッセージ受信時の応答処理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    reply_text = "メッセージを受け取りました！"
    if event.source.type == 'group':
        group_id = event.source.group_id
        print(f"グループID: {group_id}")
        reply_text += f"\n（グループID取得済）"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

# === 毎週金曜18時に送信する処理 ===
def send_weekly_meal_check():
    form_url = get_latest_form_url()
    flex_content = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": "【🐈今週のご飯予定を教えてにゃ🐈】", "weight": "bold", "size": "md"},
                
                {
                    "type": "button",
                    "style": "link",
                    "action": {
                        "type": "uri",
                     "label": "▶ フォームに回答する",
                        "uri": form_url
                    },
                    "margin": "md"
                }
            ]
        }
    }

    try:
        GROUP_ID = "C3810b06521cab5b1eb03477dfdb3d628"  # あなたのグループID
        message = FlexSendMessage(alt_text="今週のご飯予定を教えてにゃ🐈！", contents=flex_content)
        line_bot_api.push_message(GROUP_ID, message)
        print(f"[{datetime.now()}] ✅ ご飯予定確認メッセージ送信完了")
    except Exception as e:
        print(f"❌ 送信エラー: {e}")


# スケジューラを別スレッドで動かす
def run_scheduler():
    schedule.every(1).minutes.do(send_weekly_meal_check)
    #schedule.every().friday.at("18:00").do(send_weekly_meal_check)
    # schedule.every(1).minutes.do(send_weekly_meal_check)  # ← テスト用に1分ごとに送る場合
    while True:
        schedule.run_pending()
        time.sleep(1)



# Flask起動
if __name__ == "__main__":
    scheduler_thread = Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    app.run(host='0.0.0.0', port=5050, debug=True, use_reloader=False)

