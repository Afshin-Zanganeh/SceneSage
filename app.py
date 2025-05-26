import streamlit as st
import tempfile
import os
from pathlib import Path
import json
from scenesage import detect_scenes, analyze_scene_async, get_llm, format_subrip_time, process_scene_chunks
import pysrt

st.set_page_config(
    page_title="SceneSage - Movie Scene Analyzer",
    page_icon="🎬",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        background-color: #f5f5f5;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        padding: 10px 24px;
        border-radius: 4px;
        border: none;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    .upload-section {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .result-section {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-top: 20px;
    }
    .settings-section {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-top: 20px;
    }
    [data-testid="stHorizontalBlock"] > div {
        padding: 0 10px;
    }
</style>
""", unsafe_allow_html=True)

# Title and description
st.title("🎬 SceneSage - Movie Scene Analyzer")
st.markdown("""
Upload your subtitle file and let AI analyze the scenes for you! 
SceneSage will detect scenes, analyze characters, mood, and cultural references.
""")

# Create three columns for the layout
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    st.markdown("### 📤 Upload Subtitle File")
    uploaded_file = st.file_uploader("Choose an SRT file", type=['srt'])

with col2:
    st.markdown("### ⚙️ Model Settings")
    model = st.selectbox(
        "Select Model",
        ["gpt-3.5-turbo", "gemini-pro"],
        index=0
    )
    temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)
    max_tokens = st.slider("Max Tokens", 100, 4000, 1000, 100)
    top_p = st.slider("Top P", 0.0, 1.0, 0.95, 0.05)
    frequency_penalty = st.slider("Frequency Penalty", -2.0, 2.0, 0.0, 0.1)
    presence_penalty = st.slider("Presence Penalty", -2.0, 2.0, 0.0, 0.1)

with col3:
    st.markdown("### 🎬 Scene Settings")
    min_pause = st.slider("Minimum Pause (seconds)", 1, 10, 4, 1)
    chunk_size = st.slider("Chunk Size (scenes)", 2, 10, 5, 1)
    overlap = st.slider("Scene Overlap", 1, 5, 2, 1)
    st.markdown("""
    <div style='font-size: 0.8em; color: #666;'>
    <b>Chunk Size:</b> Number of scenes to process at once<br>
    <b>Scene Overlap:</b> Number of scenes to overlap between chunks
    </div>
    """, unsafe_allow_html=True)

# Process button
process_button = st.button("🚀 Analyze Scenes", type="primary")

if process_button and uploaded_file is not None:
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.srt') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name

        # Show progress
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Load subtitles
        status_text.text("Loading subtitle file...")
        subtitles = pysrt.open(tmp_file_path)
        progress_bar.progress(20)

        # Initialize LLM with custom settings
        status_text.text("Initializing AI model...")
        llm = get_llm(
            model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty
        )
        progress_bar.progress(40)

        # Detect scenes
        status_text.text("Detecting scenes...")
        scenes = detect_scenes(subtitles, min_pause)
        progress_bar.progress(60)

        # Analyze scenes in chunks
        status_text.text("Analyzing scenes...")
        total_chunks = (len(scenes) + chunk_size - overlap - 1) // (chunk_size - overlap)
        progress_per_chunk = 40 / total_chunks
        
        analyzed_scenes = process_scene_chunks(scenes, llm, chunk_size, overlap)
        progress_bar.progress(100)

        # Clean up
        os.unlink(tmp_file_path)
        status_text.text("Analysis complete! ✅")

        # Display results
        st.markdown("### 💾 Download Results")
        result_json = json.dumps(analyzed_scenes, indent=2)
        st.download_button(
            label="📥 Download Analysis Results",
            data=result_json,
            file_name="scene_analysis.json",
            mime="application/json"
        )
        
        st.markdown("### 📊 Analysis Results")
        for i, scene in enumerate(analyzed_scenes):
            with st.expander(f"Scene {i+1} ({scene['start']} - {scene['end']})"):
                st.markdown(f"**Summary:** {scene['summary']}")
                st.markdown(f"**Characters:** {', '.join(scene['characters'])}")
                st.markdown(f"**Mood:** {scene['mood']}")
                if scene['cultural_refs']:
                    st.markdown(f"**Cultural References:** {', '.join(scene['cultural_refs'])}")
                st.markdown(f"**Transcript:** {scene['transcript']}")

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.error(f"Error type: {type(e)}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")

elif process_button and uploaded_file is None:
    st.warning("Please upload a subtitle file first!")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p>Made with ❤️ using Streamlit and LangChain</p>
</div>
""", unsafe_allow_html=True) 