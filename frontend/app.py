import streamlit as st
import requests
import uuid
import os
import time

# Page configuration
st.set_page_config(
    page_title="Video Chat Assistant",
    page_icon="🎬",
    layout="wide"
)

# Initialize session state
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "video_file" not in st.session_state:
    st.session_state.video_file = None
if "processed_file" not in st.session_state:
    st.session_state.processed_file = None
if "upload_complete" not in st.session_state:
    st.session_state.upload_complete = False
if "video_cache" not in st.session_state:
    st.session_state.video_cache = {}
if "processing_subtitles" not in st.session_state:
    st.session_state.processing_subtitles = False
if "processing_trim" not in st.session_state:
    st.session_state.processing_trim = False
if "last_action_time" not in st.session_state:
    st.session_state.last_action_time = 0
if "current_subtitle_params" not in st.session_state:
    st.session_state.current_subtitle_params = None

# Backend URL
BACKEND_URL = "http://localhost:8000"

def download_video_bytes(filename):
    """Download video bytes with caching"""
    if not filename:
        return None
    
    # Check cache first
    if filename in st.session_state.video_cache:
        return st.session_state.video_cache[filename]
    
    try:
        download_url = f"{BACKEND_URL}/download/{filename}"
        response = requests.get(download_url, timeout=60)
        if response.status_code == 200:
            # Cache the video data
            st.session_state.video_cache[filename] = response.content
            return response.content
        else:
            st.error(f"Failed to download video: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error getting video: {e}")
        return None

def display_video_with_fallback(filename, label):
    """Display video with proper error handling"""
    if not filename:
        return
    
    try:
        # Try to get video bytes
        video_bytes = download_video_bytes(filename)
        
        if video_bytes:
            st.video(video_bytes)
            if label == "processed":
                st.success(" Processed Video")
            else:
                st.info(" Original Video")
        else:
            st.warning(f" Could not load {label} video")
            st.info("The video file exists but couldn't be loaded for preview")
            
    except Exception as e:
        st.error(f" Error displaying video: {e}")

def can_process():
    """Check if we can process (prevent rapid clicks)"""
    current_time = time.time()
    if current_time - st.session_state.last_action_time < 3:  # 3 second cooldown
        return False
    st.session_state.last_action_time = current_time
    return True

def reset_processing_states():
    """Reset all processing states"""
    st.session_state.processing_subtitles = False
    st.session_state.processing_trim = False

st.title(" Video Chat Assistant with AI")
st.write("Chat with AI and edit your videos with custom subtitles!")

# Sidebar for video operations
with st.sidebar:
    st.header("Video Operations")
    
    # Video upload with better state management
    uploaded_file = st.file_uploader("Upload Video", type=['mp4', 'avi', 'mov', 'mkv'])
    
    if uploaded_file is not None and not st.session_state.upload_complete:
        try:
            with st.spinner(" Uploading video..."):
                # Use requests with file upload properly
                files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                response = requests.post(f"{BACKEND_URL}/upload-video", files=files, timeout=120)
                
                if response.status_code == 200:
                    st.session_state.video_file = response.json()["filename"]
                    st.session_state.upload_complete = True
                    st.session_state.processed_file = None
                    # Clear video cache for new upload
                    st.session_state.video_cache = {}
                    reset_processing_states()
                    st.success(f" Video uploaded: {uploaded_file.name}")
                    st.rerun()
                else:
                    st.error(f" Upload failed: {response.status_code}")
                    
        except Exception as e:
            st.error(f" Upload error: {str(e)}")
    
    # Reset upload state if no file is selected
    if uploaded_file is None and st.session_state.upload_complete:
        st.session_state.upload_complete = False
        st.session_state.video_file = None
        st.session_state.processed_file = None
        st.session_state.video_cache = {}
        reset_processing_states()
    
    # Video editing options
    if st.session_state.video_file and st.session_state.upload_complete:
        st.subheader("Edit Video")
        
        # Subtitle options
        subtitle_text = st.text_input("Subtitle Text", "Hello World")
        font_size = st.slider("Font Size", 16, 48, 24)
        position = st.selectbox("Position", ["bottom", "center"])
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(" Add Subtitles", 
                        use_container_width=True,
                        disabled=st.session_state.processing_subtitles,
                        key="add_subtitles_btn"):
                
                if subtitle_text and can_process():
                    current_params = f"{subtitle_text}_{font_size}_{position}"
                    
                    # Check if we're already processing the same parameters
                    if (st.session_state.current_subtitle_params == current_params and 
                        st.session_state.processed_file):
                        st.info(" Using existing processed video")
                    else:
                        st.session_state.processing_subtitles = True
                        st.session_state.current_subtitle_params = current_params
                        
                        try:
                            with st.spinner("Adding subtitles..."):
                                data = {
                                    "filename": st.session_state.video_file,
                                    "subtitle_text": subtitle_text,
                                    "font_size": font_size,
                                    "position": position
                                }
                                response = requests.post(f"{BACKEND_URL}/add-subtitles", data=data, timeout=120)
                                if response.status_code == 200:
                                    st.success(" " + response.json()["message"])
                                    st.session_state.processed_file = response.json()["processed_file"]
                                    # Clear cache to force reload
                                    st.session_state.video_cache = {}
                                else:
                                    st.error(f" Failed to add subtitles: {response.status_code}")
                        except Exception as e:
                            st.error(f" Error: {str(e)}")
                        finally:
                            st.session_state.processing_subtitles = False
                            st.rerun()
                elif not subtitle_text:
                    st.warning(" Please enter subtitle text")
        
        with col2:
            if st.button(" Trim Silences", 
                        use_container_width=True,
                        disabled=st.session_state.processing_trim,
                        key="trim_silences_btn"):
                if can_process():
                    st.session_state.processing_trim = True
                    try:
                        with st.spinner("Trimming silences..."):
                            data = {"filename": st.session_state.video_file}
                            response = requests.post(f"{BACKEND_URL}/trim-silences", data=data, timeout=120)
                            if response.status_code == 200:
                                st.success(" " + response.json()["message"])
                                st.session_state.processed_file = response.json()["processed_file"]
                                # Clear cache to force reload
                                st.session_state.video_cache = {}
                            else:
                                st.error(f" Failed to trim silences: {response.status_code}")
                    except Exception as e:
                        st.error(f" Error: {str(e)}")
                    finally:
                        st.session_state.processing_trim = False
                        st.rerun()
        
        # Show processing status
        if st.session_state.processing_subtitles:
            st.info(" Processing subtitles...")
        if st.session_state.processing_trim:
            st.info(" Trimming silences...")
        
        # Download processed video
        if st.session_state.processed_file and not st.session_state.processing_subtitles and not st.session_state.processing_trim:
            try:
                download_url = f"{BACKEND_URL}/download/{st.session_state.processed_file}"
                st.download_button(
                    " Download Processed Video",
                    data=requests.get(download_url, timeout=60).content,
                    file_name=st.session_state.processed_file,
                    mime="video/mp4",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f" Download error: {e}")

