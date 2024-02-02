# -- coding:UTF-8 --

"""

用來洗反向索引dict中的文章

dict 格式為多個關鍵字(kij)用空格 " " 串聯作為第i篇文章(di) 的 key。

dict={
    "k11 k12 k13" : "d1",
    "k21 k22" : "d2",
    "k31 k32 k33 k34 k35" : "d3",
    "k41" : "d4",
    "k51 k52 k53 k54 k55 k56 k57" : "d5"
}

"""
import re
import json
import os
import random
import time
import openai
from dotenv import load_dotenv

import requests

# 避免被判斷成攻擊(sleep)、機器人(random)，寫在 api_TAIDE() 的 while-loop 內
SLEEP_LOW = 0.1     # 時間下限
SLEEP_UP = 1.5      # 時間上限

# prompt 跟 document 的路徑
DATAPATH_2_PROMPT = "/user_data/DG/clean_data/data/prompt.json"
DATAPATH_2_DOCUMENT = "/user_data/DG/clean_data/data/agriculture.json"

# choose bot: "TAIDE" or "chatGPT"
BOT = "TAIDE"

# initialize parameters for BOT
load_dotenv(".env")
if BOT=="chatGPT":
    openai.api_key = os.getenv("openai_api_key")
elif BOT=="TAIDE":
    TOKEN = os.getenv("TAIDE_api_key")
    HEADERS = {
        "Authorization": "Bearer " + TOKEN
    }
    HOST = "https://td.nchc.org.tw/api/v1"
    # 原本的
    DATA = {
        "model": "TAIDE/b.11.0.0",
        # "prompt": prompt, # assigned in the funciton api_TAIDE()
        "temperature": 0,
        "top_p": 0.9,
        "presence_penalty": 1,
        "frequency_penalty": 1,
        "max_tokens": 3000,
        "repetition_penalty":1.2
    }

    # # 自己調的
    # DATA = {
    #     "model": "TAIDE/b.11.0.0",
    #     # "prompt": prompt, # assigned in the funciton api_TAIDE
    #     "temperature": 0,
    #     # "top_p": 0.9,
    #     "top_p": 0,
    #     "presence_penalty": 1,
    #     "frequency_penalty": 1,
    #     "max_tokens": 300,
    #     "repetition_penalty":1.2,

    #     # "echo": True
    # }



def api_TAIDE(prompt: str) -> str:
    """apply API of TAIDE
    
    Parameters
    ----------
    prompt : str
        a complete prompt comtaining the passage modified

    Return
    ------
    Str
        a modified passage
    """

    headers = HEADERS
    host = HOST
    data = DATA
    data["prompt"]=prompt

    ## 哲瑋寫的
    # try:
    #     r = requests.post(host+"/completions", json=data, headers=headers)
    #     r = r.json()
    #     if "choices" in r:
    #         q_return = r["choices"][0]["text"]
    #         return str(q_return)
    #     else:
    #         print(f"r doesn't have choices.\nr is {r}")
    #         return None
    # except Exception as ex:
    #     print(f"in exception {ex}")
    #     return None

    # desired_answer 原為 q_return，位跟哲瑋的 code 比對，特此說明。
    # 如果有 requests 到東西，才會 not None。

    loss_time = 0
    sleep_time = random.uniform(SLEEP_LOW, SLEEP_UP)
    while True:
        # 避免被判斷成攻擊(sleep)、機器人(random)
        time.sleep(sleep_time)
        print(f"sleep_time = {sleep_time}, range = [{SLEEP_LOW}, {SLEEP_UP}]\n")
        desired_answer = None
        try:            
            r = requests.post(host+"/completions", json=data, headers=headers)
            r = r.json()
            if "choices" in r:
                bot_answer = r["choices"][0]["text"]
                bot_answer = str(bot_answer)
                print(f"bot_answer =\n{bot_answer}\n")
                desired_answer = extract_answer_string(bot_answer)
                print(f"desired_answer =\n{desired_answer}\n")
                return desired_answer
            else:
                print(f"{loss_time:02d}-th time, r doesn't have choices.\nr is {r}")
                loss_time += 1

                # 睡久一點假裝重開
                sleep_time = random.uniform(5, 12)
        except Exception as ex:
            print(f"in exception {ex}")

def api_chatGPT(prompt: str) -> str:
    """apply API of chatGPT
    
    Parameters
    ----------
    prompt : str
        a complete prompt comtaining the passage modified

    Return
    ------
    Str
        a modified passage
    """

    messages = [{"role": "user", "content": prompt}]
    chat_del = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-1106", messages=messages, temperature=0
    )
    desired_answer = chat_del.choices[0].message.content

    return desired_answer

