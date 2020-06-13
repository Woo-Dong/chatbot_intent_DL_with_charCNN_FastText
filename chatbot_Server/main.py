# uwsgi --socket 0.0.0.0:5000 --protocol=http -w flaskapp:app
from flask import Flask, request, abort
app = Flask(__name__)

# LineBot Library call =====================================
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    LineBotApiError, InvalidSignatureError
)
from linebot.models import ( MessageEvent, ButtonsTemplate, TemplateSendMessage,
    TextMessage, TextSendMessage, MessageAction,QuickReply, QuickReplyButton,
    CarouselTemplate, CarouselColumn, URIAction, FlexSendMessage
)

CHANNEL_ACCESS_TOKEN = 'oqMEiC+Mvvbh2Q+b93NsUk65lfdTwWxcfCcZJ9R9rJAeOBYXytd3BWjyOggiBovqF/9jnQUhBsPtU9kGWsdLRNvtNiqySmQs5nxOzpdd95w03UpRwurf8nGK/WJiDRjyAOb7HkPokYLaNnUKjPVGmQdB04t89/1O/w1cDnyilFU='
CHANNEL_SECRET = '1da6192d6992b311c96010792bdc5c59'
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)
# ===========================================================

# Callback Setting -> less use to develop. better if not touch
@app.route("/callback", methods=['GET', 'POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try: handler.handle(body, signature)
    except InvalidSignatureError: abort(400)
    return 'OK'
# ==========================================================

# Setting MongoDB Connection ================================
from pymongo import MongoClient
from collections import OrderedDict


uri = 'mongodb://user:dwpark94@ds011725.mlab.com:11725/capstone'
conn = MongoClient(uri, retryWrites="false")
db = conn.get_default_database()
user_info = db['userinfo']
products = db['product']
detailed_info = db['detailedInfo']
orderList = db['orderList']
# ===========================================================

import json 
from functions import posIntentAPI, takeOrder
from soynlp.hangle import jamo_levenshtein 

@app.route('/complete', methods=['GET'])

def complete_order(): 
    param_dict = request.args.to_dict()

    user_id = param_dict["user_id"]
    menu = orderList.find_one({"user_id": user_id})["menu"]

    tmp_query = { "user_id": user_id }
    new_received = { "$set": { "received": True } }
    orderList.update_one(tmp_query, new_received) 


    sentence = "주문하신 음료/케익 나왔습니다.\n" + menu + "\n" 
    sentence += "수령대에서 받아가시면 되며, 행복한 시간 보내세요:)"
    line_bot_api.push_message(
            user_id,
            TextSendMessage(text= sentence )
        )
    return sentence  

# Message Handler Setting ==================================
@handler.add(MessageEvent, message=TextMessage)
def handle_stage(event):

    profile = line_bot_api.get_profile(event.source.user_id)
    reply_msg = event.message.text 
    user_id = event.source.user_id
    event_token = event.reply_token
    username = profile.display_name

    query_id = user_info.find_one({"user_id": user_id})
    user_stage = 0 
    if not query_id: 
        user_dict = dict() 
        user_dict['user_id'] = user_id
        user_dict['username'] = username
        user_dict['stage'] = 0
        user_info.insert(OrderedDict(user_dict))
    else: user_stage = query_id['stage'] 


    # Step1. Based on Special Keyword  ===========
    if reply_msg == "메뉴": 
        buttons_template = ButtonsTemplate(
            title='주요 기능이에요!', text='아래 보기에서 원하시는 서비스를 선택해 주세요:)', 
            actions=[
                MessageAction(label="주문하고 싶어", text="주문하기"),
                MessageAction(label="최근 주문한거 조회하고 싶어", text="주문조회"),
                MessageAction(label="뭐 물어보고 싶어", text="기타문의")
            ]
        )

        line_bot_api.push_message( 
            user_id,
            TemplateSendMessage(alt_text='보기 선택하기', template=buttons_template) 
        )
    elif reply_msg == "기타문의": 

        buttons_template = ButtonsTemplate(
            title='기타 문의에요!', text='아래 보기에서 궁금한 것이 있다면 선택해 주세요:)', 
            actions=[
                MessageAction(label="영업시간문의", text="영업시간문의"),
                MessageAction(label="시럽설탕요구", text="시럽설탕요구"),
                MessageAction(label="냅킨물티슈요구", text="냅킨물티슈요구"),
                MessageAction(label="화장실이용문의", text="화장실이용문의")
            ]
        )

        line_bot_api.reply_message(
            event_token,
            TemplateSendMessage(alt_text='보기 선택하기', template=buttons_template) 
        )

    elif reply_msg == "의도틀림": 
        user_stage = 0 # 초기 단계 
        tmp_query = { "user_id": user_id }
        new_stage = { "$set": { "stage": user_stage } }
        user_info.update_one(tmp_query, new_stage) 

        sentence = "죄송합니다ㅠㅠ 다시 한번 입력해 보시면 똑똑하게 맞춰 볼께요! 만약 버튼식으로 서비스를 이용하시려면 '메뉴'라고 적어주세요!"
        line_bot_api.reply_message(
            event_token,
            TextSendMessage(text= sentence )
        )

    elif reply_msg == "주문하기": 
        user_stage = 0 # 초기 단계 
        tmp_query = { "user_id": user_id }
        new_stage = { "$set": { "stage": user_stage } }
        user_info.update_one(tmp_query, new_stage) 

        sentence = "주문하시려면 원하시는 음료나 케익을 말씀하세요! \n 예시) 따뜻한 아메리카노 3잔이랑 치즈케익 2개 주세요"
        line_bot_api.reply_message(
            event_token,
            TextSendMessage(text= sentence )
        )

    elif reply_msg == "주문맞음": 
        
        user_stage = 1 # 주문 단계 
        tmp_query = { "user_id": user_id }
        new_stage = { "$set": { "stage": user_stage } }
        user_info.update_one(tmp_query, new_stage)

        menu = orderList.find_one({"user_id": user_id})["menu"]

        total_cash = 0 
        for elem in menu.split("\n"): 
            sub_menu, cnt = elem.split(":")
            sub_menu = sub_menu.strip() 
            if "/" in cnt: 
                cnt = int(cnt.split("/")[1][:-1]) 
            else: cnt = int(cnt.strip()[:-1]) 

            each_cash = products.find_one({"name": sub_menu})["cost"]            
            total_cash += (each_cash*cnt)

        buttons_template = ButtonsTemplate(
                title='주문 단계', text='총 {}원 입니다. 결제하시겠어요?'.format(total_cash), 
                actions=[
                    MessageAction(label="결제할래", text="결제요청"),
                    MessageAction(label="아니야 그냥 주문 안할래", text="주문취소"),
                ]
            )

        line_bot_api.push_message( 
            user_id,
            TemplateSendMessage(alt_text='보기 선택하기', template=buttons_template)
        )

    elif reply_msg == "주문조회": 
        recent_order = orderList.find_one({"user_id": user_id})

        if recent_order: 
            sentence = "최근 주문하신 내역입니다\n" 
            menu = recent_order["menu"]
            menu = menu.replace("\n", " ")
            sentence += "<메뉴> " + menu + "\n" 
            payed = recent_order["payed"] 
            payed = "예" if payed else "아니오"
            sentence += "결제여부: " + payed + "\n" 
            received = recent_order["received"]
            if payed == "예":
                received = "제조 완료" if received else "제조 중"
            else: received = "주문 미완료" 
            sentence += "상태: " + received 

            line_bot_api.reply_message(
                event_token,
                TextSendMessage(text= sentence )
            )

        else: 
            sentence = "최근 주문하신 내역이 없습니다!" 
            line_bot_api.reply_message(
                event_token,
                TextSendMessage(text= sentence )
            )


    elif reply_msg == "주문틀림": 
        orderList.delete_one({"user_id": user_id})

        sentence = "죄송합니다ㅠㅠ 다시 또박또박 써주시면 정확하게 이해해 볼께요!" 
        line_bot_api.reply_message(
            event_token,
            TextSendMessage(text= sentence )
        ) 
    

    elif reply_msg == "주문취소": 
        orderList.delete_one({"user_id": user_id})

        tmp_query = { "user_id": user_id }
        new_stage = { "$set": { "stage": 0 } }
        user_info.update_one(tmp_query, new_stage)

        sentence = "주문 과정이 취소되었습니다! 다음에 기회가 된다면 또 저희 카페를 이용바랍니다:)"
        line_bot_api.reply_message(
            event_token,
            TextSendMessage(text= sentence )
        ) 

    elif reply_msg == "결제요청": 
        if user_stage != 1:
            sentence = "죄송합니다ㅠㅠ 결제할 주문이 존재하지 않습니다. 먼저 주문 부탁드려요!"
            line_bot_api.reply_message(
                event_token,
                TextSendMessage(text= sentence )
            ) 
        else: 
            order_dict = orderList.find_one({"user_id": user_id})

            if order_dict["payed"]: 
                sentence = "이미 결제하신 주문이에요! 다른 주문을 원하신다면 말씀해 주세요:)" 
                line_bot_api.reply_message(
                    event_token,
                    TextSendMessage(text= sentence )
                )

            else:
                menu = order_dict["menu"]
                
                total_cash = 0 
                for elem in menu.split("\n"): 
                    sub_menu, cnt = elem.split(":")
                    sub_menu = sub_menu.strip() 
                    if "/" in cnt: 
                        cnt = int(cnt.split("/")[1][:-1]) 
                    else: cnt = int(cnt.strip()[:-1]) 

                    each_cash = products.find_one({"name": sub_menu})["cost"]            
                    total_cash += (each_cash*cnt)

                tmp_query = { "user_id": user_id }
                new_payed = { "$set": { "payed": True } }
                orderList.update_one(tmp_query, new_payed) 

                user_stage = 0 
                tmp_query = { "user_id": user_id }
                new_stage = { "$set": { "stage": user_stage } }
                user_info.update_one(tmp_query, new_stage)

                sentence = "{}원 결제 완료되었습니다! 음료가 준비 끝나면 알려드릴께요:)".format(total_cash) 
                line_bot_api.reply_message(
                    event_token,
                    TextSendMessage(text= sentence )
                )

    elif reply_msg == "응!! 고마워": 
        sentence = "감사합니다:) 더 필요하시면 언제든지 말씀하세요~"
        line_bot_api.reply_message(
            event_token,
            TextSendMessage(text= sentence )
        )
 
    elif reply_msg in [
        "영업시간문의", "뜨거운차가운물요구", "시럽설탕요구", "냅킨물티슈요구", 
        "화장실이용문의", "남은음료테이크아웃문의"]: 

        info_dict = detailed_info.find_one({"intent": reply_msg}) 
        line_bot_api.reply_message(
            event_token,
            TextSendMessage(text= info_dict["content"] )
        )

        line_bot_api.push_message(
            user_id,
            TextSendMessage(
                text= "답변에 도움이 되셨나요?!",
                quick_reply= QuickReply(
                    items= [
                        QuickReplyButton(
                            action= MessageAction(label="응!! 고마워", text="응!! 고마워")
                        ),
                        QuickReplyButton(
                            action= MessageAction(label="아니 다른거 물어보는거야ㅠㅠ", text="의도틀림")
                        )
                    ])))
    # ============================================ 

    # Step2. Preferring Intent on the message ====
    else: 
        error_sentence = "죄송합니다, 내부 서버오류로 인해 장애가 발생하였습니다. 잠시후에 시도해 주세요."
        fin_text_msg = "답변에 도움이 되셨나요?!"

        res, pos, intent = posIntentAPI(reply_msg) 
        print("res, pos, intent: ", res, pos, intent) 

        if not res: 
            line_bot_api.reply_message(
                event_token,
                TextSendMessage(text= error_sentence )
            )

        else: 

            if intent in [
                "영업시간문의", "뜨거운차가운물요구", "시럽설탕요구", "냅킨물티슈요구", 
                "화장실이용문의", "남은음료테이크아웃문의"]: 

                info_dict = detailed_info.find_one({"intent": intent}) 
                line_bot_api.reply_message(
                    event_token,
                    TextSendMessage(text= info_dict["content"] )
                )

                line_bot_api.push_message(
                    user_id,
                    TextSendMessage(
                        text= fin_text_msg,
                        quick_reply= QuickReply(
                            items= [
                                QuickReplyButton(
                                    action= MessageAction(label="응!! 고마워", text="응!! 고마워")
                                ),
                                QuickReplyButton(
                                    action= MessageAction(label="아니 다른거 물어보는거야ㅠㅠ", text="의도틀림")
                                )
                            ])))

            elif intent == "메뉴문의": 
                message = reply_msg.replace(' ', '') 
                msg_length = len(message)
                tmp_res = list() 

                all_products = products.find({})
                products_list = [elem["name"] for elem in all_products] 
                for WORD_LENGTH in range(4, 8): 
                    for i in range(msg_length-WORD_LENGTH): 
                        tmp_word = message[i:i+WORD_LENGTH]
                        for elem in products_list:
                            if len(elem) != WORD_LENGTH: continue 
                            tmp_cost = jamo_levenshtein(tmp_word, elem) 
                            if tmp_cost >= 1.3: continue 
                            tmp_res.append((tmp_cost, elem, tmp_word, i))
                
                if not tmp_res: 
                    sentence = "죄송합니다ㅠㅠ 제가 처리할 수 없는 일이에요.. 제가 할 수 있는 일이 궁금하다면 '메뉴'라고 적어주세요!" 
                    line_bot_api.reply_message(
                        event_token,
                        TextSendMessage(text= sentence )
                    )
                else: 
                    tmp_res.sort(key=lambda x:x[0])
                    fin_prd = products.find_one({"name": tmp_res[0][1]}) 

                    sentence = fin_prd["name"] + "에 대해 궁금하신가요?! 제가 알려드릴께요! \n"
                    sentence += "종류: " + fin_prd["name"] + "\n"
                    sentence += "가격: " + str(fin_prd["cost"]) + "원\n"
                    sentence += "상세: " + fin_prd["detailed"]

                    line_bot_api.reply_message(
                        event_token,
                        TextSendMessage(text= sentence )
                    )
            elif intent == "일반주문": 
                order_res = takeOrder(products, pos)
                print("order_res: ", order_res)

                send_text = "주문을 원하시나요? 직접 제가 원하시는 메뉴를 확인했어요!(메뉴: 옵션)\n"
                menu_text = ''
                for menu in order_res: 
                    detailed_menu = menu  + ": "
                    chk_num = False 
                    if order_res[menu]: 
                        for elem in order_res[menu]: 
                            if elem.isnumeric(): 
                                detailed_menu += elem + '개/'
                                chk_num = True 
                            else: detailed_menu += elem + '/'

                    if not chk_num: detailed_menu += '1개/'
                    detailed_menu = detailed_menu[:-1] 
                    send_text += detailed_menu + '\n'
                    menu_text += detailed_menu + '\n'

                line_bot_api.reply_message(
                    event_token,
                    TextSendMessage(text= send_text )
                )
                query_order = orderList.find_one({"user_id": user_id})

                if query_order: orderList.delete_one({"user_id": user_id})

                order_dict = dict() 
                order_dict['user_id'] = user_id 
                order_dict['menu'] = menu_text[:-1]
                order_dict['received'] = False 
                order_dict['payed'] = False 
                orderList.insert(order_dict)

                buttons_template = ButtonsTemplate(
                        title='주문이 맞으신가요?!', text='아래 보기에서 선택해 주세요:)', 
                        actions=[
                            MessageAction(label="응!! 맞아", text="주문맞음"),
                            MessageAction(label="아니야 다시 주문할께", text="주문틀림"),
                            MessageAction(label="주문하려던 거 아니야ㅠㅠ", text="의도틀림")
                        ]
                    )

                line_bot_api.push_message( 
                    user_id,
                    TemplateSendMessage(alt_text='보기 선택하기', template=buttons_template)
                )

            elif intent == "결제요청": 
                if user_stage != 1:
                    sentence = "죄송합니다ㅠㅠ 결제할 주문이 존재하지 않습니다. 먼저 주문 부탁드려요!"
                    line_bot_api.reply_message(
                        event_token,
                        TextSendMessage(text= sentence )
                    ) 
                else: 
                    order_dict = orderList.find_one({"user_id": user_id})

                    if order_dict["payed"]: 
                        sentence = "이미 결제하신 주문이에요! 다른 주문을 원하신다면 말씀해 주세요:)" 
                        line_bot_api.reply_message(
                            event_token,
                            TextSendMessage(text= sentence )
                        )

                    else:
                        menu = order_dict["menu"]
                        
                        total_cash = 0 
                        for elem in menu.split("\n"): 
                            sub_menu, cnt = elem.split(":")
                            sub_menu = sub_menu.strip() 
                            cnt = int(cnt.split("/")[1][0]) 

                            each_cash = products.find_one({"name": sub_menu})["cost"]            
                            total_cash += (each_cash*cnt)

                        tmp_query = { "user_id": user_id }
                        new_payed = { "$set": { "payed": True } }
                        orderList.update_one(tmp_query, new_payed) 

                        user_stage = 0 
                        tmp_query = { "user_id": user_id }
                        new_stage = { "$set": { "stage": user_stage } }
                        user_info.update_one(tmp_query, new_stage)

                        sentence = "{}원 결제 완료되었습니다! 음료가 준비 끝나면 알려드릴께요:)".format(total_cash) 
                        line_bot_api.reply_message(
                            event_token,
                            TextSendMessage(text= sentence )
                        )


            elif intent in ["사이즈요구", "에스프레소샷개수요구", "얼음요구", 
                            "테이크아웃요구", "모바일페이결제", "할인문의", "제조시간문의", 
                            "사이즈문의", "텀블러할인문의", "쿠폰멤버십적립문의", "테이크아웃문의"]: 
                fin_sentence = intent + " 를 물어보셨나요?! \n죄송합니다. 아직 서비스 준비 중 입니다. 데스크에 문의 바랍니다:)" 
                line_bot_api.reply_message(
                    event_token,
                    TextSendMessage(text= fin_sentence )
                )

            else: 
                line_bot_api.reply_message(
                    event_token,
                    TextSendMessage(text= error_sentence )
                )
        
# ==========================================================


# Flask Main Setting -> running app ========================
if __name__ == "__main__":
    app.run()
# ==========================================================
