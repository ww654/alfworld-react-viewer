import streamlit as st
import json
import os

# --- 页面配置 ---
st.set_page_config(page_title="ALFWorld ReAct Agent Viewer", layout="wide")
st.title("Revisiting ReAct on ALFWorld: Trajectory & Memory Viewer")
st.markdown("深入探索 DeepSeek ReAct Agent 的失败模式、消融实验与情节记忆。")

# --- 数据加载与解析函数 ---
@st.cache_data
def load_json_data(filepath):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def parse_model_response(response_text):
    """解析模型输出，分离 Think 和 Act"""
    think, act = response_text, ""
    if "Act:" in response_text:
        parts = response_text.split("Act:")
        think = parts[0].replace("Think:", "").strip()
        act = parts[1].strip()
    return think, act

# 加载真实失败数据
all_failures = load_json_data("all_failures.json")

# --- 侧边栏导航 ---
st.sidebar.header("Navigation")
page = st.sidebar.radio("Select a View:", [
    "1. 失败模式深度剖析 (Failure Modes)", 
    "2. 提示词脆弱性：V2 vs V3 对比", 
    "3. 情节记忆日志 (Memory Logs)"
])

# --- 页面 1：失败模式剖析 ---
if page == "1. 失败模式深度剖析 (Failure Modes)":
    st.header("1. 失败模式深度剖析 (Micro-Trajectory Viewer)")
    st.write("逐步回放失败局数，自动检测模型预期动作与环境实际执行之间的偏差。")
    
    # 将 JSON 数据转为字典，方便按 game_id 查找
    failures_dict = {f"Game {game['game_id']} ({game['task_type']})": game for game in all_failures}
    
    if not failures_dict:
        st.warning("请确保 all_failures.json 与本脚本在同一目录下。")
    else:
        selected_game_key = st.selectbox("选择要回放的失败局:", list(failures_dict.keys()))
        game_data = failures_dict[selected_game_key]
        
        st.subheader(f"任务目标: {game_data['initial_obs'].split('Your task is to:')[-1].strip()}")
        st.markdown(f"**总步数:** {game_data['total_steps']} 步 | **最终结果:** {game_data['result']}")
        
        # 渲染每一步的微观轨迹
        for step in game_data['steps']:
            step_num = step['step']
            think, intended_act = parse_model_response(step['model_response'])
            actual_act = step['action_taken']
            obs = step['next_observation']
            
            # 核心逻辑：检测静默替换
            is_silently_substituted = intended_act.lower() != actual_act.lower()
            
            # 使用 expander 折叠面板，如果发生替换则默认展开并加上警告表情
            expander_title = f"Step {step_num}: {intended_act}" + (" ⚠️ [动作被替换]" if is_silently_substituted else "")
            
            with st.expander(expander_title, expanded=is_silently_substituted):
                st.markdown(f"**🧠 思考 (Think):** {think}")
                
                # 如果发生动作替换，进行红绿对比高亮
                if is_silently_substituted:
                    st.error("🚨 **触发静默替换 (Silent Substitution)!**")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.info(f"**🤖 AI 试图执行:**\n`{intended_act}`")
                    with col2:
                        st.warning(f"**⚙️ 引擎实际执行:**\n`{actual_act}`")
                    st.markdown(f"> **🌍 环境导致的结果:** `{obs}`")
                    st.markdown("*分析：由于 AI 缺乏错误反馈，它仍以为自己执行了原始指令，导致推理链与物理环境脱节。*")
                else:
                    st.markdown(f"**🤖 动作 (Act):** `{intended_act}`")
                    st.markdown(f"> **🌍 环境反馈 (Obs):** `{obs}`")

# --- 页面 2：V2 vs V3 对比 ---
elif page == "2. 提示词脆弱性：V2 vs V3 对比":
    st.header("2. 提示词脆弱性：V2 与 V3 的确定性分歧")
    st.write("展示仅仅一句话的 Prompt 差异，如何导致 V2 陷入死循环，而 V3 成功完成任务。")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("❌ V2：产生幻觉的循环路径")
        st.error("**错误提示 (Flawed Hint):**\n'Pick up the first item, then search for the second.'")
        st.markdown("在 ALFWorld 中，一旦拿取物品，`take` 动作就会从合法列表中消失。V2 被提示误导，陷入了不断的无效搜索。")
        st.divider()
        # 这里用作示例展示，你可以替换为读取你真实的 V2 txt 日志
        st.markdown("**Step 12 🤖 Act:** `take apple 2 from fridge 1`")
        st.markdown("⚠️ **实际执行:** `examine fridge 1` *(被静默替换)*")
        st.markdown("> *Obs:* `You examine the fridge 1.`")
        
        st.markdown("**Step 13 🤖 Act:** `take apple 2 from fridge 1`")
        st.markdown("⚠️ **实际执行:** `close fridge 1` *(被静默替换)*")
        st.markdown("> *Obs:* `You close the fridge 1.`")
        st.caption("...模型在此陷入确定性死循环，直至超时。")

    with col2:
        st.subheader("✅ V3：修正后的正确路径")
        st.success("**修正提示 (Corrected Hint):**\n'Locate both items first, then pick and place sequentially.'")
        st.markdown("V3 规避了底层环境约束，先完全定位，后依次抓取，成功完成 pick2。")
        st.divider()
        # 这里用作示例展示，你可以替换为读取你真实的 V3 txt/json 日志
        st.markdown("**Step 10 🤖 Act:** `go to countertop 1`")
        st.markdown("> *Obs:* `On the countertop 1, you see an apple 1.`")
        
        st.markdown("**Step 11 🤖 Act:** `go to fridge 1`")
        st.markdown("> *Obs:* `The fridge 1 is open. In it, you see an apple 2.`")
        
        st.markdown("**Step 12 🤖 Act:** `take apple 1 from countertop 1`")
        st.markdown("> *Obs:* `You pick up the apple 1.`")
        st.caption("...模型顺利拿取第一件物品并去放置。")

# --- 页面 3：情节记忆 ---
elif page == "3. 情节记忆日志 (Memory Logs)":
    st.header("3. 跨局情节记忆 (Episodic Memory)")
    st.write("这部分可以加载你的 memory.json，展示 AI 是如何从失败中吸取教训的。")
    #Memory Log
    def load_real_memory(filepath="memory.json"):
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            st.warning(f"找不到文件: {filepath}")
            return {}
            
    real_memory = load_real_memory("memory.json")