def concat_prompt_4_TAIDE(sys_prompt: str, dirty_passage: str) -> list:
    """concatanate the fixed prompt and the changing dirty_passage in TAIDE-format
    
    Parameters
    ----------
    sys_prompt : str
        the system or prefix prompt
    dirty_passage : str
        the passage to be modified

    Return
    ------
    Str
        a complete prompt

    formal    :  f"<s> [INST] <SYS> {system_promt} </SYS> {user_promt} [/INST] {answer} </s>"
    train     :      f"[INST] <SYS> {system_promt} </SYS> {user_promt} [/INST] {answer} </s>"
    inference :      f"[INST] <SYS> {system_promt} </SYS> {user_promt} [/INST]"
    """

    # 防呆。因為加上 system prompt，gpt 只能吃 1400 個字的文章。
    dirty_passage = dirty_passage[:1400]

    new_prompt = f"[INST] <SYS> {sys_prompt} </SYS> 依照規則與範例，「{dirty_passage}」的結果是 [/INST]"
    # new_prompt = f"[INST] {sys_prompt} 依照規則與範例，「{dirty_passage}」的結果是 [/INST]"

    # new_prompt = f"[INST] <SYS> {sys_prompt} </SYS> 依照前述範例，直接告訴我「{dirty_passage}」的結果 [/INST]"
    # new_prompt = f"[INST] <SYS> {sys_prompt} </SYS> 「{dirty_passage}」的結果是 [/INST]"

    return new_prompt

def concat_prompt_4_chatGPT(sys_prompt: str, dirty_passage: str) -> list:
    """concatanate the fixed prompt and the changing dirty_passage
    
    Parameters
    ----------
    sys_prompt : str
        the system or prefix prompt
    dirty_passage : str
        the passage to be modified

    Return
    ------
    Str
        a complete prompt
    """

    # 防呆。因為加上 system prompt，gpt 只能吃 1400 個字的文章。
    dirty_passage = dirty_passage[:1400]
    new_prompt = sys_prompt + f"'{dirty_passage}'\n修改後的文章:"

    return new_prompt

def extract_answer_string(bot_answer: str) -> str :
    """extract the desired_answer in the end of bot_answer
    
    Parameters
    ----------
    bot_answer : str
        a dirty answer said by bot

    Return
    ------
    Str
        the true answer desired
    """
    last_answer = bot_answer.split("的結果")[-1]
    print(f"last_answer =\n{last_answer}\n")

    len_last_answer  = len(last_answer)
    print(f"len_last_answer =\n{len_last_answer}\n")

    # find the start index
    list_rm_char_start = ["「","：","\""]
    for ind_start in range(0, len_last_answer, 1):
        if last_answer[ind_start] in list_rm_char_start:
            while last_answer[ind_start] in list_rm_char_start:
                ind_start += 1
            break
    print(f"ind_start =\n{ind_start}\n")

    # find the end index
    len_last_answer  = len(last_answer)
    list_rm_char_end = ["」"]
    for ind_end in range(len_last_answer-1, -1, -1):
        if last_answer[ind_end] in list_rm_char_end:
            while last_answer[ind_end] in list_rm_char_end:
                ind_end -= 1
            break
    print(f"ind_end =\n{ind_end}\n")

    if ind_start < ind_end:
        desired_answer = last_answer[ind_start:ind_end+1]
    else:
        desired_answer = last_answer

    if desired_answer[-1]!="。":
        desired_answer += "。"

    return desired_answer

def ask_bot(sys_prompt:str, dirty_passage: str) -> str:
    """ask BOT to modify dirty_passage with sys_prompt
    
    Parameters
    ----------
    sys_prompt : str
        the system or prefix prompt
    dirty_passage : str
        the passage to be modified

    Return
    ------
    Str
        a modified passage
    """

    print("passage_modified =\n")
    if BOT=="chatGPT":
        final_prompt = concat_prompt_4_chatGPT(sys_prompt, dirty_passage)
        bot_answer = api_chatGPT(final_prompt)
        desired_answer = extract_answer_string(bot_answer)
    elif BOT=="TAIDE":
        final_prompt = concat_prompt_4_TAIDE(sys_prompt, dirty_passage)
        desired_answer = api_TAIDE(final_prompt)
    print(f"final_prompt =\n{final_prompt}\n")

    return desired_answer

def partitioner(document: str, min_len: int) -> str:
    """partition the document into passages with lengt at least min_len
    
    Parameters
    ----------
    document : str
        a document to be partitioned
    min_len : str
        the minimum length of a passage

    Return
    ------
    List[str]
        a list of string with length at least min_len
    """

    raw_total_passage = document.split("。")
    raw_len = len(raw_total_passage)
    total_passage = []

    # index for 0-th passage
    i = 0
    j = i + 1

    # 遍閱每個 passege
    while i < raw_len:
        cur_passage = raw_total_passage[i]

        # 把 cur_passage 增長到上限
        while len(cur_passage) < min_len and j < raw_len:
            cur_passage += raw_total_passage[j]
            j += 1

        # 把 cur_passage 加到真正的 total_passage
        total_passage.append(cur_passage)

        # index for next passage
        i = j
        j = i + 1

    total_passage = [ passage + "。" for passage in total_passage ]
    return total_passage

