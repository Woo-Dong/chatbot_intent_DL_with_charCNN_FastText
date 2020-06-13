import requests
from flask import Flask, jsonify, request
from konlpy.tag import Mecab 

from tensorflow.keras.preprocessing import sequence
from tensorflow.keras.models import load_model
import numpy as np 
import pickle

app = Flask(__name__)
mecab = Mecab() 

saved_model_path = './model_save/myModel_ver{}.h5' 
tokenizer_path = './tokenizer/tokenizer.pickle'
max_seq_len = 30

with open(tokenizer_path, 'rb') as handle: 
    tokenizer = pickle.load(handle)
print("loading tokenizer completed")

model_list = list() 
for i in range(1, 11): 
    new_model = load_model(saved_model_path.format(i))
    model_list.append(new_model) 
print("loading deep learning completed")


idx2intent = {
    
    2: '가격문의',
    7: '메뉴문의',

    0: '영업시간문의',
    6: '뜨거운차가운물요구',
    8: '시럽설탕요구',
    11: '냅킨물티슈요구',
    12: '화장실이용문의',
    16: '할인문의',
    14: '사이즈문의',
    19: '텀블러할인문의',
    20: '남은음료테이크아웃문의',
    4: '테이크아웃문의',
    10: '쿠폰멤버십적립문의',

    5: '일반주문',

    1: '사이즈요구',
    13: '에스프레소샷개수요구',
    18: '얼음요구',
    15: '테이크아웃요구',
    17: '결제요청',
    3: '모바일페이결제',

    9: '제조시간문의'
}

def predict_intent(test_text): 
    test_text = list(test_text.replace(" ", ''))
    test_text = ' '.join(test_text)
    test_text = tokenizer.texts_to_sequences([test_text])
    test_text = sequence.pad_sequences(test_text, max_seq_len)
    res = model_list[0].predict(test_text)
    for i in range(1, 10): 
        tmp_res = model_list[i].predict(test_text) 
        res += tmp_res 
    
    return np.argmax(res)


@app.route('/', methods=['POST'])

def main_flow():

    req = request.get_json()
    message = req["message"] 
    pos_ret = mecab.pos(message) 
    intent_res = idx2intent[predict_intent(message)]

    return jsonify({
        'pos': pos_ret, 
        'intent': intent_res
    })

if __name__ == "__main__":
    app.run(host='0.0.0.0')