# Main layout with columns
col1, col2 = st.columns([2, 1])

with col1:
    st.header(" Chat with AI")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message("user" if message["role"] == "user" else "assistant"):
            st.markdown(message["content"])

with col2:
    st.header(" Video Preview")
    
    # Display appropriate video with proper error handling
    if st.session_state.processed_file:
        # Show processed video
        display_video_with_fallback(st.session_state.processed_file, "processed")
            
    elif st.session_state.video_file and st.session_state.upload_complete:
        # Show original video
        display_video_with_fallback(st.session_state.video_file, "original")
    else:
        st.info(" Upload a video to see preview and editing options")
        
        # Placeholder for video upload prompt
        st.write("""
        **Supported formats:** MP4, AVI, MOV, MKV
        
        After uploading, you can:
        - Add custom subtitles
        - Trim silences  
        - Chat with AI about video editing
        """)

# CHAT INPUT
if prompt := st.chat_input("Ask about video editing, subtitles, or anything else..."):
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Send to backend
    with st.chat_message("assistant"):
        with st.spinner(" Thinking..."):
            try:
                data = {
                    "message": prompt,
                    "user_id": st.session_state.user_id
                }
                response = requests.post(f"{BACKEND_URL}/chat", data=data, timeout=60)
                
                if response.status_code == 200:
                    ai_response = response.json()["response"]
                    st.markdown(ai_response)
                    st.session_state.messages.append({"role": "assistant", "content": ai_response})
                else:
                    error_msg = f" Error from AI service (Status: {response.status_code})"
                    st.markdown(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
                    
            except Exception as e:
                error_msg = f" Connection error: {e}"
                st.markdown(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

# Footer
st.markdown("---")
st.markdown("###  Built with:")
st.markdown("""
- **Backend:** FastAPI, LangGraph, Groq LLM
- **Frontend:** Streamlit  
- **Video Processing:** FFmpeg
- **Database:** SQLite for conversation storage
""")

# Clear chat button
if st.sidebar.button(" Clear Chat History", use_container_width=True, key="clear_chat_unique"):
    st.session_state.messages = []
    st.rerun()

# Reset everything button
if st.sidebar.button(" Reset All", use_container_width=True, key="reset_all_unique"):
    st.session_state.upload_complete = False
    st.session_state.video_file = None
    st.session_state.processed_file = None
    st.session_state.messages = []
    st.session_state.video_cache = {}
    st.session_state.current_subtitle_params = None
    reset_processing_states()
    st.rerun()

# Refresh video preview button
if st.sidebar.button(" Refresh Video Preview", use_container_width=True, key="refresh_preview_unique"):
    st.session_state.video_cache = {}
    st.rerun()