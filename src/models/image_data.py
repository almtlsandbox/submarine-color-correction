"""
Image data model and utilities.
Handles image loading, metadata, and state management.
"""
from dataclasses import dataclass
from typing import Optional, Tuple, List
import cv2
import numpy as np
from PIL import Image
import os


@dataclass
class ImageData:
    """Represents an image with its metadata and processing state."""
    
    file_path: str
    original_bgr: Optional[np.ndarray] = None  # Original image in BGR format
    original_rgb: Optional[np.ndarray] = None  # Original image in RGB format for display
    corrected_rgb: Optional[np.ndarray] = None  # Processed image in RGB format
    width: int = 0
    height: int = 0
    channels: int = 3
    file_size: int = 0
    format: str = ""
    
    def __post_init__(self):
        """Load image data after initialization."""
        if self.file_path and os.path.exists(self.file_path):
            self.load()
    
    def load(self) -> bool:
        """Load image from file path."""
        try:
            # Load with OpenCV (BGR format)
            self.original_bgr = cv2.imread(self.file_path)
            if self.original_bgr is None:
                return False
            
            # Convert to RGB for display
            self.original_rgb = cv2.cvtColor(self.original_bgr, cv2.COLOR_BGR2RGB)
            
            # Extract metadata
            self.height, self.width, self.channels = self.original_bgr.shape
            self.file_size = os.path.getsize(self.file_path)
            self.format = os.path.splitext(self.file_path)[1].upper()[1:]  # Remove dot
            
            return True
            
        except Exception as e:
            print(f"Error loading image {self.file_path}: {e}")
            return False
    
    def get_display_image(self, apply_rotation: int = 0) -> Optional[np.ndarray]:
        """Get the image for display (RGB format) with optional rotation."""
        if self.corrected_rgb is not None:
            image = self.corrected_rgb.copy()
        elif self.original_rgb is not None:
            image = self.original_rgb.copy()
        else:
            return None
        
        # Apply rotation if specified
        if apply_rotation != 0:
            if apply_rotation == 90:
                image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
            elif apply_rotation == 180:
                image = cv2.rotate(image, cv2.ROTATE_180)
            elif apply_rotation == 270:
                image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        
        return image
    
    def get_processing_image(self) -> Optional[np.ndarray]:
        """Get the image for processing (BGR format)."""
        return self.original_bgr
    
    def set_corrected_result(self, corrected_bgr: np.ndarray) -> None:
        """Set the processed image result."""
        if corrected_bgr is not None:
            self.corrected_rgb = cv2.cvtColor(corrected_bgr, cv2.COLOR_BGR2RGB)
    
    def has_correction(self) -> bool:
        """Check if image has been processed."""
        return self.corrected_rgb is not None
    
    def clear_correction(self) -> None:
        """Clear the processed result."""
        self.corrected_rgb = None
    
    def get_filename(self) -> str:
        """Get just the filename without path."""
        return os.path.basename(self.file_path)
    
    def get_info_string(self) -> str:
        """Get formatted info string for display."""
        size_mb = self.file_size / (1024 * 1024)
        return f"{self.get_filename()} | {self.width}×{self.height} | {self.format} | {size_mb:.1f}MB"
    
    def save_corrected(self, output_path: str, apply_rotation: int = 0) -> bool:
        """Save the corrected image with optional rotation."""
        if not self.has_correction() or self.corrected_rgb is None:
            return False
        
        try:
            # Get corrected image in BGR format for saving
            image_to_save = cv2.cvtColor(self.corrected_rgb, cv2.COLOR_RGB2BGR)
            
            # Apply rotation if specified
            if apply_rotation != 0:
                if apply_rotation == 90:
                    image_to_save = cv2.rotate(image_to_save, cv2.ROTATE_90_COUNTERCLOCKWISE)
                elif apply_rotation == 180:
                    image_to_save = cv2.rotate(image_to_save, cv2.ROTATE_180)
                elif apply_rotation == 270:
                    image_to_save = cv2.rotate(image_to_save, cv2.ROTATE_90_CLOCKWISE)
            
            cv2.imwrite(output_path, image_to_save)
            return True
            
        except Exception as e:
            print(f"Error saving image: {e}")
            return False


class ImageCollection:
    """Manages a collection of images."""
    
    def __init__(self):
        self.images: List[ImageData] = []
        self.current_index: int = 0
        
    def load_from_folder(self, folder_path: str) -> int:
        """Load all supported images from a folder."""
        image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tga', '.webp')
        self.images.clear()
        self.current_index = 0
        
        if not os.path.exists(folder_path):
            return 0
            
        for filename in os.listdir(folder_path):
            if filename.lower().endswith(image_extensions):
                file_path = os.path.join(folder_path, filename)
                image_data = ImageData(file_path)
                if image_data.original_rgb is not None:  # Successfully loaded
                    self.images.append(image_data)
        
        return len(self.images)
    
    def get_current_image(self) -> Optional[ImageData]:
        """Get the currently selected image."""
        if 0 <= self.current_index < len(self.images):
            return self.images[self.current_index]
        return None
    
    def next_image(self) -> Optional[ImageData]:
        """Move to next image."""
        if self.images:
            self.current_index = (self.current_index + 1) % len(self.images)
            return self.get_current_image()
        return None
    
    def prev_image(self) -> Optional[ImageData]:
        """Move to previous image."""
        if self.images:
            self.current_index = (self.current_index - 1) % len(self.images)
            return self.get_current_image()
        return None
    
    def get_navigation_info(self) -> Tuple[int, int]:
        """Get current position info (current, total)."""
        return (self.current_index + 1, len(self.images))
    
    def is_empty(self) -> bool:
        """Check if collection is empty."""
        return len(self.images) == 0