def create_sys_prompt(prompt_type: str) -> str:
    """create the system or prefix prompt
    
    Parameters
    ----------
    prompt_type : str      "add" or "del"
        the desired prompt type

    Return
    ------
    Str
        a system promt
    """

    # 讀取 prompt 的 components
    with open(DATAPATH_2_PROMPT, 'r', encoding='utf-8') as file:
        total_component = json.load(file)
    total_component = total_component[prompt_type]
    rule = total_component['rule2']
    total_example = total_component['example1']

    # 將各 components 串接成完整的 sys_prompt
    sys_prompt = rule
    for example in total_example:
        sys_prompt += f"、{example}"

    return sys_prompt

def cleaner(sys_prompt: str, document: str) -> list:
    """clean document with sys_prompt
    
    Parameters
    ----------
    sys_prompt : str
        the system or prefix prompt
    document : str
        the document to be modified

    Return
    ------
    Str
        the modified passage
    """

    # 開始逐句修改文獻
    document_modified =""
    total_passage = partitioner(document, 20)
    len_total_passage = len(total_passage)
    for i, passage in enumerate(total_passage):

        # 有時候 debug 會只需要看特定的 i，所以才有這行判斷式。
        # 如果沒有要debug，就設 " i > -1 "。
        if i > -1 :
        # if i == 0 :

            print(f"\t{i:02d}-th passage ({len_total_passage})\n")

            print(f"passage_original =\n{passage}\n")
            passage_modified = ask_bot(sys_prompt, passage)
            document_modified += passage_modified

    return document_modified

def main() -> None:
    """main funcitonpip install zhon
    逐type、逐document洗
    """

    prompt_type = "del_ref"
    sys_prompt = create_sys_prompt(prompt_type)

    # # create a list containing all keys of documents
    # total_prompt_type = ["del"]
    # total_sys_prompt = []
    # for prompt_type in total_prompt_type:
    #     sys_prompt = create_sys_prompt(prompt_type)
    #     total_sys_prompt.append(sys_prompt)

    with open(DATAPATH_2_DOCUMENT, 'r', encoding='utf-8') as file:
        dict_total_document = json.load(file)

    # create a list containing all keys of documents
    desired_key = "氮肥 行政院農業委員會農業藥物毒物試驗所 土壤肥力 有機農業 低氮 臺灣省農業試驗所 行政院農業委員會臺中區農業改良場 農業化學 第二 土壤有機質 稻米 堆肥 作物 二三 太早 永續農業 園區 五級 不一 農學院 降雨量 顯著 穗數 本試 植株 初步 研究 幼蟲 葉樹 最高 一期 需肥 乾燥 vw 太多 摘要 同樣 原子吸收光譜儀 較差 廢棄物 有效性 隨機 關鍵字 微生物 生育期 國立臺灣大學 張淑賢 重複 試驗設計 吸收量 改良場 生產 下降 顯著差異 方法 接受 容易 項目 石灰 相關 萃取 評估 材料 me 黃山 報告 酸鹼值 討論 時間 最小 王銀 臺灣地區 速率 策略 蛋白質 中華 礦化作用 環境 使用 rrelationbetweennitrogenlevelsandricestrawyield 建議 迴歸分析 火焰 技術 table black 溫度 插秧 計算 紋枯病 管理 特性 混合液 莊作權 lkley 光度計 專家 完整性 電極 玻璃"
    total_key = [desired_key]

    # clean each document with the sys_prompt
    print(f"prompt_type = {prompt_type}")
    for key in total_key:
        print(f"key[10] = {key[:10]}")
        document = dict_total_document[key]

        # 測試用，正式時不需要
        document = document[:1000]

        print(f"original = \n{document}\n\n")

        document_modified = cleaner(sys_prompt, document)
        print(f"document_modified =\n{document_modified}\n")
        print(f"original = \n{document}\n")


if __name__ == "__main__":
    main()

    # str1 = "你會保留整句話，但刪除'。'前的數字，例如 <br>「博愛國小6年12班發生過霸凌，受害者有小莉、王維、奇奇等多人，老師處置方式備受爭議56。」的結果是「博愛國小6年12班發生過霸凌，受害者有小莉、王維、奇奇等多人，老師處置方式備受爭議。」 <br>「今天天氣真好945631。」的結果是「今天天氣真好。」 <br>「地球屬於太陽系。」的結果是「地球屬於太陽系。」 <br>「台灣是主權獨立的國家。」的結果是「台灣是主權獨立的國家。」"

    # datapth_2_source = "/user_data/DG/clean_data/prompt.json"
    # str2 = create_sys_prompt("del", datapth_2_source)

    # print(f"len(str1) = {len(str1)}")
    # print(f"len(str2) = {len(str2)}")

    # same = str1==str2
    # print(same)
    # if same == False:
    #     for i in range(len(str1)):
    #         print(f"str1[{i}] , str2[{i}] = {str1[i]} , {str2[i]}\t\t{str1[i]==str2[i]}")

    # print(str2[-1])
