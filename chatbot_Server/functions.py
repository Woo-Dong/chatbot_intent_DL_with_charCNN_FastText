import requests 
from soynlp.hangle import jamo_levenshtein 


def stringToNum(astring): 
    if astring in ['한', '하나']: return 1
    elif astring in ['두', '둘']: return 2
    elif astring in ['네', '넷']: return 4
    tmp_dict = { 
        '다섯': 5, 
        '여섯': 6, 
        '일곱': 7, 
        '여덟': 8, 
        '아홉': 9
    }
    return tmp_dict.get(astring, 0) 


def posIntentAPI(message): 

    req_json = dict() 
    req_json["message"] = message  

    # EC2_URL = "http://15.165.69.231/"
    EC2_URL = "http://15.165.69.231:5000" # For debugging 
    
    response = requests.post(url=EC2_URL, json=req_json)
    status_code = response.status_code 
    ret = False 
    if status_code // 100 != 2: 
        return (ret, None, None) 
    else: 
        res_dict = response.json()
        pos, intent = res_dict["pos"], res_dict["intent"]
        return (True, pos, intent) 
 
def takeOrder(products, pos_list): 

    all_products = products.find({})
    products_list = [elem["name"] for elem in all_products] 
    
    message = ''
    clean_pos = list() 
    for word, pos in pos_list: 
        if word == '한' and 'XSA+' in pos: continue 
        clean_pos.append((word, pos))
        message += word

    msg_length = len(message)
    tmp_res = list() 

    for WORD_LENGTH in range(4, 8): 
        for i in range(msg_length-WORD_LENGTH): 
            tmp_word = message[i:i+WORD_LENGTH]
            for elem in products_list:
                if len(elem) != WORD_LENGTH: continue 
                tmp_cost = jamo_levenshtein(tmp_word, elem) 
                if tmp_cost >= 1.3: continue 
                tmp_res.append((tmp_cost, elem, tmp_word, i))
    
    if not tmp_res: return None 

    tmp_res.sort(key=lambda x:x[0])

    fin_res = dict() 
    for _, menu, word, i in tmp_res: 
        if menu not in fin_res: fin_res[menu] = (word, i) 
        else: continue 


    pos_length = len(clean_pos)
    checkPos = [['', ''] for _ in range(pos_length)]

    for menu in fin_res: 
        word = fin_res[menu][0] 
        for i in range(pos_length): 
            tmp_word, _ = clean_pos[i] 
            
            if tmp_word == word:
                checkPos[i][0] = 'PRD'
                checkPos[i][1] = menu
                break 

            elif len(tmp_word) < len(word): 
                if tmp_word not in word: continue 
                tmp_check = False 
                if 0 < i and clean_pos[i-1][0] in word: tmp_check = True 
                if i < pos_length-1 and clean_pos[i+1][0] in word: tmp_check = True 

                if tmp_check: 
                    checkPos[i][0] = 'PRD'
                    checkPos[i][1] = menu

    idx = 0 

    fin_res_opt = dict() 
    for menu in fin_res: fin_res_opt[menu] = list() 


    while idx < pos_length: 

        word, pos = clean_pos[idx] 
        if checkPos[idx][0] == 'PRD': 
            idx += 1
            continue

        if word in ['뜨거운', '핫', '아이스', '차가운'] or pos in ['NR', 'XR', 'SN', 'NR'] \
            or (pos == 'MM' and word in ['한', '두', '네']) or word == '세잔':

            if pos == 'NR' or pos == 'MM': 
                word = stringToNum(word)  
            elif word == '세잔': word = 3 
            word = str(word) 

            if 0 < idx and checkPos[idx-1][0] == 'PRD': 
                prd = checkPos[idx-1][1]
                fin_res_opt[prd].append(word) 
            elif idx < pos_length-1 and checkPos[idx+1][0] == 'PRD': 
                prd = checkPos[idx+1][1] 
                fin_res_opt[prd].append(word)
                idx += 1
        idx += 1 

    ret = dict() 
    for menu in fin_res: 
        if fin_res_opt[menu]: fin_res_opt[menu].sort(reverse=True)
        ret[menu] = fin_res_opt[menu]
    return ret 
