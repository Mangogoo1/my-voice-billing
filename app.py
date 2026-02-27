import streamlit as st
import speech_recognition as sr
from openai import OpenAI
import pandas as pd
import json
import os
from datetime import datetime

# --- 页面配置 ---
st.set_page_config(page_title="智能语音记账", page_icon="💰")
st.title("智能语音记账助手")
st.markdown("点击下方按钮并说话，AI 将自动为你整理账单。")

# --- 初始化阿里云客户端 ---
client = OpenAI(
    api_key="sk-8272ab26559b4862ba5caa392cc65a5e", 
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# --- 核心功能函数 ---
def listen_and_parse():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.toast("正在倾听中...", icon="👂")
        recognizer.adjust_for_ambient_noise(source)
        try:
            audio = recognizer.listen(source, timeout=5)
            text = recognizer.recognize_google(audio, language='zh-CN')
            
            # AI 解析
            prompt = '提取账单为JSON: {"item": "项目", "amount": 数字, "category": "分类"}'
            response = client.chat.completions.create(
                model="qwen-turbo",
                messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text}],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content), text
        except Exception as e:
            st.error(f"识别出错啦: {e}")
            return None, None

# --- 数据展示逻辑 ---
file_name = "my_bills.csv"

# 显示现有的账单表格
st.subheader("📊 我的账单历史")
if os.path.exists(file_name):
    df = pd.read_csv(file_name)
    st.dataframe(df, use_container_width=True) # 漂亮的可交互表格
else:
    st.info("暂无账单数据，开始记第一笔吧！")

# --- 交互按钮 ---
if st.button("🎤 开始语音记账", type="primary"):
    data, raw_text = listen_and_parse()
    if data:
        st.success(f"识别到：{raw_text}")
        
        # 写入数据
        new_row = {
            "日期": datetime.now().strftime("%Y-%m-%d"),
            "项目": data['item'],
            "金额": data['amount'],
            "分类": data['category']
        }
        
        # 使用 Pandas 更新并保存
        if os.path.exists(file_name):
            df = pd.read_csv(file_name)
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        else:
            df = pd.DataFrame([new_row])
            
        df.to_csv(file_name, index=False, encoding='utf-8-sig')
        st.balloons() # 庆祝动画！
        st.rerun() # 刷新页面显示新数据
