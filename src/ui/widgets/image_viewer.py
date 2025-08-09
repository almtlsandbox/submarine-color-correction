"""
Advanced image viewer widget supporting both static images and video frames.
Provides pan, zoom, rotation, and overlay capabilities.
"""
import tkinter as tk
from tkinter import ttk
import numpy as np
from PIL import Image, ImageTk
from typing import Optional, Tuple, Dict, Any
import threading

from services.logger_service import get_logger


class ImageViewer:
    """Advanced image viewer with pan, zoom, and overlay support."""
    
    def __init__(self, parent: tk.Widget, view_mode_callback=None):
        self.parent = parent
        self.logger = get_logger('image_viewer')
        self.view_mode_callback = view_mode_callback
        
        # Current image state
        self.original_image: Optional[np.ndarray] = None
        self.processed_image: Optional[np.ndarray] = None
        self.display_image: Optional[Image.Image] = None
        self.photo_image: Optional[ImageTk.PhotoImage] = None
        
        # View state
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.rotation = 0
        self.show_original = False
        self.show_processed = True
        self.show_split_view = False
        self.split_position = 0.5  # Split position as percentage (0.0 to 1.0)
        
        # Panning state
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.is_panning = False
        
        # Canvas dimensions
        self.canvas_width = 800
        self.canvas_height = 600
        
        self.create_ui()
        
    def create_ui(self):
        """Create the image viewer interface."""
        # Main container
        container = tk.Frame(self.parent)
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # View controls frame
        controls_frame = tk.Frame(container)
        controls_frame.pack(fill=tk.X, pady=(0, 5))
        
        # View mode selection
        view_frame = tk.LabelFrame(controls_frame, text="View Mode", padx=5, pady=5)
        view_frame.pack(side=tk.LEFT, padx=(0, 5))
        
        self.view_var = tk.StringVar(value="processed")
        tk.Radiobutton(view_frame, text="Original", variable=self.view_var,
                      value="original", command=self._update_view_mode).pack(side=tk.LEFT)
        tk.Radiobutton(view_frame, text="Processed", variable=self.view_var,
                      value="processed", command=self._update_view_mode).pack(side=tk.LEFT)
        tk.Radiobutton(view_frame, text="Split View", variable=self.view_var,
                      value="split", command=self._update_view_mode).pack(side=tk.LEFT)
        
        # Overlay controls
        overlay_frame = tk.LabelFrame(controls_frame, text="Overlays", padx=5, pady=5)
        overlay_frame.pack(side=tk.LEFT, padx=5)
        
        self.show_grid_var = tk.BooleanVar()
        tk.Checkbutton(overlay_frame, text="Grid", 
                      variable=self.show_grid_var,
                      command=self._update_overlays).pack(side=tk.LEFT)
        
        self.show_info_var = tk.BooleanVar(value=True)
        tk.Checkbutton(overlay_frame, text="Info", 
                      variable=self.show_info_var,
                      command=self._update_overlays).pack(side=tk.LEFT)
        
        # Zoom info
        zoom_frame = tk.Frame(controls_frame)
        zoom_frame.pack(side=tk.RIGHT)
        
        tk.Label(zoom_frame, text="Zoom:").pack(side=tk.LEFT)
        self.zoom_label = tk.Label(zoom_frame, text="100%", font=('Arial', 9, 'bold'))
        self.zoom_label.pack(side=tk.LEFT, padx=5)
        
        # Canvas with scrollbars
        canvas_frame = tk.Frame(container)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create canvas with scrollbars
        self.canvas = tk.Canvas(canvas_frame, bg='gray20',
                               width=self.canvas_width, height=self.canvas_height)
        
        # Scrollbars
        h_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        
        self.canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
        
        # Grid layout
        self.canvas.grid(row=0, column=0, sticky='nsew')
        h_scroll.grid(row=1, column=0, sticky='ew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        
        canvas_frame.rowconfigure(0, weight=1)
        canvas_frame.columnconfigure(0, weight=1)
        
        # Bind events
        self.canvas.bind('<Button-1>', self._start_pan)
        self.canvas.bind('<B1-Motion>', self._pan_image)
        self.canvas.bind('<ButtonRelease-1>', self._end_pan)
        self.canvas.bind('<MouseWheel>', self._mouse_wheel)
        self.canvas.bind('<Double-Button-1>', self._double_click)
        
        # Status info
        self.info_text = self.canvas.create_text(10, 10, anchor='nw', fill='white',
                                                font=('Arial', 9), text="No image loaded")
        
        # Split view slider at bottom (full width)
        self.split_frame = tk.Frame(container)
        
        # Split controls with full width
        split_control_frame = tk.Frame(self.split_frame)
        split_control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(split_control_frame, text="Split Position:", font=('Arial', 9, 'bold')).pack(side=tk.LEFT)
        
        self.split_var = tk.DoubleVar(value=50.0)
        self.split_slider = tk.Scale(split_control_frame, from_=0, to=100, 
                                    orient=tk.HORIZONTAL, variable=self.split_var,
                                    command=self._on_split_change, length=300, 
                                    showvalue=True, resolution=1)
        self.split_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 10))
        
        tk.Label(split_control_frame, text="%").pack(side=tk.RIGHT)
        
        # Initially hide split controls
        # Don't pack the split_frame yet - will be shown when split view is selected
    
    def load_image(self, image: np.ndarray, is_processed: bool = False):
        """Load an image into the viewer."""
        if image is None:
            self.logger.warning("Attempted to load None image")
            return
        
        if is_processed:
            self.processed_image = image.copy()
        else:
            self.original_image = image.copy()
        
        # If this is the first image or we don't have both versions
        if not hasattr(self, 'original_image') or self.original_image is None:
            if not is_processed:
                self.processed_image = image.copy()  # Use as both original and processed
        
        self._update_display()
        self.logger.info(f"Loaded {'processed' if is_processed else 'original'} image: {image.shape}")
    
    def update_processed_image(self, image: np.ndarray):
        """Update only the processed image."""
        self.processed_image = image.copy()
        if self.show_processed or self.show_split_view:
            self._update_display()

    def clear_processed_image_and_adjust_view(self):
        """
        Clear the processed image and adjust view mode when loading a new image.
        - If currently showing "corrected" view, switch to "original" view
        - Keep "split" view if currently selected
        """
        # Clear the processed image
        self.processed_image = None
        
        # Adjust view mode based on current selection
        if self.show_processed:  # Currently showing "corrected" view
            # Switch to "original" view
            self.view_var.set("original")
            self._update_view_mode()  # This will update the show_* flags
            
        # If split view is selected, keep it (but processed side will be empty until new processing)
        # If original view is selected, keep it as is
        
        # Update display to reflect changes
        self._update_display()

    def set_zoom(self, zoom_level: float):
        """Set zoom level directly."""
        self.zoom_level = max(0.1, min(5.0, zoom_level))
        self._update_display()
        self._update_zoom_label()
    
    def zoom_in(self, factor: float = 1.25):
        """Zoom in by factor."""
        self.set_zoom(self.zoom_level * factor)
    
    def zoom_out(self, factor: float = 0.8):
        """Zoom out by factor."""
        self.set_zoom(self.zoom_level * factor)
    
    def fit_to_window(self):
        """Fit image to window."""
        img = self._get_current_image()
        if img is None:
            return
        
        img_height, img_width = img.shape[:2]
        
        # Calculate zoom to fit
        zoom_w = self.canvas_width / img_width
        zoom_h = self.canvas_height / img_height
        self.zoom_level = min(zoom_w, zoom_h)
        
        # Center the image
        self.pan_x = 0
        self.pan_y = 0
        
        self._update_display()
        self._update_zoom_label()
    
    def reset_view(self):
        """Reset view to 100% zoom, centered."""
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self._update_display()
        self._update_zoom_label()
    
    def rotate_left(self):
        """Rotate image 90 degrees counter-clockwise."""
        self.rotation = (self.rotation - 90) % 360
        self._update_display()
    
    def rotate_right(self):
        """Rotate image 90 degrees clockwise."""
        self.rotation = (self.rotation + 90) % 360
        self._update_display()
    
    def _get_current_image(self) -> Optional[np.ndarray]:
        """Get the currently active image based on view mode."""
        if self.show_original and self.original_image is not None:
            return self.original_image
        elif self.processed_image is not None:
            return self.processed_image
        elif self.original_image is not None:
            return self.original_image
        return None
    
    def _update_view_mode(self):
        """Update view mode based on radio button selection."""
        mode = self.view_var.get()
        
        self.show_original = (mode == "original")
        self.show_processed = (mode == "processed")
        self.show_split_view = (mode == "split")
        
        # Call callback if provided
        if self.view_mode_callback:
            self.view_mode_callback()
        
        # Show/hide split controls based on mode
        if mode == "split":
            self.split_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
        else:
            self.split_frame.pack_forget()
        
        self._update_display()
        self.logger.info(f"View mode changed to: {mode}")
    
    def _update_overlays(self):
        """Update overlay visibility."""
        self._update_display()
    
    def _update_display(self):
        """Update the canvas display with current image and settings."""
        self.canvas.delete("image")  # Remove old image
        
        current_img = self._get_current_image()
        if current_img is None:
            self._update_info_text("No image loaded")
            return
        
        try:
            # Apply rotation if needed
            display_img = current_img.copy()
            if self.rotation != 0:
                display_img = self._rotate_image(display_img, self.rotation)
            
            # Handle split view
            if self.show_split_view and self.original_image is not None and self.processed_image is not None:
                split_result = self._create_split_view()
                if split_result is not None:
                    display_img = split_result
            
            # Convert to PIL Image
            if display_img is not None and len(display_img.shape) == 3:
                if display_img.shape[2] == 3:
                    # BGR to RGB
                    display_img = display_img[..., ::-1]
                pil_img = Image.fromarray(display_img)
            elif display_img is not None:
                pil_img = Image.fromarray(display_img, mode='L')
            else:
                self._update_info_text("Error: Could not process image")
                return
            
            # Apply zoom
            img_width, img_height = pil_img.size
            new_width = int(img_width * self.zoom_level)
            new_height = int(img_height * self.zoom_level)
            
            if new_width > 0 and new_height > 0:
                # Use appropriate resampling based on zoom level
                resample = Image.LANCZOS if self.zoom_level > 1.0 else Image.LANCZOS
                pil_img = pil_img.resize((new_width, new_height), resample)
            
            # Convert to PhotoImage
            self.photo_image = ImageTk.PhotoImage(pil_img)
            
            # Calculate position (centered with pan offset)
            canvas_center_x = self.canvas_width // 2
            canvas_center_y = self.canvas_height // 2
            img_x = canvas_center_x + self.pan_x
            img_y = canvas_center_y + self.pan_y
            
            # Create image on canvas
            self.canvas.create_image(img_x, img_y, anchor='center', 
                                   image=self.photo_image, tags="image")
            
            # Update scroll region
            bbox = self.canvas.bbox("image")
            if bbox:
                self.canvas.configure(scrollregion=bbox)
            
            # Update overlays
            self._update_grid_overlay()
            self._update_info_text()
            
        except Exception as e:
            self.logger.error(f"Error updating display: {e}")
            self._update_info_text(f"Display error: {str(e)}")
    
    def _create_split_view(self) -> Optional[np.ndarray]:
        """Create split view showing original on left, processed on right."""
        if self.original_image is None or self.processed_image is None:
            return self.processed_image if self.processed_image is not None else self.original_image
        
        # Ensure both images have same dimensions
        h1, w1 = self.original_image.shape[:2]
        h2, w2 = self.processed_image.shape[:2]
        
        # Resize to match if needed
        if (h1, w1) != (h2, w2):
            target_h, target_w = min(h1, h2), min(w1, w2)
            orig_resized = self.original_image[:target_h, :target_w]
            proc_resized = self.processed_image[:target_h, :target_w]
        else:
            orig_resized = self.original_image
            proc_resized = self.processed_image
        
        # Create split view
        split_img = orig_resized.copy()
        mid_point = int(split_img.shape[1] * self.split_position)
        split_img[:, mid_point:] = proc_resized[:, mid_point:]
        
        # Draw dividing line
        split_img[:, max(0, mid_point-1):min(split_img.shape[1], mid_point+1)] = [255, 255, 0]  # Yellow line
        
        return split_img
    
    def _rotate_image(self, image: np.ndarray, angle: int) -> np.ndarray:
        """Rotate image by specified angle."""
        if angle == 0:
            return image
        
        rotations = angle // 90
        for _ in range(rotations % 4):
            image = np.rot90(image, k=-1)  # Clockwise rotation
        
        return image
    
    def _update_grid_overlay(self):
        """Update grid overlay if enabled."""
        self.canvas.delete("grid")
        
        if not self.show_grid_var.get():
            return
        
        # Draw grid lines
        width = self.canvas_width
        height = self.canvas_height
        
        # Vertical lines
        for x in range(0, width, 50):
            self.canvas.create_line(x, 0, x, height, fill='gray40', width=1, tags="grid")
        
        # Horizontal lines
        for y in range(0, height, 50):
            self.canvas.create_line(0, y, width, y, fill='gray40', width=1, tags="grid")
    
    def _update_info_text(self, custom_text: Optional[str] = None):
        """Update information overlay."""
        if not self.show_info_var.get():
            self.canvas.itemconfig(self.info_text, text="")
            return

        if custom_text:
            self.canvas.itemconfig(self.info_text, text=custom_text)
            return
        
        current_img = self._get_current_image()
        if current_img is None:
            self.canvas.itemconfig(self.info_text, text="No image loaded")
            return
        
        # Build info text
        h, w = current_img.shape[:2]
        channels = current_img.shape[2] if len(current_img.shape) == 3 else 1
        
        info_lines = [
            f"Size: {w} × {h}",
            f"Channels: {channels}",
            f"Zoom: {self.zoom_level:.0%}",
            f"Rotation: {self.rotation}°"
        ]
        
        if self.show_split_view:
            info_lines.append("Mode: Split View")
        elif self.show_original:
            info_lines.append("Mode: Original")
        else:
            info_lines.append("Mode: Processed")
        
        info_text = "\n".join(info_lines)
        self.canvas.itemconfig(self.info_text, text=info_text)
    
    def _update_zoom_label(self):
        """Update zoom level display."""
        self.zoom_label.config(text=f"{self.zoom_level:.0%}")
    
    def _start_pan(self, event):
        """Start panning operation."""
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.is_panning = True
    
    def _pan_image(self, event):
        """Handle panning motion."""
        if not self.is_panning:
            return
        
        dx = event.x - self.pan_start_x
        dy = event.y - self.pan_start_y
        
        self.pan_x += dx
        self.pan_y += dy
        
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        
        self._update_display()
    
    def _end_pan(self, event):
        """End panning operation."""
        self.is_panning = False
    
    def _mouse_wheel(self, event):
        """Handle mouse wheel zoom."""
        if event.delta > 0:
            self.zoom_in(1.1)
        else:
            self.zoom_out(0.9)
    
    def _double_click(self, event):
        """Handle double click to fit to window."""
        self.fit_to_window()
    
    def set_split_position(self, position: float):
        """Set the split position for split view (0.0 to 1.0)."""
        self.split_position = max(0.0, min(1.0, position))
        if self.show_split_view:
            self._update_display()
    
    def _on_split_change(self, value):
        """Handle split slider change."""
        split_position = float(value) / 100.0
        self.set_split_position(split_position)
