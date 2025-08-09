"""
Video data model and utilities.
Handles video loading, frame navigation, and state management.
"""
from dataclasses import dataclass
from typing import Optional, Callable
import cv2
import numpy as np
import os
import threading


@dataclass
class VideoData:
    """Represents a video with its metadata and processing state."""
    
    file_path: str
    video_cap: Optional[cv2.VideoCapture] = None
    total_frames: int = 0
    fps: float = 30.0
    width: int = 0
    height: int = 0
    current_frame_number: int = 0
    current_frame_bgr: Optional[np.ndarray] = None
    current_frame_rgb: Optional[np.ndarray] = None
    corrected_frame_rgb: Optional[np.ndarray] = None
    is_playing: bool = False
    
    def __post_init__(self):
        """Load video data after initialization."""
        if self.file_path and os.path.exists(self.file_path):
            self.load()
    
    def load(self) -> bool:
        """Load video from file path."""
        try:
            self.video_cap = cv2.VideoCapture(self.file_path)
            if not self.video_cap.isOpened():
                return False
            
            # Extract metadata
            self.total_frames = int(self.video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.video_cap.get(cv2.CAP_PROP_FPS)
            self.width = int(self.video_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.current_frame_number = 0
            
            # Load first frame
            self.load_frame(0)
            
            return True
            
        except Exception as e:
            print(f"Error loading video {self.file_path}: {e}")
            return False
    
    def load_frame(self, frame_number: int) -> bool:
        """Load a specific frame."""
        if not self.video_cap or not self.video_cap.isOpened():
            return False
        
        try:
            # Set frame position
            self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = self.video_cap.read()
            
            if ret:
                self.current_frame_number = frame_number
                self.current_frame_bgr = frame.copy()
                self.current_frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # Clear previous correction when loading new frame
                self.corrected_frame_rgb = None
                return True
            
            return False
            
        except Exception as e:
            print(f"Error loading frame {frame_number}: {e}")
            return False
    
    def get_current_frame_for_display(self, apply_rotation: int = 0) -> Optional[np.ndarray]:
        """Get current frame for display (RGB format) with optional rotation."""
        if self.corrected_frame_rgb is not None:
            frame = self.corrected_frame_rgb.copy()
        elif self.current_frame_rgb is not None:
            frame = self.current_frame_rgb.copy()
        else:
            return None
        
        # Apply rotation if specified
        if apply_rotation != 0:
            if apply_rotation == 90:
                frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
            elif apply_rotation == 180:
                frame = cv2.rotate(frame, cv2.ROTATE_180)
            elif apply_rotation == 270:
                frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        
        return frame
    
    def get_current_frame_for_processing(self) -> Optional[np.ndarray]:
        """Get current frame for processing (BGR format)."""
        return self.current_frame_bgr
    
    def set_corrected_frame(self, corrected_bgr: np.ndarray) -> None:
        """Set the processed frame result."""
        if corrected_bgr is not None:
            self.corrected_frame_rgb = cv2.cvtColor(corrected_bgr, cv2.COLOR_BGR2RGB)
    
    def has_correction(self) -> bool:
        """Check if current frame has been processed."""
        return self.corrected_frame_rgb is not None
    
    def clear_correction(self) -> None:
        """Clear the processed result for current frame."""
        self.corrected_frame_rgb = None
    
    def next_frame(self) -> bool:
        """Move to next frame."""
        if self.current_frame_number < self.total_frames - 1:
            return self.load_frame(self.current_frame_number + 1)
        return False
    
    def prev_frame(self) -> bool:
        """Move to previous frame."""
        if self.current_frame_number > 0:
            return self.load_frame(self.current_frame_number - 1)
        return False
    
    def jump_to_frame(self, frame_number: int) -> bool:
        """Jump to specific frame."""
        frame_number = max(0, min(self.total_frames - 1, frame_number))
        return self.load_frame(frame_number)
    
    def get_filename(self) -> str:
        """Get just the filename without path."""
        return os.path.basename(self.file_path)
    
    def get_info_string(self) -> str:
        """Get formatted info string for display."""
        duration = self.total_frames / self.fps if self.fps > 0 else 0
        size_mb = os.path.getsize(self.file_path) / (1024 * 1024) if os.path.exists(self.file_path) else 0
        return f"{self.get_filename()} | {self.width}×{self.height} | {duration:.1f}s | {size_mb:.1f}MB"
    
    def get_navigation_info(self) -> tuple[int, int]:
        """Get current frame position info (current, total)."""
        return (self.current_frame_number + 1, self.total_frames)
    
    def cleanup(self):
        """Clean up video resources."""
        if self.video_cap:
            self.video_cap.release()
            self.video_cap = None


class VideoProcessor:
    """Processes full videos with progress tracking."""
    
    def __init__(self, image_processor):
        self.image_processor = image_processor
    
    def process_video(self, video_data: VideoData, params, progress_callback: Optional[Callable] = None) -> str:
        """
        Process full video with current parameters.
        
        Args:
            video_data: VideoData instance
            params: ProcessingParameters
            progress_callback: Optional callback function(frame_count, total_frames, preview_frame) -> bool
            
        Returns:
            Output video file path
        """
        if not video_data.video_cap or not video_data.video_cap.isOpened():
            raise Exception("Video not loaded")
        
        # Create output path
        base_name = os.path.splitext(os.path.basename(video_data.file_path))[0]
        output_path = os.path.join(os.path.dirname(video_data.file_path), f"{base_name}_corrected.mp4")
        
        # Create video writer
        fourcc = cv2.VideoWriter.fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, video_data.fps, (video_data.width, video_data.height))
        
        try:
            # Reset to beginning
            video_data.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
            frame_count = 0
            while True:
                ret, frame = video_data.video_cap.read()
                if not ret:
                    break
                
                # Process frame
                corrected_frame = self.image_processor.process_image(frame, params)
                out.write(corrected_frame)
                
                frame_count += 1
                
                # Update progress
                if progress_callback:
                    should_continue = progress_callback(frame_count, video_data.total_frames, corrected_frame)
                    if not should_continue:
                        break
                        
        finally:
            out.release()
        
        return output_path
