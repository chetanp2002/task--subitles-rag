import subprocess
import os
import shutil

class VideoService:
    
    def _check_ffmpeg(self):
        """Check if FFmpeg is available"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except:
            return False
    
    def add_subtitles(self, input_path: str, output_path: str, 
                     subtitle_text: str, font_size: int = 24, 
                     position: str = "bottom") -> str:
        """Add subtitles to video with custom styling"""
        
        print(f"🔧 Adding subtitles: {input_path} -> {output_path}")
        
        # Check if FFmpeg is available
        if not self._check_ffmpeg():
            print(" FFmpeg not available - creating placeholder file")
            return self._create_placeholder_file(input_path, output_path, "subtitled")
        
        # Check if input file exists
        if not os.path.exists(input_path):
            error_msg = f"Input video file not found: {input_path}"
            print(error_msg)
            raise Exception(error_msg)
        
        # Rest of FFmpeg implementation...
        # [Keep your existing FFmpeg code here]
        
        return output_path
    
    def trim_silences(self, input_path: str, output_path: str) -> str:
        """Trim silences from video using audio detection"""
        
        print(f"🔧 Trimming silences: {input_path} -> {output_path}")
        
        # Check if FFmpeg is available
        if not self._check_ffmpeg():
            print("⚠️ FFmpeg not available - creating placeholder file")
            return self._create_placeholder_file(input_path, output_path, "trimmed")
        
        if not os.path.exists(input_path):
            error_msg = f"❌ Input video file not found: {input_path}"
            print(error_msg)
            raise Exception(error_msg)
        
        # Rest of FFmpeg implementation...
        # [Keep your existing FFmpeg code here]
        
        return output_path
    
    def _create_placeholder_file(self, input_path: str, output_path: str, operation: str) -> str:
        """Create a placeholder file when FFmpeg is not available"""
        try:
            # Just copy the original file as a placeholder
            shutil.copy2(input_path, output_path)
            print(f"Created placeholder {operation} file: {output_path}")
            print("Note: Install FFmpeg for actual video processing")
            return output_path
        except Exception as e:
            raise Exception(f"Placeholder creation failed: {str(e)}")