import streamlit as st
from streamlit_mic_recorder import mic_recorder
from openai import OpenAI
import pandas as pd
import json
import os
from datetime import datetime
import io

# --- 1. 页面配置 (保持极简，避免触发数学解析 Bug) ---
st.set_page_config(page_title="语音账本", page_icon="💰")
st.title("🎙️ 智能语音记账")

# 安全获取 API Key
try:
    api_key = st.secrets["ALIYUN_API_KEY"]
except:
    api_key = ""

client = OpenAI(
    api_key=api_key,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# --- 2. 核心逻辑：语音转文字 + AI 解析 ---
def process_audio_to_bill(audio_bytes):
    try:
        # A. 语音转文字 (ASR)
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "record.mp3"
        
        transcript = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file
        )
        recognized_text = transcript.text
        
        if not recognized_text:
            return None, "未能识别到声音内容"

        # B. AI 结构化解析
        prompt = '你是一个账单助手。请从文字中提取信息并只返回JSON格式: {"item": "项目", "amount": 数字, "category": "分类"}'
        response = client.chat.completions.create(
            model="qwen-turbo",
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": recognized_text}],
            response_format={"type": "json_object"}
        )
        
        data = json.loads(response.choices[0].message.content)
        return data, recognized_text

    except Exception as e:
        return None, str(e)

# --- 3. 网页交互界面 ---
st.info("点击下方按钮并说话，系统将自动完成记账。")

# 录音组件
audio = mic_recorder(
    start_prompt="● 开始记账",
    stop_prompt="■ 停止并自动保存",
    key='my_recorder'
)

if audio:
    with st.spinner('🚀 正在同步到云端并解析...'):
        bill_data, raw_text = process_audio_to_bill(audio['bytes'])
        
        if bill_data:
            # 数据落地
            file_name = "my_bills.csv"
            new_row = {
                "日期": datetime.now().strftime("%Y-%m-%d"),
                "项目": bill_data.get('item', '未知'),
                "金额": bill_data.get('amount', 0),
                "分类": bill_data.get('category', '其他')
            }
            
            # 使用 Pandas 更新
            if os.path.exists(file_name):
                df = pd.read_csv(file_name)
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            else:
                df = pd.DataFrame([new_row])
            
            df.to_csv(file_name, index=False, encoding='utf-8-sig')
            
            # 结果反馈
            st.success(f"已识别: {raw_text}")
            st.write(f"✅ 成功记录：{new_row['项目']} | {new_row['金额']}元")
            st.balloons()
            # 延迟一下再刷新，让用户看清结果
            st.rerun()
        else:
            st.error(f"解析失败，请再试一次。错误信息: {raw_text}")

# --- 4. 历史记录展示 ---
st.divider()
st.subheader("📊 历史账单")
if os.path.exists("my_bills.csv"):
    history_df = pd.read_csv("my_bills.csv")
    # 按照日期倒序排列，最新的在上面
    st.table(history_df.tail(10)) 
else:
    st.caption("目前还没有记录哦。")
