import streamlit as st
from streamlit_mic_recorder import mic_recorder # 使用这个插件
from openai import OpenAI
import pandas as pd
import json
import os
from datetime import datetime

# --- 1. 配置 ---
st.set_page_config(page_title="AI语音账本", page_icon="💰")
st.title("🎙️ 智能语音记账网站")

client = OpenAI(
    api_key=st.secrets["ALIYUN_API_KEY"],
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# --- 2. 核心解析逻辑 ---
def parse_text_to_json(text):
    prompt = '你是一个记账助手。请从文字中提取信息并只返回 JSON: {"item": "项目", "amount": 数字, "category": "分类"}'
    try:
        response = client.chat.completions.create(
            model="qwen-turbo",
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        st.error(f"解析失败: {e}")
        return None

# --- 3. 界面交互 ---
st.write("请点击下方按钮说话，系统会自动识别账单信息。")

# 重要：这是网页专用的录音组件，不依赖服务器硬件
audio = mic_recorder(
    start_prompt="开始录音",
    stop_prompt="停止录音",
    key='recorder'
)

if audio:
    # 由于网页环境直接转文字较复杂，我们先让用户确认识别内容
    # 以后可以接入阿里云 ASR 实现全自动转换
    st.audio(audio['bytes'])
    st.info("录音已完成！由于服务器环境限制，请在下方确认或输入您的账单内容：")
    
    user_input = st.text_input("识别结果校对 (示例: 中午吃火锅花了200元)", "今天中午吃面花了15块")

    if st.button("确认并存入账本"):
        bill_data = parse_text_to_json(user_input)
        if bill_data:
            file_name = "my_bills.csv"
            new_row = {
                "日期": datetime.now().strftime("%Y-%m-%d"),
                "项目": bill_data['item'],
                "金额": bill_data['amount'],
                "分类": bill_data['category']
            }
            # 更新表格
            df = pd.read_csv(file_name) if os.path.exists(file_name) else pd.DataFrame()
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_csv(file_name, index=False, encoding='utf-8-sig')
            
            st.success("记账成功！")
            st.balloons()
            st.rerun()

# --- 4. 账单展示 ---
st.divider()
st.subheader("📊 历史记录")
if os.path.exists("my_bills.csv"):
    st.dataframe(pd.read_csv("my_bills.csv"), use_container_width=True)
