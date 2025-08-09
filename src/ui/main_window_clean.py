"""
Clean, working main window with proper video and parameter support.
Fixed geometry manager conflicts and integrated all components properly.
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import numpy as np
import subprocess
import sys
import os
import glob
from pathlib import Path
from typing import Optional, List

from models.image_data import ImageData, ImageCollection
from models.video_data import VideoData
from models.processing_params import ProcessingParameters
from core.image_processor import ImageProcessor
from core.auto_tuner import AutoTuner
from services.logger_service import get_logger, setup_logging

# Import our enhanced widgets
from ui.widgets import ParameterPanel, NavigationBar, ImageViewer


class MainWindowClean:
    """Clean main window with proper video and parameter support."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        
        # Setup logging control (disabled by default)
        self.logging_enabled = tk.BooleanVar(value=False)
        setup_logging(enable_file_logging=self.logging_enabled.get())
        self.logger = get_logger('main_window_clean')
        
        # Initialize core components
        self.image_processor = ImageProcessor()
        self.auto_tuner = AutoTuner()
        self.processing_params = ProcessingParameters()
        
        # Data state
        self.current_image: Optional[ImageData] = None
        self.current_video: Optional[VideoData] = None
        self.image_files: List[Path] = []
        self.current_file_index = 0
        self.video_mode = False
        
        # UI components (will be initialized)
        self.parameter_panel: Optional[ParameterPanel] = None
        self.navigation_bar: Optional[NavigationBar] = None
        self.image_viewer: Optional[ImageViewer] = None
        
        self.setup_ui()
        self.logger.info("Clean main window initialized successfully")
    
    def setup_ui(self):
        """Setup clean UI with proper layout management."""
        try:
            # Configure main window
            self.root.title("Submarine Color Correction v2.0 - Clean Edition")
            self.root.geometry("1400x900")
            self.root.minsize(1000, 700)
            
            # Create menu bar
            self._create_menu_bar()
            
            # Create main layout using PanedWindow for proper resizing
            self.main_paned = ttk.PanedWindow(self.root, orient='horizontal')
            self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Left panel for controls (350px wide)
            self.left_frame = ttk.Frame(self.main_paned, width=350)
            self.main_paned.add(self.left_frame, weight=0)
            
            # Right panel for image viewing  
            self.right_frame = ttk.Frame(self.main_paned)
            self.main_paned.add(self.right_frame, weight=1)
            
            # Setup left panel components
            self._setup_left_panel()
            
            # Setup right panel components  
            self._setup_right_panel()
            
            # Setup status bar
            self._setup_status_bar()
            
            # Bind keyboard shortcuts
            self._bind_shortcuts()
            
            self.logger.info("Clean UI setup completed successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to setup UI: {e}")
            messagebox.showerror("Error", f"Failed to setup UI: {str(e)}")
            raise
    
    def _create_menu_bar(self):
        """Create comprehensive menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Images...", command=self.load_images)
        file_menu.add_command(label="Open Video...", command=self.load_video)
        file_menu.add_separator()
        file_menu.add_command(label="Save Image", command=self.save_image)
        file_menu.add_command(label="Save Video", command=self.save_video)
        file_menu.add_separator()
        file_menu.add_command(label="View Log File", command=self.open_log_file, accelerator="Ctrl+L")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Reset Parameters", command=self.reset_parameters)
        edit_menu.add_command(label="Auto-Tune", command=self.auto_tune)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Fit to Window", command=self.fit_to_window, accelerator="Ctrl+0")
        view_menu.add_command(label="Actual Size", command=self.reset_view, accelerator="Ctrl+1")
        view_menu.add_separator()
        view_menu.add_command(label="Toggle Auto-fit", command=self.toggle_auto_fit, accelerator="Ctrl+F")
        view_menu.add_separator()
        view_menu.add_command(label="Zoom In", command=self._zoom_in, accelerator="Ctrl++")
        view_menu.add_command(label="Zoom Out", command=self._zoom_out, accelerator="Ctrl+-")
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
    
    def _setup_left_panel(self):
        """Setup left panel with file operations, navigation, and parameters."""
        # File operations section
        file_frame = ttk.LabelFrame(self.left_frame, text="📁 File Operations", padding=5)
        file_frame.pack(fill=tk.X, padx=5, pady=(5, 10))
        
        # File type selection
        type_frame = ttk.Frame(file_frame)
        type_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.file_type_var = tk.StringVar(value="image")
        ttk.Radiobutton(type_frame, text="🖼️ Images", variable=self.file_type_var, 
                       value="image").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(type_frame, text="🎬 Video", variable=self.file_type_var,
                       value="video").pack(side=tk.LEFT)
        
        # Load and save buttons
        button_frame = ttk.Frame(file_frame)
        button_frame.pack(fill=tk.X)
        
        tk.Button(button_frame, text="📂 Load", command=self.load_files,
                 bg='#3498DB', fg='white', font=('Arial', 10, 'bold'),
                 relief='raised', bd=2).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        tk.Button(button_frame, text="💾 Save", command=self.save_current,
                 bg='#27AE60', fg='white', font=('Arial', 10, 'bold'),
                 relief='raised', bd=2).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 2))
        tk.Button(button_frame, text="📋 Logs", command=self.open_log_file,
                 bg='#E74C3C', fg='white', font=('Arial', 10, 'bold'),
                 relief='raised', bd=2).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))
        
        # File info and logging control
        info_frame = ttk.Frame(file_frame)
        info_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.file_info_label = ttk.Label(info_frame, text="No files loaded")
        self.file_info_label.pack(anchor='w')
        
        # Logging control checkbox
        logging_frame = ttk.Frame(info_frame)
        logging_frame.pack(fill=tk.X, pady=(2, 0))
        
        logging_check = ttk.Checkbutton(
            logging_frame, 
            text="Enable log file generation", 
            variable=self.logging_enabled,
            command=self._on_logging_toggle
        )
        logging_check.pack(anchor='w')
        
        # Navigation bar
        nav_frame = ttk.LabelFrame(self.left_frame, text="🎮 Navigation & View", padding=5)
        nav_frame.pack(fill=tk.X, padx=5, pady=(0, 10))
        
        # Quick view controls at top
        view_controls_frame = ttk.Frame(nav_frame)
        view_controls_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Button(view_controls_frame, text="🔍 Fit to Window", 
                  command=self.fit_to_window,
                  bg='#2ECC71', fg='white', font=('Arial', 9, 'bold'),
                  relief='raised', bd=2).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(view_controls_frame, text="↺ Reset View", 
                  command=self.reset_view,
                  bg='#F39C12', fg='white', font=('Arial', 9, 'bold'),
                  relief='raised', bd=2).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(view_controls_frame, text="🔄 Fit to Window", 
                  command=self.fit_to_window,
                  bg='#16A085', fg='white', font=('Arial', 9, 'bold'),
                  relief='raised', bd=2).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(view_controls_frame, text="⚙️ Auto-Fit", 
                  command=self.toggle_auto_fit,
                  bg='#9B59B6', fg='white', font=('Arial', 9, 'bold'),
                  relief='raised', bd=2).pack(side=tk.LEFT)
        
        # Auto-fit toggle state
        self.auto_fit_enabled = tk.BooleanVar(value=True)  # Default enabled
        auto_fit_check = ttk.Checkbutton(view_controls_frame, text="Auto-fit new images", 
                                        variable=self.auto_fit_enabled)
        auto_fit_check.pack(side=tk.RIGHT)
        
        self.navigation_bar = NavigationBar(nav_frame)
        self._setup_navigation_callbacks()
        
        # Parameters panel
        param_frame = ttk.LabelFrame(self.left_frame, text="⚙️ Parameters", padding=5)
        param_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        
        self.parameter_panel = ParameterPanel(param_frame, self.processing_params,
                                             on_change_callback=None)  # Disabled automatic processing
        self._setup_parameter_callbacks()
        
        # Processing controls section
        controls_frame = ttk.LabelFrame(self.left_frame, text="🎛️ Processing Controls", padding=5)
        controls_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # Create colorful processing buttons
        buttons_frame = ttk.Frame(controls_frame)
        buttons_frame.pack(fill=tk.X)
        
        # Row 1: Apply and Auto-Tune
        row1_frame = ttk.Frame(buttons_frame)
        row1_frame.pack(fill=tk.X, pady=(0, 2))
        
        tk.Button(row1_frame, text="🎨 Apply Correction", command=self.apply_correction,
                 bg='#3498DB', fg='white', font=('Arial', 10, 'bold'),
                 relief='raised', bd=2).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        
        tk.Button(row1_frame, text="✨ Auto-Tune", command=self.auto_tune,
                 bg='#2ECC71', fg='white', font=('Arial', 10, 'bold'),
                 relief='raised', bd=2).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))
        
        # Row 2: Reset and Save
        row2_frame = ttk.Frame(buttons_frame)
        row2_frame.pack(fill=tk.X)
        
        tk.Button(row2_frame, text="🔄 Reset", command=self.reset_parameters,
                 bg='#F39C12', fg='white', font=('Arial', 10, 'bold'),
                 relief='raised', bd=2).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        
        tk.Button(row2_frame, text="💾 Save Result", command=self.save_corrected,
                 bg='#E74C3C', fg='white', font=('Arial', 10, 'bold'),
                 relief='raised', bd=2).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))
        
        self.logger.info("Left panel setup completed")
    
    def _setup_right_panel(self):
        """Setup right panel with image viewer."""
        # Image viewer
        viewer_frame = ttk.LabelFrame(self.right_frame, text="🖼️ Image Viewer", padding=5)
        viewer_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.image_viewer = ImageViewer(viewer_frame, view_mode_callback=self._on_view_mode_change)
        
        self.logger.info("Right panel setup completed")
    
    def _setup_status_bar(self):
        """Setup status bar at bottom."""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = ttk.Label(status_frame, text="Ready", relief=tk.SUNKEN, anchor='w')
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, 
                                          mode='determinate', length=200)
        self.progress_bar.pack(side=tk.RIGHT, padx=5)
    
    def _setup_navigation_callbacks(self):
        """Setup navigation bar callbacks."""
        if self.navigation_bar:
            self.navigation_bar.set_callbacks(
                on_prev=self.previous_item,
                on_next=self.next_item,
                on_zoom_in=self._zoom_in,
                on_zoom_out=self._zoom_out,
                on_reset_view=self.reset_view,
                on_rotate_left=self.rotate_left,
                on_rotate_right=self.rotate_right,
                on_frame_change=self._on_frame_change,
                on_play_pause=self._on_play_pause,
                on_process_video=self.process_full_video
            )
    
    def _setup_parameter_callbacks(self):
        """Setup parameter panel callbacks."""
        # The parameter panel will call our update method when parameters change
        # This is handled through the on_change_callback passed to the constructor
        pass
    
    def _on_parameter_change(self):
        """Handle manual parameter changes - only called by Apply Correction button."""
        try:
            # Update parameters from UI
            if self.parameter_panel:
                self.parameter_panel.update_parameters_from_ui()
            
            # Reprocess current image or frame
            if self.video_mode:
                self._process_current_frame()
            else:
                self._process_current_image()
                
        except Exception as e:
            self.logger.error(f"Failed to process after parameter change: {e}")
            self.status_label.config(text=f"Processing error: {str(e)}")
    
    def _bind_shortcuts(self):
        """Bind keyboard shortcuts."""
        self.root.bind('<Control-o>', lambda e: self.load_files())
        self.root.bind('<Control-s>', lambda e: self.save_current())
        self.root.bind('<Control-l>', lambda e: self.open_log_file())
        self.root.bind('<Control-0>', lambda e: self.fit_to_window())
        self.root.bind('<Control-1>', lambda e: self.reset_view())
        self.root.bind('<Control-f>', lambda e: self.toggle_auto_fit())
        self.root.bind('<Control-plus>', lambda e: self._zoom_in())
        self.root.bind('<Control-equal>', lambda e: self._zoom_in())  # + key without shift
        self.root.bind('<Control-minus>', lambda e: self._zoom_out())
        self.root.bind('<Left>', lambda e: self.previous_item())
        self.root.bind('<Right>', lambda e: self.next_item())
        self.root.bind('<space>', lambda e: self._toggle_playback())
        self.root.bind('<Control-r>', lambda e: self.reset_parameters())
    
    # File operations
    def load_files(self):
        """Load files based on selected type."""
        if self.file_type_var.get() == "video":
            self.load_video()
        else:
            self.load_images()
    
    def load_images(self):
        """Load image files."""
        filetypes = [
            ('Image files', '*.jpg *.jpeg *.png *.bmp *.tiff *.tga'),
            ('All files', '*.*')
        ]
        
        filenames = filedialog.askopenfilenames(
            title="Select Image Files",
            filetypes=filetypes
        )
        
        if not filenames:
            return
        
        try:
            self.image_files = [Path(f) for f in filenames]
            self.current_file_index = 0
            self.video_mode = False
            self.current_video = None
            
            # Update navigation
            if self.navigation_bar:
                self.navigation_bar.set_image_mode(0, len(self.image_files))
            
            # Load first image
            self._load_current_image()
            
            # Update file info
            self.file_info_label.config(text=f"Images: {len(self.image_files)} files")
            self.status_label.config(text=f"Loaded {len(self.image_files)} images")
            
            self.logger.info(f"Loaded {len(self.image_files)} image files")
            
        except Exception as e:
            self.logger.error(f"Failed to load images: {e}")
            messagebox.showerror("Error", f"Failed to load images: {str(e)}")
    
    def load_video(self):
        """Load video file."""
        filetypes = [
            ('Video files', '*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm'),
            ('All files', '*.*')
        ]
        
        filename = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=filetypes
        )
        
        if not filename:
            return
        
        try:
            self.current_video = VideoData(filename)
            self.video_mode = True
            self.image_files = []
            
            # Load video
            if not self.current_video.load():
                raise Exception("Failed to load video file")
            
            # Update navigation
            if self.navigation_bar:
                total_frames = self.current_video.total_frames
                fps = self.current_video.fps
                self.navigation_bar.set_video_mode(0, total_frames, fps)
            
            # Load first frame
            self._load_current_frame()
            
            # Auto-fit new video to window if enabled
            if self.auto_fit_enabled.get() and self.image_viewer:
                self.image_viewer.fit_to_window()
            
            # Update file info
            frame_info = f"Video: {self.current_video.total_frames} frames @ {self.current_video.fps:.1f}fps"
            self.file_info_label.config(text=frame_info)
            self.status_label.config(text=f"Loaded video: {Path(filename).name}")
            
            self.logger.info(f"Loaded video: {filename}")
            
        except Exception as e:
            self.logger.error(f"Failed to load video: {e}")
            messagebox.showerror("Error", f"Failed to load video: {str(e)}")
    
    def save_current(self):
        """Save current processed result."""
        if self.video_mode:
            self.save_video()
        else:
            self.save_image()
    
    def save_image(self):
        """Save current processed image."""
        if not self.current_image or not self.current_image.has_correction():
            messagebox.showwarning("Warning", "No processed image to save")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Save Processed Image",
            defaultextension=".jpg",
            filetypes=[('JPEG files', '*.jpg'), ('PNG files', '*.png'), ('All files', '*.*')]
        )
        
        if filename:
            try:
                if self.current_image.save_corrected(filename):
                    self.status_label.config(text=f"Saved: {Path(filename).name}")
                    self.logger.info(f"Saved image: {filename}")
                else:
                    raise Exception("Save operation failed")
            except Exception as e:
                self.logger.error(f"Failed to save image: {e}")
                messagebox.showerror("Error", f"Failed to save image: {str(e)}")
    
    def save_video(self):
        """Save processed video."""
        if not self.video_mode or not self.current_video:
            messagebox.showwarning("Warning", "No video loaded")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Save Processed Video",
            defaultextension=".mp4",
            filetypes=[('MP4 files', '*.mp4'), ('AVI files', '*.avi'), ('All files', '*.*')]
        )
        
        if filename:
            self.process_full_video(output_path=filename)
    
    def process_full_video(self, output_path: Optional[str] = None):
        """Process entire video."""
        if not self.video_mode or not self.current_video:
            messagebox.showwarning("Warning", "No video loaded")
            return
        
        if not output_path:
            output_path = filedialog.asksaveasfilename(
                title="Save Processed Video",
                defaultextension=".mp4",
                filetypes=[('MP4 files', '*.mp4'), ('AVI files', '*.avi')]
            )
            if not output_path:
                return
        
        # For now, show a placeholder message
        messagebox.showinfo("Video Processing", 
                           f"Video processing will save to: {output_path}\n"
                           "This feature is being implemented...")
        
        self.logger.info(f"Video processing requested for: {output_path}")
    
    def open_log_file(self):
        """Open the current log file in the default text editor."""
        try:
            # Check if logging is enabled
            if not self.logging_enabled.get():
                messagebox.showwarning("Log Files Disabled", 
                                     "Log file generation is currently disabled.\n"
                                     "Enable it using the checkbox in File Operations to create log files.")
                return
            
            # Find the most recent log file
            # First check the main directory for submarine_color_correction logs
            main_dir = Path(__file__).parent.parent.parent
            pattern = main_dir / "submarine_color_correction_*.log"
            log_files = glob.glob(str(pattern))
            
            # Also check for color_correction logs
            pattern2 = main_dir / "color_correction_*.log"
            log_files.extend(glob.glob(str(pattern2)))
            
            # Check the logs subdirectory
            logs_dir = main_dir / "logs"
            if logs_dir.exists():
                pattern3 = logs_dir / "*.log"
                log_files.extend(glob.glob(str(pattern3)))
            
            if not log_files:
                messagebox.showwarning("No Log Files", "No log files found.")
                return
            
            # Get the most recent log file
            most_recent_log = max(log_files, key=os.path.getmtime)
            
            # Open the log file with the default text editor
            if os.name == 'nt':  # Windows
                os.startfile(most_recent_log)
            elif os.name == 'posix':  # macOS and Linux
                subprocess.call(['open' if sys.platform == 'darwin' else 'xdg-open', most_recent_log])
            
            self.status_label.config(text=f"Opened log: {Path(most_recent_log).name}")
            self.logger.info(f"Opened log file: {most_recent_log}")
            
        except Exception as e:
            self.logger.error(f"Failed to open log file: {e}")
            messagebox.showerror("Error", f"Failed to open log file: {str(e)}")
    
    def _on_logging_toggle(self):
        """Handle logging enable/disable toggle."""
        try:
            is_enabled = self.logging_enabled.get()
            
            # Reconfigure logging
            setup_logging(enable_file_logging=is_enabled)
            
            # Update logger instance
            self.logger = get_logger('main_window_clean')
            
            if is_enabled:
                self.logger.info("File logging enabled by user")
                self.status_label.config(text="Log file generation enabled")
            else:
                self.logger.info("File logging disabled by user")
                self.status_label.config(text="Log file generation disabled")
            
        except Exception as e:
            self.logger.error(f"Failed to toggle logging: {e}")
            messagebox.showerror("Error", f"Failed to toggle logging: {str(e)}")
    
    
    # Navigation methods
    def previous_item(self):
        """Navigate to previous item."""
        if self.video_mode and self.current_video:
            if self.current_video.prev_frame():
                self._load_current_frame()
                if self.navigation_bar:
                    current, _ = self.current_video.get_navigation_info()
                    self.navigation_bar.update_position(current)
        elif self.image_files and self.current_file_index > 0:
            self.current_file_index -= 1
            self._load_current_image()
            if self.navigation_bar:
                self.navigation_bar.update_position(self.current_file_index)
    
    def next_item(self):
        """Navigate to next item."""
        if self.video_mode and self.current_video:
            if self.current_video.next_frame():
                self._load_current_frame()
                if self.navigation_bar:
                    current, _ = self.current_video.get_navigation_info()
                    self.navigation_bar.update_position(current)
        elif self.image_files and self.current_file_index < len(self.image_files) - 1:
            self.current_file_index += 1
            self._load_current_image()
            if self.navigation_bar:
                self.navigation_bar.update_position(self.current_file_index)
    
    def _on_frame_change(self, frame_number: int):
        """Handle video frame change from navigation."""
        if self.video_mode and self.current_video:
            if self.current_video.jump_to_frame(frame_number):
                self._load_current_frame()
    
    def _on_play_pause(self, is_playing: bool):
        """Handle play/pause from navigation."""
        # Playback is handled internally by navigation bar
        pass
    
    def _toggle_playback(self):
        """Toggle video playback."""
        if self.video_mode and self.navigation_bar:
            self.navigation_bar._on_play_pause()
    
    # Image/frame loading and processing
    def _load_current_image(self):
        """Load current image from file list."""
        if not self.image_files or self.current_file_index >= len(self.image_files):
            return
        
        try:
            image_path = self.image_files[self.current_file_index]
            self.current_image = ImageData(str(image_path))
            
            if not self.current_image.load():
                raise Exception("Failed to load image data")
            
            # Show original image in viewer
            display_image = self.current_image.get_display_image()
            if display_image is not None and self.image_viewer:
                self.image_viewer.load_image(display_image)
                
                # Clear any existing processed image and adjust view mode appropriately
                # This will switch from "corrected" to "original" if needed, but preserve "split" view
                self.image_viewer.clear_processed_image_and_adjust_view()
                
                # Auto-fit to window if enabled
                if self.auto_fit_enabled.get():
                    self.image_viewer.fit_to_window()
            
            # Note: Processing is now manual - user must click Apply Correction
            # self._process_current_image()  # Disabled automatic processing
            
            self.status_label.config(text=f"Image: {image_path.name} ({self.current_file_index + 1}/{len(self.image_files)}) - Click Apply to process")
            
        except Exception as e:
            self.logger.error(f"Failed to load image: {e}")
            self.status_label.config(text=f"Error loading image: {str(e)}")
    
    def _load_current_frame(self):
        """Load current frame from video."""
        if not self.current_video:
            return
        
        try:
            # Get current frame for display
            display_frame = self.current_video.get_current_frame_for_display()
            if display_frame is not None and self.image_viewer:
                self.image_viewer.load_image(display_frame)
                
                # Clear any existing processed image and adjust view mode appropriately
                # This will switch from "corrected" to "original" if needed, but preserve "split" view
                self.image_viewer.clear_processed_image_and_adjust_view()
            
            # Process frame with current parameters
            self._process_current_frame()
            
            current, total = self.current_video.get_navigation_info()
            self.status_label.config(text=f"Frame: {current + 1}/{total}")
            
        except Exception as e:
            self.logger.error(f"Failed to load frame: {e}")
            self.status_label.config(text=f"Error loading frame: {str(e)}")
    
    def _process_current_image(self):
        """Process current image with current parameters."""
        if not self.current_image:
            return
        
        try:
            # Get image for processing
            processing_image = self.current_image.get_processing_image()
            if processing_image is None:
                return
            
            # Process image
            corrected = self.image_processor.process_image(processing_image, self.processing_params)
            
            # Update image data
            self.current_image.set_corrected_result(corrected)
            
            # Update viewer with processed result
            if self.image_viewer:
                display_corrected = cv2.cvtColor(corrected, cv2.COLOR_BGR2RGB)
                self.image_viewer.update_processed_image(display_corrected)
            
        except Exception as e:
            self.logger.error(f"Image processing failed: {e}")
            self.status_label.config(text=f"Processing error: {str(e)}")
    
    def _process_current_frame(self):
        """Process current video frame."""
        if not self.current_video:
            return
        
        try:
            # Get frame for processing
            processing_frame = self.current_video.get_current_frame_for_processing()
            if processing_frame is None:
                return
            
            # Process frame
            corrected = self.image_processor.process_image(processing_frame, self.processing_params)
            
            # Update video data
            self.current_video.set_corrected_frame(corrected)
            
            # Update viewer with processed result
            if self.image_viewer:
                display_corrected = cv2.cvtColor(corrected, cv2.COLOR_BGR2RGB)
                self.image_viewer.update_processed_image(display_corrected)
            
        except Exception as e:
            self.logger.error(f"Frame processing failed: {e}")
            self.status_label.config(text=f"Processing error: {str(e)}")
    
    # View controls
    def fit_to_window(self):
        """Fit image to window."""
        if self.image_viewer:
            self.image_viewer.fit_to_window()
            self.status_label.config(text="Fitted image to window")
    
    def reset_view(self):
        """Reset image view."""
        if self.image_viewer:
            self.image_viewer.reset_view()
            self.status_label.config(text="Reset view to actual size")
    
    def toggle_auto_fit(self):
        """Toggle auto-fit mode."""
        current = self.auto_fit_enabled.get()
        self.auto_fit_enabled.set(not current)
        status = "enabled" if not current else "disabled"
        self.status_label.config(text=f"Auto-fit {status}")
        
        # If enabling auto-fit and we have an image, fit it now
        if not current and (self.current_image or self.current_video):
            self.fit_to_window()
    
    def _on_split_change(self, value):
        """Handle split slider change."""
        if self.image_viewer:
            split_position = float(value) / 100.0
            self.image_viewer.set_split_position(split_position)
    
    def _on_view_mode_change(self):
        """Handle view mode changes - no longer needed as split controls are in ImageViewer."""
        pass
    
    def _zoom_in(self):
        """Zoom in on current image."""
        if self.image_viewer:
            self.image_viewer.zoom_in()
            self.status_label.config(text="Zoomed in")
    
    def _zoom_out(self):
        """Zoom out of current image."""
        if self.image_viewer:
            self.image_viewer.zoom_out()
            self.status_label.config(text="Zoomed out")
    
    def rotate_left(self):
        """Rotate image left."""
        if self.image_viewer:
            self.image_viewer.rotate_left()
    
    def rotate_right(self):
        """Rotate image right."""
        if self.image_viewer:
            self.image_viewer.rotate_right()
    
    # Processing controls
    def apply_correction(self):
        """Apply color correction to current image/frame."""
        # Update parameters from UI and process
        self._on_parameter_change()
    
    def save_corrected(self):
        """Save the corrected image or frame."""
        try:
            if self.video_mode and self.current_video:
                if self.current_video.has_correction():
                    # For video, save the current corrected frame
                    import os
                    from pathlib import Path
                    
                    # Create output filename for current frame
                    video_path = Path(self.current_video.file_path)
                    frame_num = self.current_video.current_frame_number
                    output_path = video_path.parent / f"{video_path.stem}_frame_{frame_num:04d}_corrected.jpg"
                    
                    # Get corrected frame from video (convert RGB to BGR for saving)
                    if self.current_video.corrected_frame_rgb is not None:
                        import cv2
                        corrected_bgr = cv2.cvtColor(self.current_video.corrected_frame_rgb, cv2.COLOR_RGB2BGR)
                        success = cv2.imwrite(str(output_path), corrected_bgr)
                        if success:
                            self.status_label.config(text=f"Frame saved: {output_path.name}")
                        else:
                            self.status_label.config(text="Failed to save frame")
                    else:
                        self.status_label.config(text="No corrected frame available")
                else:
                    self.status_label.config(text="No correction to save")
            elif self.current_image:
                if self.current_image.has_correction():
                    # Create output filename for image
                    import os
                    from pathlib import Path
                    
                    original_path = Path(self.current_image.file_path)
                    output_path = original_path.parent / f"{original_path.stem}_corrected{original_path.suffix}"
                    
                    success = self.current_image.save_corrected(str(output_path))
                    if success:
                        self.status_label.config(text=f"Image saved: {output_path.name}")
                    else:
                        self.status_label.config(text="Failed to save image")
                else:
                    self.status_label.config(text="No correction to save")
            else:
                self.status_label.config(text="No image to save")
                
        except Exception as e:
            self.logger.error(f"Save failed: {e}")
            self.status_label.config(text=f"Save failed: {str(e)}")
    
    # Parameter controls
    def reset_parameters(self):
        """Reset all parameters to defaults."""
        self.processing_params = ProcessingParameters()
        if self.parameter_panel:
            # Update the parameter panel's reference to the new parameters object
            self.parameter_panel.params = self.processing_params
            self.parameter_panel.update_ui_from_parameters()
        
        # Reprocess current image/frame only on manual Apply
        # if self.video_mode:
        #     self._process_current_frame()
        # else:
        #     self._process_current_image()
        
        self.status_label.config(text="Parameters reset to defaults - Click Apply to process")
    
    def auto_tune(self):
        """Auto-tune parameters."""
        if self.video_mode and self.current_video:
            processing_image = self.current_video.get_current_frame_for_processing()
        elif self.current_image:
            processing_image = self.current_image.get_processing_image()
        else:
            messagebox.showwarning("Warning", "No image or video loaded")
            return
        
        if processing_image is None:
            messagebox.showwarning("Warning", "No image data available for auto-tuning")
            return
        
        try:
            self.status_label.config(text="Auto-tuning parameters...")
            self.root.update_idletasks()
            
            # Ensure parameters are up to date before auto-tuning
            if self.parameter_panel:
                # Force parameter update from UI to ensure user selections are preserved
                self.parameter_panel.update_parameters_from_ui()
                # Double-check: manually sync the checkbox value
                self.processing_params.green_water_detection = self.parameter_panel.green_water_detection_var.get()
            
            # Call the auto-tuner with current parameters to respect user settings
            result = self.auto_tuner.auto_tune(processing_image, self.processing_params)            # Update parameters with auto-tuned values
            self.processing_params = result.parameters
            
            # Update UI to reflect new parameters
            if self.parameter_panel:
                # Update the parameter panel's reference to the new parameters object
                self.parameter_panel.params = self.processing_params
                self.parameter_panel.update_ui_from_parameters()
            
            # Automatically apply the correction
            confidence_percent = int(result.confidence * 100)
            self.status_label.config(text=f"Auto-tune complete (confidence: {confidence_percent}%) - Applying correction...")
            self.root.update_idletasks()
            
            # Apply the auto-tuned parameters
            self._on_parameter_change()
            
            self.status_label.config(text=f"Auto-tune applied (confidence: {confidence_percent}%)")
            self.logger.info(f"Auto-tune completed and applied with confidence: {result.confidence:.2f}")
            
        except Exception as e:
            self.logger.error(f"Auto-tune failed: {e}")
            messagebox.showerror("Error", f"Auto-tune failed: {str(e)}")
            self.status_label.config(text="Auto-tune failed")
    
    def show_about(self):
        """Show about dialog."""
        about_text = """Submarine Color Correction v2.0
Clean Edition

A professional tool for underwater image and video color correction.

Features:
• Advanced color correction algorithms
• Real-time parameter adjustment
• Video frame-by-frame processing
• Professional image viewer with pan/zoom
• Comprehensive parameter controls

Built with modern Python architecture and professional UI components."""
        
        messagebox.showinfo("About", about_text)


def create_main_window() -> MainWindowClean:
    """Create and return the clean main application window."""
    root = tk.Tk()
    return MainWindowClean(root)
