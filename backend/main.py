from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import uuid
import sqlite3
from datetime import datetime
import hashlib
import time
from pathlib import Path

# Import services
try:
    from services.llm_service import LLMService
    from services.rag_service import RAGService
    from services.video_service import VideoService
    from agents.langgraph_agent import LangGraphAgent
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure services and agents directories exist with __init__.py files")
    raise

app = FastAPI(title="Video Chat API", version="1.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
llm_service = LLMService()
rag_service = RAGService()
video_service = VideoService()
langgraph_agent = LangGraphAgent(llm_service, rag_service)

# Ensure directories exist
os.makedirs("data/videos", exist_ok=True)
os.makedirs("data/processed", exist_ok=True)
os.makedirs("data/vector_store", exist_ok=True)

# Track processing requests to prevent duplicates
processing_cache = {}

def get_request_hash(filename: str, subtitle_text: str, font_size: int, position: str) -> str:
    """Generate unique hash for processing requests"""
    params = f"{filename}_{subtitle_text}_{font_size}_{position}"
    return hashlib.md5(params.encode()).hexdigest()

def get_processed_filename(filename: str, subtitle_text: str, font_size: int, position: str) -> str:
    """Generate consistent processed filename based on parameters"""
    param_hash = hashlib.md5(f"{subtitle_text}_{font_size}_{position}".encode()).hexdigest()[:8]
    return f"subtitled_{param_hash}_{filename}"

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    rag_service.init_database()
    print(" Backend services initialized successfully")

@app.get("/")
async def root():
    return {"message": "Video Chat API is running"}

@app.post("/chat")
async def chat(message: str = Form(...), user_id: str = Form(...)):
    """Chat endpoint using LangGraph orchestration"""
    try:
        response = await langgraph_agent.process_message(user_id, message)
        return {"response": response}
    except Exception as e:
        error_msg = f"Error in chat: {str(e)}"
        print(f" {error_msg}")
        return {"response": error_msg}

@app.post("/upload-video")
async def upload_video(file: UploadFile = File(...)):
    """Upload video file with better timeout handling"""
    try:
        file_extension = file.filename.split('.')[-1]
        filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = f"data/videos/{filename}"
        
        # Use chunked writing to handle large files
        with open(file_path, "wb") as buffer:
            while True:
                chunk = await file.read(8192)  # 8KB chunks
                if not chunk:
                    break
                buffer.write(chunk)
        
        file_size = os.path.getsize(file_path)
        print(f" Video uploaded: {filename} ({file_size} bytes)")
        return {"filename": filename, "message": "Video uploaded successfully"}
    except Exception as e:
        error_msg = f"Upload error: {str(e)}"
        print(f" {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/add-subtitles")
async def add_subtitles(
    filename: str = Form(...),
    subtitle_text: str = Form(""),
    font_size: int = Form(24),
    position: str = Form("bottom")
):
    """Add subtitles to video with existing file check"""
    try:
        input_path = f"data/videos/{filename}"
        
        # Generate consistent output filename
        output_filename = get_processed_filename(filename, subtitle_text, font_size, position)
        output_path = f"data/processed/{output_filename}"
        
        # Check if processed file already exists
        if os.path.exists(output_path):
            print(f" Using existing processed file: {output_filename}")
            return {
                "processed_file": output_filename, 
                "message": "Subtitles already added (using cached version)"
            }
        
        # Check if input file exists
        if not os.path.exists(input_path):
            print(f" Input file not found: {input_path}")
            raise HTTPException(status_code=404, detail="Original video file not found")
        
        print(f" Starting subtitle processing for: {filename}")
        print(f" Subtitle: '{subtitle_text}', Size: {font_size}, Position: {position}")
        print(f" Output: {output_filename}")
        
        # Process the video
        result_path = video_service.add_subtitles(
            input_path, output_path, subtitle_text, font_size, position
        )
        
        # Verify the file was created
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f" Subtitle processing completed: {output_filename} ({file_size} bytes)")
            return {
                "processed_file": output_filename, 
                "message": "Subtitles added successfully"
            }
        else:
            print(f" Output file not created: {output_path}")
            raise HTTPException(status_code=500, detail="Failed to create processed video")
        
    except Exception as e:
        error_msg = f"Subtitle error: {str(e)}"
        print(f" {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/trim-silences")
async def trim_silences(filename: str = Form(...)):
    """Trim silences from video"""
    try:
        input_path = f"data/videos/{filename}"
        output_filename = f"trimmed_{filename}"
        output_path = f"data/processed/{output_filename}"
        
        # Check if processed file already exists
        if os.path.exists(output_path):
            print(f" Using existing trimmed file: {output_filename}")
            return {
                "processed_file": output_filename, 
                "message": "Silences already trimmed (using cached version)"
            }
        
        print(f" Starting silence trimming for: {filename}")
        result_path = video_service.trim_silences(input_path, output_path)
        
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f" Silence trimming completed: {output_filename} ({file_size} bytes)")
            return {
                "processed_file": output_filename, 
                "message": "Silences trimmed successfully"
            }
        else:
            print(f" Output file not created: {output_path}")
            raise HTTPException(status_code=500, detail="Failed to create trimmed video")
            
    except Exception as e:
        error_msg = f"Silence trimming error: {str(e)}"
        print(f" {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download processed video file"""
    try:
        # Check processed files first
        file_path = f"data/processed/{filename}"
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f" Serving processed file: {filename} ({file_size} bytes)")
            return FileResponse(file_path, media_type='video/mp4', filename=filename)
        
        # Check original videos
        file_path = f"data/videos/{filename}"
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f" Serving original file: {filename} ({file_size} bytes)")
            return FileResponse(file_path, media_type='video/mp4', filename=filename)
        
        print(f" File not found: {filename}")
        raise HTTPException(status_code=404, detail="File not found")
        
    except Exception as e:
        error_msg = f"Download error: {str(e)}"
        print(f" {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/check-file/{filename}")
async def check_file(filename: str):
    """Check if file exists and return info"""
    file_path = f"data/processed/{filename}"
    if os.path.exists(file_path):
        return {
            "exists": True,
            "size": os.path.getsize(file_path),
            "path": file_path
        }
    else:
        return {"exists": False}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            response = await langgraph_agent.process_message(client_id, data)
            await websocket.send_text(response)
    except Exception as e:
        print(f"WebSocket error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        timeout_keep_alive=60
    )