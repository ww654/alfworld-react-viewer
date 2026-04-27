import streamlit as st
import json
import os

# --- Page Configuration ---
st.set_page_config(page_title="ALFWorld ReAct Agent Viewer", layout="wide")
st.title("Revisiting ReAct on ALFWorld: Trajectory & Memory Viewer")
st.markdown("Dive deep into the failure modes, ablation studies, and episodic memory of the DeepSeek ReAct Agent.")

# --- Data Loading and Parsing Functions ---
@st.cache_data
def load_json_data(filepath):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def parse_model_response(response_text):
    """Parse model output to separate Think and Act."""
    think, act = response_text, ""
    if "Act:" in response_text:
        parts = response_text.split("Act:")
        think = parts[0].replace("Think:", "").strip()
        act = parts[1].strip()
    return think, act

# Load actual failure data
all_failures = load_json_data("all_failures.json")

# --- Sidebar Navigation ---
st.sidebar.header("Navigation")
page = st.sidebar.radio("Select a View:", [
    "1. Failure Modes Analysis", 
    "2. Prompt Vulnerability: V2 vs V3", 
    "3. Episodic Memory Logs"
])

# --- Page 1: Failure Modes Analysis ---
if page == "1. Failure Modes Analysis":
    st.header("1. Micro-Trajectory Viewer (Failure Modes)")
    st.write("Step-by-step replay of failed episodes, automatically detecting deviations between the model's intended action and the environment's actual execution.")
    
    # Convert JSON data to dictionary for easy lookup by game_id
    failures_dict = {f"Game {game['game_id']} ({game['task_type']})": game for game in all_failures}
    
    if not failures_dict:
        st.warning("Please ensure all_failures.json is in the same directory as this script.")
    else:
        selected_game_key = st.selectbox("Select a failed episode to replay:", list(failures_dict.keys()))
        game_data = failures_dict[selected_game_key]
        
        st.subheader(f"Task Objective: {game_data['initial_obs'].split('Your task is to:')[-1].strip()}")
        st.markdown(f"**Total Steps:** {game_data['total_steps']} | **Final Result:** {game_data['result']}")
        
        # Render micro-trajectory for each step
        for step in game_data['steps']:
            step_num = step['step']
            think, intended_act = parse_model_response(step['model_response'])
            actual_act = step['action_taken']
            obs = step['next_observation']
            
            # Core logic: Detect silent substitution
            is_silently_substituted = intended_act.lower() != actual_act.lower()
            
            # Use expander, default to expanded and add warning emoji if substitution occurred
            expander_title = f"Step {step_num}: {intended_act}" + (" ⚠️ [Action Replaced]" if is_silently_substituted else "")
            
            with st.expander(expander_title, expanded=is_silently_substituted):
                st.markdown(f"**🧠 Think:** {think}")
                
                # Highlight with red/green columns if action substitution occurred
                if is_silently_substituted:
                    st.error("🚨 **Silent Substitution Triggered!**")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.info(f"**🤖 AI Intended Act:**\n`{intended_act}`")
                    with col2:
                        st.warning(f"**⚙️ Engine Actually Executed:**\n`{actual_act}`")
                    st.markdown(f"> **🌍 Environmental Observation:** `{obs}`")
                    st.markdown("*Analysis: Lacking error feedback, the AI assumes its original command was executed, causing its reasoning chain to disconnect from the physical environment.*")
                else:
                    st.markdown(f"**🤖 Act:** `{intended_act}`")
                    st.markdown(f"> **🌍 Env Observation:** `{obs}`")

# --- Page 2: V2 vs V3 Comparison ---
elif page == "2. Prompt Vulnerability: V2 vs V3":
    st.header("2. Prompt Vulnerability: Deterministic Divergence in V2 vs V3")
    st.write("Demonstrating how a single sentence prompt difference causes V2 to fall into an infinite loop, while V3 successfully completes the task.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("❌ V2: Hallucinated Loop Path")
        st.error("**Flawed Hint:**\n'Pick up the first item, then search for the second.'")
        st.markdown("In ALFWorld, once an item is held, the `take` action disappears from the valid list. Misled by the hint, V2 falls into endless invalid searching.")
        st.divider()
        # Placeholder display (can be replaced with actual V2 txt logs)
        st.markdown("**Step 12 🤖 Act:** `take apple 2 from fridge 1`")
        st.markdown("⚠️ **Actually Executed:** `examine fridge 1` *(Silently Substituted)*")
        st.markdown("> *Obs:* `You examine the fridge 1.`")
        
        st.markdown("**Step 13 🤖 Act:** `take apple 2 from fridge 1`")
        st.markdown("⚠️ **Actually Executed:** `close fridge 1` *(Silently Substituted)*")
        st.markdown("> *Obs:* `You close the fridge 1.`")
        st.caption("...The model enters a deterministic infinite loop here until timeout.")

    with col2:
        st.subheader("✅ V3: Corrected Successful Path")
        st.success("**Corrected Hint:**\n'Locate both items first, then pick and place sequentially.'")
        st.markdown("V3 avoids the underlying environmental constraints by fully locating both items first, then picking them sequentially, successfully completing pick2.")
        st.divider()
        # Placeholder display (can be replaced with actual V3 txt/json logs)
        st.markdown("**Step 10 🤖 Act:** `go to countertop 1`")
        st.markdown("> *Obs:* `On the countertop 1, you see an apple 1.`")
        
        st.markdown("**Step 11 🤖 Act:** `go to fridge 1`")
        st.markdown("> *Obs:* `The fridge 1 is open. In it, you see an apple 2.`")
        
        st.markdown("**Step 12 🤖 Act:** `take apple 1 from countertop 1`")
        st.markdown("> *Obs:* `You pick up the apple 1.`")
        st.caption("...The model successfully picks up the first item and proceeds to place it.")

# --- Page 3: Episodic Memory ---
elif page == "3. Episodic Memory Logs":
    st.header("3. Cross-Episode Episodic Memory")
    st.write("This section loads memory.json, demonstrating how the AI learns from failures across different episodes.")
    
    # Define read function
    def load_real_memory(filepath="memory.json"):
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            st.warning(f"File not found: {filepath}. Please check the path.")
            return {}

    # Load real data
    real_memory = load_real_memory("memory.json")

    # Render the dropdown and cards only if data is successfully read (prevents errors)
    if real_memory:
        # Dropdown: Select task type
        task_type = st.selectbox("Select Task Type:", list(real_memory.keys()))
        
        st.subheader(f"Lessons for '{task_type}'")
        
        # Iterate and display specific lessons using green success boxes
        for i, lesson in enumerate(real_memory[task_type]):
            st.success(f"**Lesson {i+1}:** {lesson}")
            
        st.divider()
        st.write("Raw JSON Data:")
        # Display raw JSON structure at the bottom
        st.json(real_memory)
