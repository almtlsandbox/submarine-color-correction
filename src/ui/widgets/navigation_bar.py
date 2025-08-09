"""
Enhanced navigation bar with full video and image support.
Unified navigation for both images and video frames.
"""
import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable
import threading

from services.logger_service import get_logger


class NavigationBar:
    """Unified navigation controls for images and videos."""
    
    def __init__(self, parent: tk.Widget):
        self.parent = parent
        self.logger = get_logger('navigation_bar')
        
        # State
        self.video_mode = False
        self.is_playing = False
        self.playback_job = None
        self.total_items = 0
        self.current_item = 0
        self.fps = 30.0
        
        # Callbacks
        self.on_prev_callback: Optional[Callable] = None
        self.on_next_callback: Optional[Callable] = None
        self.on_zoom_in_callback: Optional[Callable] = None
        self.on_zoom_out_callback: Optional[Callable] = None
        self.on_reset_view_callback: Optional[Callable] = None
        self.on_rotate_left_callback: Optional[Callable] = None
        self.on_rotate_right_callback: Optional[Callable] = None
        self.on_frame_change_callback: Optional[Callable] = None
        self.on_play_pause_callback: Optional[Callable] = None
        self.on_process_video_callback: Optional[Callable] = None
        
        self.create_ui()
    
    def create_ui(self):
        """Create the navigation interface."""
        # Main navigation frame
        nav_frame = tk.LabelFrame(self.parent, text="Navigation & View", padx=5, pady=5)
        nav_frame.pack(fill=tk.X, padx=5, pady=(5,10))
        
        # Basic navigation controls (row 0)
        self.btn_prev = tk.Button(nav_frame, text="<< Previous", command=self._on_prev,
                                 bg='#4A90E2', fg='white', font=('Arial', 9, 'bold'),
                                 relief='raised', bd=2)
        self.btn_prev.grid(row=0, column=0, sticky='ew', padx=2)
        
        self.btn_next = tk.Button(nav_frame, text="Next >>", command=self._on_next,
                                 bg='#5BA3F5', fg='white', font=('Arial', 9, 'bold'),
                                 relief='raised', bd=2)
        self.btn_next.grid(row=0, column=1, sticky='ew', padx=2)
        
        self.btn_zoom_in = tk.Button(nav_frame, text="Zoom In", command=self._on_zoom_in,
                                    bg='#7ED321', fg='white', font=('Arial', 9, 'bold'),
                                    relief='raised', bd=2)
        self.btn_zoom_in.grid(row=0, column=2, sticky='ew', padx=2)
        
        self.btn_zoom_out = tk.Button(nav_frame, text="Zoom Out", command=self._on_zoom_out,
                                     bg='#8EE234', fg='white', font=('Arial', 9, 'bold'),
                                     relief='raised', bd=2)
        self.btn_zoom_out.grid(row=0, column=3, sticky='ew', padx=2)
        
        self.btn_zoom_reset = tk.Button(nav_frame, text="Reset View", command=self._on_reset_view,
                                       bg='#50C878', fg='white', font=('Arial', 9, 'bold'),
                                       relief='raised', bd=2)
        self.btn_zoom_reset.grid(row=0, column=4, sticky='ew', padx=2)
        
        self.btn_rotate_left = tk.Button(nav_frame, text="Rotate ↺", command=self._on_rotate_left,
                                        bg='#FF8C00', fg='white', font=('Arial', 9, 'bold'),
                                        relief='raised', bd=2)
        self.btn_rotate_left.grid(row=0, column=5, sticky='ew', padx=2)
        
        self.btn_rotate_right = tk.Button(nav_frame, text="Rotate ↻", command=self._on_rotate_right,
                                         bg='#FFA500', fg='white', font=('Arial', 9, 'bold'),
                                         relief='raised', bd=2)
        self.btn_rotate_right.grid(row=0, column=6, sticky='ew', padx=2)
        
        # Video navigation controls (row 1)
        self.video_nav_frame = tk.Frame(nav_frame)
        self.video_nav_frame.grid(row=1, column=0, columnspan=7, sticky='ew', pady=(5,0))
        
        tk.Label(self.video_nav_frame, text="Frame:").pack(side=tk.LEFT)
        
        self.frame_var = tk.IntVar(value=0)
        self.video_frame_slider = tk.Scale(self.video_nav_frame, from_=0, to=100,
                                         orient=tk.HORIZONTAL, variable=self.frame_var,
                                         command=self._on_frame_change, length=200, state='disabled')
        self.video_frame_slider.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.frame_label = tk.Label(self.video_nav_frame, text="0 / 0")
        self.frame_label.pack(side=tk.RIGHT, padx=5)
        
        # Video playback controls (row 2)
        self.video_controls_frame = tk.Frame(nav_frame)
        self.video_controls_frame.grid(row=2, column=0, columnspan=7, sticky='ew', pady=(2,0))
        
        # Playback controls
        playback_frame = tk.Frame(self.video_controls_frame)
        playback_frame.pack(side=tk.LEFT)
        
        self.btn_video_play = tk.Button(playback_frame, text="▶️ Play", 
                                       command=self._on_play_pause, width=8, state='disabled',
                                       bg='#9B59B6', fg='white', font=('Arial', 9, 'bold'),
                                       relief='raised', bd=2)
        self.btn_video_play.pack(side=tk.LEFT, padx=2)
        
        self.btn_step_back = tk.Button(playback_frame, text="⏮️", 
                                      command=self._step_back, width=3, state='disabled',
                                      bg='#E74C3C', fg='white', font=('Arial', 9, 'bold'),
                                      relief='raised', bd=2)
        self.btn_step_back.pack(side=tk.LEFT, padx=1)
        
        self.btn_step_forward = tk.Button(playback_frame, text="⏭️", 
                                         command=self._step_forward, width=3, state='disabled',
                                         bg='#C0392B', fg='white', font=('Arial', 9, 'bold'),
                                         relief='raised', bd=2)
        self.btn_step_forward.pack(side=tk.LEFT, padx=1)
        
        # Speed control
        speed_frame = tk.Frame(self.video_controls_frame)
        speed_frame.pack(side=tk.LEFT, padx=10)
        
        tk.Label(speed_frame, text="Speed:").pack(side=tk.LEFT)
        self.speed_var = tk.DoubleVar(value=1.0)
        self.speed_scale = tk.Scale(speed_frame, from_=0.25, to=2.0, resolution=0.25,
                                   orient=tk.HORIZONTAL, variable=self.speed_var,
                                   length=100, state='disabled')
        self.speed_scale.pack(side=tk.LEFT, padx=2)
        
        # Process video button
        self.btn_process_video = tk.Button(self.video_controls_frame, text="🎬 Process Full Video", 
                                          command=self._on_process_video, font=('Arial', 9, 'bold'),
                                          state='disabled', bg='#8E44AD', fg='white',
                                          relief='raised', bd=2)
        self.btn_process_video.pack(side=tk.RIGHT, padx=2)
        
        # Configure column weights for equal distribution
        for i in range(7):
            nav_frame.columnconfigure(i, weight=1)
        
        # Initially disable video controls
        self._update_video_controls_state()
    
    def set_callbacks(self, **callbacks):
        """Set callback functions for navigation events."""
        self.on_prev_callback = callbacks.get('on_prev')
        self.on_next_callback = callbacks.get('on_next')
        self.on_zoom_in_callback = callbacks.get('on_zoom_in')
        self.on_zoom_out_callback = callbacks.get('on_zoom_out')
        self.on_reset_view_callback = callbacks.get('on_reset_view')
        self.on_rotate_left_callback = callbacks.get('on_rotate_left')
        self.on_rotate_right_callback = callbacks.get('on_rotate_right')
        self.on_frame_change_callback = callbacks.get('on_frame_change')
        self.on_play_pause_callback = callbacks.get('on_play_pause')
        self.on_process_video_callback = callbacks.get('on_process_video')
    
    def set_image_mode(self, current: int = 0, total: int = 0):
        """Configure for image navigation mode."""
        self.video_mode = False
        self.current_item = current
        self.total_items = total
        self.is_playing = False
        
        if self.playback_job:
            self.parent.after_cancel(self.playback_job)
            self.playback_job = None
        
        self._update_navigation_display()
        self._update_video_controls_state()
        self.logger.info(f"Switched to image mode: {current}/{total}")
    
    def set_video_mode(self, current_frame: int = 0, total_frames: int = 0, fps: float = 30.0):
        """Configure for video navigation mode."""
        self.video_mode = True
        self.current_item = current_frame
        self.total_items = total_frames
        self.fps = fps
        self.is_playing = False
        
        # Update video controls
        self.video_frame_slider.config(from_=0, to=max(0, total_frames-1), state='normal')
        self.frame_var.set(current_frame)
        
        self._update_navigation_display()
        self._update_video_controls_state()
        self.logger.info(f"Switched to video mode: frame {current_frame}/{total_frames} @ {fps}fps")
    
    def update_position(self, current: int):
        """Update current position."""
        self.current_item = current
        if self.video_mode:
            self.frame_var.set(current)
        self._update_navigation_display()
    
    def _update_navigation_display(self):
        """Update navigation display text."""
        if self.video_mode:
            self.frame_label.config(text=f"{self.current_item} / {self.total_items-1}")
        else:
            # Update window title or status for images
            pass
    
    def _update_video_controls_state(self):
        """Enable/disable video controls based on mode."""
        state = 'normal' if self.video_mode else 'disabled'
        
        self.video_frame_slider.config(state=state)
        self.btn_video_play.config(state=state)
        self.btn_step_back.config(state=state)
        self.btn_step_forward.config(state=state)
        self.speed_scale.config(state=state)
        
        if self.video_mode:
            self.btn_process_video.config(state='normal', bg='green', fg='white')
        else:
            self.btn_process_video.config(state='disabled', bg='gray', fg='white')
    
    def _on_prev(self):
        """Handle previous button."""
        if self.on_prev_callback:
            self.on_prev_callback()
    
    def _on_next(self):
        """Handle next button."""
        if self.on_next_callback:
            self.on_next_callback()
    
    def _on_zoom_in(self):
        """Handle zoom in."""
        if self.on_zoom_in_callback:
            self.on_zoom_in_callback()
    
    def _on_zoom_out(self):
        """Handle zoom out."""
        if self.on_zoom_out_callback:
            self.on_zoom_out_callback()
    
    def _on_reset_view(self):
        """Handle reset view."""
        if self.on_reset_view_callback:
            self.on_reset_view_callback()
    
    def _on_rotate_left(self):
        """Handle rotate left."""
        if self.on_rotate_left_callback:
            self.on_rotate_left_callback()
    
    def _on_rotate_right(self):
        """Handle rotate right."""
        if self.on_rotate_right_callback:
            self.on_rotate_right_callback()
    
    def _on_frame_change(self, value):
        """Handle frame slider change."""
        frame_number = int(value)
        self.current_item = frame_number
        self._update_navigation_display()
        
        if self.on_frame_change_callback:
            self.on_frame_change_callback(frame_number)
    
    def _on_play_pause(self):
        """Handle play/pause toggle."""
        self.is_playing = not self.is_playing
        
        if self.is_playing:
            self.btn_video_play.config(text="⏸️ Pause")
            self._start_playback()
        else:
            self.btn_video_play.config(text="▶️ Play")
            if self.playback_job:
                self.parent.after_cancel(self.playback_job)
                self.playback_job = None
        
        if self.on_play_pause_callback:
            self.on_play_pause_callback(self.is_playing)
    
    def _start_playback(self):
        """Start video playback loop."""
        if not self.is_playing:
            return
        
        if self.current_item < self.total_items - 1:
            self.current_item += 1
            self.frame_var.set(self.current_item)
            self._update_navigation_display()
            
            if self.on_frame_change_callback:
                self.on_frame_change_callback(self.current_item)
            
            # Schedule next frame based on speed
            speed = self.speed_var.get()
            delay = int(1000 / (self.fps * speed)) if self.fps > 0 else 33
            self.playback_job = self.parent.after(delay, self._start_playback)
        else:
            # Reached end, stop playback
            self.is_playing = False
            self.btn_video_play.config(text="▶️ Play")
    
    def _step_back(self):
        """Step one frame back."""
        if self.current_item > 0:
            self.current_item -= 1
            self.frame_var.set(self.current_item)
            self._update_navigation_display()
            
            if self.on_frame_change_callback:
                self.on_frame_change_callback(self.current_item)
    
    def _step_forward(self):
        """Step one frame forward."""
        if self.current_item < self.total_items - 1:
            self.current_item += 1
            self.frame_var.set(self.current_item)
            self._update_navigation_display()
            
            if self.on_frame_change_callback:
                self.on_frame_change_callback(self.current_item)
    
    def _on_process_video(self):
        """Handle process video button."""
        if self.on_process_video_callback:
            self.on_process_video_callback()
    
    def stop_playback(self):
        """Stop video playback."""
        self.is_playing = False
        self.btn_video_play.config(text="▶️ Play")
        if self.playback_job:
            self.parent.after_cancel(self.playback_job)
            self.playback_job = None
