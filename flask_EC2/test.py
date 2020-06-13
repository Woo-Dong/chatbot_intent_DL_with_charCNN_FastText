from tensorflow.keras.preprocessing import sequence
from tensorflow.keras.models import load_model
import numpy as np 
import pickle

saved_model_path = './model_save/myModel_ver{}.h5' 
tokenizer_path = './tokenizer/tokenizer.pickle'
max_seq_len = 20

with open(tokenizer_path, 'rb') as handle: 
    tokenizer = pickle.load(handle)
print("loading tokenizer completed")

model_list = list() 
for i in range(1, 11): 
    new_model = load_model(saved_model_path.format(i))
    model_list.append(new_model) 
print("loading deep learning completed")


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

print(predict_intent("아이스 아메리카노 하나 주세요"))