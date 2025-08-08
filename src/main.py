from concurrent.futures import thread
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from PIL import Image, ImageTk, ImageEnhance
import cv2
import numpy as np
import color_correction as cc
import logging
import time

# Constants
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tga', '.webp')

class ColorCorrectionProcessor:
    """Wrapper class for color correction functions"""
    
    def process_image(self, img, **params):
        """Process image with given parameters"""
        result = img.copy()
        
        # White balance
        if params.get('enable_white_balance', True):
            method = params.get('wb_method', 'robust')
            strength = params.get('white_balance_strength', 1.0)
            
            if method == 'robust':
                lower = params.get('robust_lower', 5)
                upper = params.get('robust_upper', 95) 
                result = cc.white_balance(result, strength=strength, lower=lower, upper=upper)
            elif method == 'white_patch':
                percentile = params.get('retinex_percentile', 1.0)
                result = cc.white_patch_retinex(result, percentile=percentile)
            elif method == 'gray_world':
                lower = params.get('robust_lower', 5)
                upper = params.get('robust_upper', 95)
                result = cc.gray_world(result, strength=strength, lower=lower, upper=upper)
        
        # Red channel enhancement
        if params.get('enable_red_channel', True):
            red_scale = params.get('red_scale', 1.3)
            result = cc.enhance_red_channel(result, scale=red_scale)
        
        # Fusion processing
        if params.get('enable_fusion', False):
            method = params.get('fusion_method', 'average')
            
            # Create two paths for fusion
            if params.get('fusion_balance', 0.5) < 0.5:
                # Path A: More dehazing (atmospheric correction)
                path_a = result.copy()
                if params.get('enable_dehaze', True):
                    dehaze_strength = params.get('dehaze_strength', 0.8)
                    path_a = cc.dehaze(path_a, omega=dehaze_strength)
                
                # Path B: Detail enhancement  
                path_b = result.copy()
                unsharp_amount = params.get('unsharp_amount', 1.5)
                unsharp_radius = params.get('unsharp_radius', 1.0)
                path_b = cc.unsharp_mask(path_b, amount=unsharp_amount, radius=unsharp_radius)
            else:
                # Path A: Detail enhancement (primary)
                path_a = result.copy()
                unsharp_amount = params.get('unsharp_amount', 1.5)
                unsharp_radius = params.get('unsharp_radius', 1.0)
                path_a = cc.unsharp_mask(path_a, amount=unsharp_amount, radius=unsharp_radius)
                
                # Path B: Dehazing
                path_b = result.copy()
                if params.get('enable_dehaze', True):
                    dehaze_strength = params.get('dehaze_strength', 0.8)
                    path_b = cc.dehaze(path_b, omega=dehaze_strength)
            
            # Fuse the two paths
            if method == 'average':
                result = cc.average_fusion(path_a, path_b)
            elif method == 'pca':
                result = cc.pca_fusion(path_a, path_b)
            elif method == 'weighted':
                weight = params.get('fusion_balance', 0.5)
                result = cc.weighted_fusion(path_a, path_b, weight=weight)
        else:
            # Apply dehazing separately if fusion is disabled
            if params.get('enable_dehaze', True):
                dehaze_strength = params.get('dehaze_strength', 0.8)
                result = cc.dehaze(result, omega=dehaze_strength)
        
        # CLAHE
        if params.get('enable_clahe', True):
            clahe_clip = params.get('clahe_clip', 2.5)
            result = cc.apply_clahe_with_clip(result, clip_limit=clahe_clip)
        
        # Saturation enhancement
        if params.get('enable_saturation', True):
            saturation = params.get('saturation', 1.2)
            result = cc.enhance_saturation(result, saturation)
        
        return result
    
    def auto_tune_parameters(self, img):
        """Auto-tune parameters based on image characteristics"""
        params = {}
        
        # Analyze image characteristics
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        mean_intensity = np.mean(gray)
        std_intensity = np.std(gray)
        
        # Auto-tune red channel enhancement (less aggressive)
        b, g, r = cv2.split(img)
        red_mean = np.mean(r)
        blue_mean = np.mean(b)
        red_deficiency = max(1.0, (blue_mean + 10) / max(red_mean, 1))  # Reduced from +20 to +10
        params['red_scale'] = min(2.0, max(1.0, red_deficiency * 0.7))  # Reduced max from 3.0 to 2.0, and apply 0.7 factor
        
        # Auto-tune dehazing
        dark = cc.dark_channel(img)
        haze_level = np.mean(dark) / 255.0
        params['dehaze_strength'] = min(2.0, max(0.1, haze_level * 2.0))
        
        # Auto-tune saturation based on color variance
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        saturation_mean = np.mean(hsv[:, :, 1])
        params['saturation'] = max(0.8, min(2.5, 2.0 - saturation_mean / 127.5))
        
        # Auto-tune CLAHE based on contrast
        params['clahe_clip'] = max(1.0, min(4.0, 2.0 + std_intensity / 50.0))
        
        # Auto-tune white balance strength
        params['white_balance_strength'] = max(0.5, min(1.5, 1.2 - mean_intensity / 255.0))
        
        # Auto-tune fusion parameters
        detail_measure = cv2.Laplacian(gray, cv2.CV_64F).var()
        params['unsharp_amount'] = max(0.5, min(2.5, detail_measure / 1000.0))
        params['unsharp_radius'] = max(0.5, min(2.0, 1.0 + detail_measure / 2000.0))
        
        # Fusion balance based on haze vs detail needs
        haze_indicator = np.mean(dark) / 255.0
        detail_indicator = detail_measure / 1000.0
        params['fusion_balance'] = haze_indicator / (haze_indicator + detail_indicator + 0.1)
        
        return params
    
    def process_video(self, video_path, progress_callback, **params):
        """Process video with progress tracking"""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception("Could not open video file")
        
        # Get video properties
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Create output path
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_path = os.path.join(os.path.dirname(video_path), f"{base_name}_corrected.mp4")
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        try:
            frame_count = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Process frame
                corrected_frame = self.process_image(frame, **params)
                out.write(corrected_frame)
                
                frame_count += 1
                
                # Update progress
                if progress_callback:
                    should_continue = progress_callback(frame_count, total_frames, corrected_frame)
                    if not should_continue:
                        break
                        
        finally:
            cap.release()
            out.release()
        
        return output_path

class ColorCorrectionGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Submarine Color Correction Tool")
        self.root.geometry("1200x900")
        
        # Initialize variables
        self.image_paths = []
        self.current_index = 0
        self.original_image = None
        self.corrected_image = None
        self.zoom_factor = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.rotation_angle = 0  # Track rotation angle
        
        # Drag data for panning
        self._drag_data = {"x": 0, "y": 0}
        
        # Initialize the processor
        self.processor = ColorCorrectionProcessor()
        
        # Configure logging
        logging.basicConfig(
            filename=f'color_correction_{int(time.time())}.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame with scrollbar
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create canvas and scrollbar for scrolling
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mouse wheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        self.frame = self.scrollable_frame
        
        # === FILE OPERATIONS ===
        file_frame = tk.LabelFrame(self.frame, text="File Operations", padx=5, pady=5)
        file_frame.grid(row=0, column=0, columnspan=3, sticky='ew', pady=(0,10))
        
        self.btn_select_folder = tk.Button(file_frame, text="Select Folder", command=self.select_folder)
        self.btn_select_folder.grid(row=0, column=0, padx=5)
        
        self.btn_select_video = tk.Button(file_frame, text="Select Video", command=self.select_video)
        self.btn_select_video.grid(row=0, column=1, padx=5)
        
        self.btn_view_log = tk.Button(file_frame, text="View Log", command=self.view_log)
        self.btn_view_log.grid(row=0, column=2, padx=5)
        
        # === IMAGE DISPLAY ===
        self.left_canvas = tk.Canvas(self.frame, width=400, height=300, bg="black", cursor="hand2")
        self.left_canvas.grid(row=1, column=0, padx=5)
        
        self.right_canvas = tk.Canvas(self.frame, width=400, height=300, bg="black", cursor="hand2")
        self.right_canvas.grid(row=1, column=1, columnspan=2, padx=5)
        
        # Bind pan events
        self.left_canvas.bind("<Button-1>", self._on_pan_start_left)
        self.left_canvas.bind("<B1-Motion>", self._on_pan_move_left)
        self.left_canvas.bind("<ButtonRelease-1>", self._on_pan_end)
        
        self.right_canvas.bind("<Button-1>", self._on_pan_start_right)
        self.right_canvas.bind("<B1-Motion>", self._on_pan_move_right)
        self.right_canvas.bind("<ButtonRelease-1>", self._on_pan_end)
        
        # === NAVIGATION & VIEW ===
        nav_frame = tk.LabelFrame(self.frame, text="Navigation & View", padx=5, pady=5)
        nav_frame.grid(row=2, column=0, columnspan=3, sticky='ew', pady=(5,10))
        
        self.btn_prev = tk.Button(nav_frame, text="<< Previous", command=self.prev_image)
        self.btn_prev.grid(row=0, column=0, sticky='ew', padx=2)
        
        self.btn_next = tk.Button(nav_frame, text="Next >>", command=self.next_image)
        self.btn_next.grid(row=0, column=1, sticky='ew', padx=2)
        
        self.btn_zoom_in = tk.Button(nav_frame, text="Zoom In", command=self.zoom_in)
        self.btn_zoom_in.grid(row=0, column=2, sticky='ew', padx=2)
        
        self.btn_zoom_out = tk.Button(nav_frame, text="Zoom Out", command=self.zoom_out)
        self.btn_zoom_out.grid(row=0, column=3, sticky='ew', padx=2)
        
        self.btn_zoom_reset = tk.Button(nav_frame, text="Reset View", command=self.reset_view)
        self.btn_zoom_reset.grid(row=0, column=4, sticky='ew', padx=2)
        
        self.btn_rotate_left = tk.Button(nav_frame, text="Rotate ↺", command=self.rotate_left)
        self.btn_rotate_left.grid(row=0, column=5, sticky='ew', padx=2)
        
        self.btn_rotate_right = tk.Button(nav_frame, text="Rotate ↻", command=self.rotate_right)
        self.btn_rotate_right.grid(row=0, column=6, sticky='ew', padx=2)
        
        # Configure column weights for equal distribution
        for i in range(7):
            nav_frame.columnconfigure(i, weight=1)

        # === PROCESSING CONTROLS ===
        proc_frame = tk.LabelFrame(self.frame, text="Processing Controls", padx=5, pady=5)
        proc_frame.grid(row=3, column=0, columnspan=3, sticky='ew', pady=(0,10))
        
        self.btn_apply_correction = tk.Button(proc_frame, text="Apply Color Correction", command=self.apply_correction, bg='lightblue')
        self.btn_apply_correction.grid(row=0, column=0, sticky='ew', padx=2)
        
        self.btn_auto_tune = tk.Button(proc_frame, text="Auto Tune", command=self.auto_tune_parameters, bg='lightgreen')
        self.btn_auto_tune.grid(row=0, column=1, sticky='ew', padx=2)
        
        self.btn_reset_defaults = tk.Button(proc_frame, text="Reset Defaults", command=self.reset_parameters, bg='lightyellow')
        self.btn_reset_defaults.grid(row=0, column=2, sticky='ew', padx=2)
        
        self.btn_save = tk.Button(proc_frame, text="Save Corrected", command=self.save_corrected, bg='lightcoral')
        self.btn_save.grid(row=0, column=3, sticky='ew', padx=2)
        
        # Configure column weights for equal distribution
        for i in range(4):
            proc_frame.columnconfigure(i, weight=1)

        # === TABBED PARAMETER INTERFACE ===
        notebook = ttk.Notebook(self.frame)
        notebook.grid(row=4, column=0, columnspan=3, sticky='ew', pady=(0,5))
        
        # === WHITE BALANCE TAB ===
        wb_tab = ttk.Frame(notebook)
        notebook.add(wb_tab, text="White Balance")
        
        self.enable_white_balance = tk.BooleanVar(value=True)
        tk.Checkbutton(wb_tab, text="Enable White Balance", variable=self.enable_white_balance).grid(row=0, column=0, sticky='w', padx=5, pady=5)
        
        tk.Label(wb_tab, text="Method:").grid(row=0, column=1, sticky='w', padx=(10,5))
        method_frame = tk.Frame(wb_tab)
        method_frame.grid(row=0, column=2, sticky='w', padx=5)
        
        self.wb_method = tk.StringVar(value="robust")
        tk.Radiobutton(method_frame, text="Robust", variable=self.wb_method, value="robust").pack(side=tk.LEFT)
        tk.Radiobutton(method_frame, text="White Patch", variable=self.wb_method, value="white_patch").pack(side=tk.LEFT)
        tk.Radiobutton(method_frame, text="Gray World", variable=self.wb_method, value="gray_world").pack(side=tk.LEFT)

        tk.Label(wb_tab, text="Strength").grid(row=1, column=0, sticky='w', padx=5)
        self.white_balance_strength = tk.DoubleVar(value=1.0)
        tk.Scale(wb_tab, from_=0.0, to=2.0, resolution=0.1, orient=tk.HORIZONTAL, 
                variable=self.white_balance_strength).grid(row=1, column=1, columnspan=2, sticky='ew', padx=5, pady=2)

        tk.Label(wb_tab, text="Percentile Low").grid(row=2, column=0, sticky='w', padx=5)
        self.robust_lower = tk.DoubleVar(value=5)
        self.lower_scale = tk.Scale(wb_tab, from_=0, to=49, resolution=1, orient=tk.HORIZONTAL,
                variable=self.robust_lower, command=self.update_upper_min)
        self.lower_scale.grid(row=2, column=1, columnspan=2, sticky='ew', padx=5, pady=2)

        tk.Label(wb_tab, text="Percentile High").grid(row=3, column=0, sticky='w', padx=5)
        self.robust_upper = tk.DoubleVar(value=95)
        self.upper_scale = tk.Scale(wb_tab, from_=51, to=100, resolution=1, orient=tk.HORIZONTAL,
                variable=self.robust_upper, command=self.update_lower_max)
        self.upper_scale.grid(row=3, column=1, columnspan=2, sticky='ew', padx=5, pady=2)

        tk.Label(wb_tab, text="Retinex Percentile").grid(row=4, column=0, sticky='w', padx=5)
        self.retinex_percentile = tk.DoubleVar(value=1.0)
        tk.Scale(wb_tab, from_=0.1, to=10.0, resolution=0.1, orient=tk.HORIZONTAL, 
                variable=self.retinex_percentile).grid(row=4, column=1, columnspan=2, sticky='ew', padx=5, pady=2)
        
        wb_tab.columnconfigure(1, weight=1)
        wb_tab.columnconfigure(2, weight=1)

        # === BASIC CORRECTIONS TAB ===
        basic_tab = ttk.Frame(notebook)
        notebook.add(basic_tab, text="Basic")
        
        self.enable_red_channel = tk.BooleanVar(value=True)
        tk.Checkbutton(basic_tab, text="Red Channel Enhancement", variable=self.enable_red_channel).grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.red_scale = tk.DoubleVar(value=1.3)
        tk.Scale(basic_tab, from_=1.0, to=3.0, resolution=0.1, orient=tk.HORIZONTAL, 
                variable=self.red_scale).grid(row=0, column=1, columnspan=2, sticky='ew', padx=5, pady=2)

        self.enable_dehaze = tk.BooleanVar(value=True)
        tk.Checkbutton(basic_tab, text="Dehazing", variable=self.enable_dehaze).grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.dehaze_strength = tk.DoubleVar(value=0.8)
        tk.Scale(basic_tab, from_=0.1, to=2.0, resolution=0.1, orient=tk.HORIZONTAL, 
                variable=self.dehaze_strength).grid(row=1, column=1, columnspan=2, sticky='ew', padx=5, pady=2)

        self.enable_saturation = tk.BooleanVar(value=True)
        tk.Checkbutton(basic_tab, text="Saturation", variable=self.enable_saturation).grid(row=2, column=0, sticky='w', padx=5, pady=5)
        self.saturation = tk.DoubleVar(value=1.2)
        tk.Scale(basic_tab, from_=0.5, to=3.0, resolution=0.1, orient=tk.HORIZONTAL, 
                variable=self.saturation).grid(row=2, column=1, columnspan=2, sticky='ew', padx=5, pady=2)
        
        self.enable_clahe = tk.BooleanVar(value=True)
        tk.Checkbutton(basic_tab, text="CLAHE (Adaptive Histogram Equalization)", variable=self.enable_clahe).grid(row=3, column=0, sticky='w', padx=5, pady=5)
        tk.Label(basic_tab, text="CLAHE Clip Limit").grid(row=3, column=1, sticky='w', padx=(10,5))
        self.clahe_clip = tk.DoubleVar(value=2.5)
        tk.Scale(basic_tab, from_=1.0, to=5.0, resolution=0.1, orient=tk.HORIZONTAL, 
                variable=self.clahe_clip).grid(row=3, column=2, sticky='ew', padx=5, pady=2)
        
        basic_tab.columnconfigure(1, weight=1)
        basic_tab.columnconfigure(2, weight=1)

        # === ADVANCED TAB (includes Fusion) ===
        advanced_tab = ttk.Frame(notebook)
        notebook.add(advanced_tab, text="Advanced")
        
        self.enable_fusion = tk.BooleanVar(value=False)
        tk.Checkbutton(advanced_tab, text="Enable Fusion Processing", variable=self.enable_fusion).grid(row=0, column=0, sticky='w', padx=5, pady=5)
        
        tk.Label(advanced_tab, text="Method:").grid(row=0, column=1, sticky='w', padx=(10,5))
        fusion_method_frame = tk.Frame(advanced_tab)
        fusion_method_frame.grid(row=0, column=2, sticky='w', padx=5)
        
        self.fusion_method = tk.StringVar(value="average")
        tk.Radiobutton(fusion_method_frame, text="Average", variable=self.fusion_method, value="average").pack(side=tk.LEFT)
        tk.Radiobutton(fusion_method_frame, text="PCA", variable=self.fusion_method, value="pca").pack(side=tk.LEFT)
        tk.Radiobutton(fusion_method_frame, text="Weighted", variable=self.fusion_method, value="weighted").pack(side=tk.LEFT)

        # Fusion parameters
        tk.Label(advanced_tab, text="Sharpen Amount").grid(row=1, column=0, sticky='w', padx=5)
        self.unsharp_amount = tk.DoubleVar(value=1.5)
        tk.Scale(advanced_tab, from_=0.0, to=3.0, resolution=0.1, orient=tk.HORIZONTAL, 
                variable=self.unsharp_amount).grid(row=1, column=1, columnspan=2, sticky='ew', padx=5, pady=2)

        tk.Label(advanced_tab, text="Sharpen Radius").grid(row=2, column=0, sticky='w', padx=5)
        self.unsharp_radius = tk.DoubleVar(value=1.0)
        tk.Scale(advanced_tab, from_=0.5, to=3.0, resolution=0.1, orient=tk.HORIZONTAL, 
                variable=self.unsharp_radius).grid(row=2, column=1, columnspan=2, sticky='ew', padx=5, pady=2)

        tk.Label(advanced_tab, text="Balance (Dehaze/Detail)").grid(row=3, column=0, sticky='w', padx=5)
        self.fusion_balance = tk.DoubleVar(value=0.5)
        tk.Scale(advanced_tab, from_=0.0, to=1.0, resolution=0.01, orient=tk.HORIZONTAL, 
                variable=self.fusion_balance).grid(row=3, column=1, columnspan=2, sticky='ew', padx=5, pady=2)
        
        advanced_tab.columnconfigure(1, weight=1)
        advanced_tab.columnconfigure(2, weight=1)

    def _on_pan_start_left(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _on_pan_move_left(self, event):
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        self.pan_x += dx
        self.pan_y += dy
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
        self.display_images()

    def _on_pan_start_right(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _on_pan_move_right(self, event):
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        self.pan_x += dx
        self.pan_y += dy
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
        self.display_images()

    def _on_pan_end(self, event):
        pass

    def reset_view(self):
        """Reset zoom and pan to default values"""
        self.zoom_factor = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.display_images()

    def rotate_left(self):
        """Rotate image 90 degrees counter-clockwise"""
        self.rotation_angle = (self.rotation_angle - 90) % 360
        self.display_images()

    def rotate_right(self):
        """Rotate image 90 degrees clockwise"""
        self.rotation_angle = (self.rotation_angle + 90) % 360
        self.display_images()

    def update_upper_min(self, val):
        lower = int(float(val))
        self.upper_scale.config(from_=lower + 1)
        if self.robust_upper.get() <= lower:
            self.robust_upper.set(lower + 1)

    def update_lower_max(self, val):
        upper = int(float(val))
        self.lower_scale.config(to=upper - 1)
        if self.robust_lower.get() >= upper:
            self.robust_lower.set(upper - 1)

    def select_folder(self):
        folder = filedialog.askdirectory()
        if not folder:
            return
        self.image_paths = [
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if f.lower().endswith(IMAGE_EXTENSIONS)
        ]
        if not self.image_paths:
            messagebox.showwarning("Warning", "No supported image files found!")
            return
        self.current_index = 0
        self.rotation_angle = 0  # Reset rotation when selecting new folder
        self.load_current_image()

    def load_current_image(self):
        if not self.image_paths:
            return
        
        try:
            image_path = self.image_paths[self.current_index]
            self.original_image = cv2.imread(image_path)
            if self.original_image is None:
                messagebox.showerror("Error", f"Could not load image: {image_path}")
                return
            
            # Convert BGR to RGB for display
            self.original_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
            self.corrected_image = None
            self.zoom_factor = 1.0
            self.pan_x = 0
            self.pan_y = 0
            
            self.display_images()
            
            # Update window title
            filename = os.path.basename(image_path)
            self.root.title(f"Submarine Color Correction - {filename} ({self.current_index + 1}/{len(self.image_paths)})")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {str(e)}")

    def display_images(self):
        if self.original_image is None:
            return
        
        try:
            # Apply rotation to both images
            def rotate_image(image):
                if self.rotation_angle == 0:
                    return image
                elif self.rotation_angle == 90:
                    return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
                elif self.rotation_angle == 180:
                    return cv2.rotate(image, cv2.ROTATE_180)
                elif self.rotation_angle == 270:
                    return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
                return image
            
            original_rotated = rotate_image(self.original_image)
            
            # Convert and display original image
            original_pil = Image.fromarray(original_rotated)
            original_resized = self.resize_and_center_image(original_pil, self.left_canvas)
            original_photo = ImageTk.PhotoImage(original_resized)
            
            self.left_canvas.delete("all")
            # Apply pan offset to image position
            canvas_center_x = (self.left_canvas.winfo_width() or 400) // 2
            canvas_center_y = (self.left_canvas.winfo_height() or 300) // 2
            img_x = canvas_center_x + self.pan_x
            img_y = canvas_center_y + self.pan_y
            self.left_canvas.create_image(img_x, img_y, image=original_photo)
            self.left_canvas.image = original_photo  # Keep a reference
            self.left_canvas.create_text(canvas_center_x, 10, text="Original", fill="white", font=("Arial", 12, "bold"))
            
            # Display corrected image if available
            if self.corrected_image is not None:
                corrected_rotated = rotate_image(self.corrected_image)
                corrected_pil = Image.fromarray(corrected_rotated)
                corrected_resized = self.resize_and_center_image(corrected_pil, self.right_canvas)
                corrected_photo = ImageTk.PhotoImage(corrected_resized)
                
                self.right_canvas.delete("all")
                # Apply pan offset to image position
                canvas_center_x = (self.right_canvas.winfo_width() or 400) // 2
                canvas_center_y = (self.right_canvas.winfo_height() or 300) // 2
                img_x = canvas_center_x + self.pan_x
                img_y = canvas_center_y + self.pan_y
                self.right_canvas.create_image(img_x, img_y, image=corrected_photo)
                self.right_canvas.image = corrected_photo  # Keep a reference
                self.right_canvas.create_text(canvas_center_x, 10, text="Corrected", fill="white", font=("Arial", 12, "bold"))
            else:
                self.right_canvas.delete("all")
                canvas_center_x = (self.right_canvas.winfo_width() or 400) // 2
                canvas_center_y = (self.right_canvas.winfo_height() or 300) // 2
                self.right_canvas.create_text(canvas_center_x, canvas_center_y, text="No corrected image", fill="gray", font=("Arial", 14))
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to display images: {str(e)}")

    def resize_and_center_image(self, pil_image, canvas):
        canvas_width = canvas.winfo_width() or 400
        canvas_height = canvas.winfo_height() or 300
        
        # First, calculate the base size to fit the canvas
        original_width = pil_image.width
        original_height = pil_image.height
        
        # Calculate base size that fits in canvas (this is our 1.0 zoom level)
        max_width = canvas_width - 20
        max_height = canvas_height - 40
        
        base_ratio = min(max_width / original_width, max_height / original_height, 1.0)
        base_width = int(original_width * base_ratio)
        base_height = int(original_height * base_ratio)
        
        # Now apply zoom factor to the base size
        final_width = int(base_width * self.zoom_factor)
        final_height = int(base_height * self.zoom_factor)
        
        if final_width > 0 and final_height > 0:
            pil_image = pil_image.resize((final_width, final_height), Image.LANCZOS)
        
        return pil_image

    def prev_image(self):
        if not self.image_paths:
            return
        self.current_index = (self.current_index - 1) % len(self.image_paths)
        self.rotation_angle = 0  # Reset rotation when navigating
        self.load_current_image()

    def next_image(self):
        if not self.image_paths:
            return
        self.current_index = (self.current_index + 1) % len(self.image_paths)
        self.rotation_angle = 0  # Reset rotation when navigating
        self.load_current_image()

    def zoom_in(self):
        self.zoom_factor = min(self.zoom_factor * 1.1, 5.0)
        self.display_images()

    def zoom_out(self):
        self.zoom_factor = max(self.zoom_factor / 1.1, 0.2)
        # Reset pan when zooming out to normal size
        if self.zoom_factor <= 1.0:
            self.pan_x = 0
            self.pan_y = 0
        self.display_images()

    def apply_correction(self):
        if self.original_image is None:
            messagebox.showwarning("Warning", "Please select an image first!")
            return
        
        try:
            logger = logging.getLogger(__name__)
            
            # Collect parameters
            params = {
                'enable_white_balance': self.enable_white_balance.get(),
                'wb_method': self.wb_method.get(),
                'white_balance_strength': self.white_balance_strength.get(),
                'robust_lower': self.robust_lower.get(),
                'robust_upper': self.robust_upper.get(),
                'retinex_percentile': self.retinex_percentile.get(),
                'enable_red_channel': self.enable_red_channel.get(),
                'red_scale': self.red_scale.get(),
                'enable_dehaze': self.enable_dehaze.get(),
                'dehaze_strength': self.dehaze_strength.get(),
                'enable_saturation': self.enable_saturation.get(),
                'saturation': self.saturation.get(),
                'enable_clahe': self.enable_clahe.get(),
                'clahe_clip': self.clahe_clip.get(),
                'enable_fusion': self.enable_fusion.get(),
                'fusion_method': self.fusion_method.get(),
                'unsharp_amount': self.unsharp_amount.get(),
                'unsharp_radius': self.unsharp_radius.get(),
                'fusion_balance': self.fusion_balance.get()
            }
            
            logger.info(f"Applying correction with parameters: {params}")
            
            # Convert RGB back to BGR for processing
            bgr_image = cv2.cvtColor(self.original_image, cv2.COLOR_RGB2BGR)
            
            # Apply corrections
            corrected_bgr = self.processor.process_image(bgr_image, **params)
            
            # Convert back to RGB for display
            self.corrected_image = cv2.cvtColor(corrected_bgr, cv2.COLOR_BGR2RGB)
            
            self.display_images()
            # messagebox.showinfo("Success", "Color correction applied!")  # Removed success popup
            
        except Exception as e:
            logger.error(f"Error applying correction: {str(e)}")
            messagebox.showerror("Error", f"Failed to apply correction: {str(e)}")

    def auto_tune_parameters(self):
        """Auto-tune parameters based on image characteristics"""
        if self.original_image is None:
            messagebox.showwarning("Warning", "Please select an image first!")
            return
        
        try:
            logger = logging.getLogger(__name__)
            logger.info("Starting auto-tune parameters")
            
            # Convert RGB to BGR for analysis
            bgr_image = cv2.cvtColor(self.original_image, cv2.COLOR_RGB2BGR)
            
            # Auto-tune parameters
            tuned_params = self.processor.auto_tune_parameters(bgr_image)
            
            # Update UI with tuned parameters
            if 'red_scale' in tuned_params:
                self.red_scale.set(tuned_params['red_scale'])
            if 'dehaze_strength' in tuned_params:
                self.dehaze_strength.set(tuned_params['dehaze_strength'])
            if 'saturation' in tuned_params:
                self.saturation.set(tuned_params['saturation'])
            if 'clahe_clip' in tuned_params:
                self.clahe_clip.set(tuned_params['clahe_clip'])
            if 'white_balance_strength' in tuned_params:
                self.white_balance_strength.set(tuned_params['white_balance_strength'])
            if 'fusion_balance' in tuned_params:
                self.fusion_balance.set(tuned_params['fusion_balance'])
            if 'unsharp_amount' in tuned_params:
                self.unsharp_amount.set(tuned_params['unsharp_amount'])
            if 'unsharp_radius' in tuned_params:
                self.unsharp_radius.set(tuned_params['unsharp_radius'])
            
            logger.info(f"Auto-tuned parameters: {tuned_params}")
            # messagebox.showinfo("Success", "Parameters auto-tuned based on image analysis!")  # Removed success popup
            
            # Automatically apply correction after auto-tuning
            self.apply_correction()
            
        except Exception as e:
            logger.error(f"Error in auto-tune: {str(e)}")
            messagebox.showerror("Error", f"Failed to auto-tune parameters: {str(e)}")

    def reset_parameters(self):
        """Reset all parameters to default values"""
        # White balance
        self.enable_white_balance.set(True)
        self.wb_method.set("robust")
        self.white_balance_strength.set(1.0)
        self.robust_lower.set(5)
        self.robust_upper.set(95)
        self.retinex_percentile.set(1.0)
        
        # Basic corrections
        self.enable_red_channel.set(True)
        self.red_scale.set(1.3)
        self.enable_dehaze.set(True)
        self.dehaze_strength.set(0.8)
        self.enable_saturation.set(True)
        self.saturation.set(1.2)
        
        # Advanced processing
        self.enable_clahe.set(True)
        self.clahe_clip.set(2.5)
        
        # Fusion processing
        self.enable_fusion.set(False)
        self.fusion_method.set("average")
        self.unsharp_amount.set(1.5)
        self.unsharp_radius.set(1.0)
        self.fusion_balance.set(0.5)
        
        # messagebox.showinfo("Success", "All parameters reset to defaults!")  # Removed success popup

    def save_corrected(self):
        if self.corrected_image is None:
            messagebox.showwarning("Warning", "No corrected image to save!")
            return
        
        try:
            # Get current image path and create output filename
            current_path = self.image_paths[self.current_index]
            directory = os.path.dirname(current_path)
            filename = os.path.basename(current_path)
            name, ext = os.path.splitext(filename)
            
            # Add rotation suffix if rotated
            rotation_suffix = f"_rot{self.rotation_angle}" if self.rotation_angle != 0 else ""
            output_filename = f"{name}_corrected{rotation_suffix}{ext}"
            output_path = os.path.join(directory, output_filename)
            
            # Apply rotation to corrected image for saving
            image_to_save = self.corrected_image
            if self.rotation_angle != 0:
                if self.rotation_angle == 90:
                    image_to_save = cv2.rotate(image_to_save, cv2.ROTATE_90_COUNTERCLOCKWISE)
                elif self.rotation_angle == 180:
                    image_to_save = cv2.rotate(image_to_save, cv2.ROTATE_180)
                elif self.rotation_angle == 270:
                    image_to_save = cv2.rotate(image_to_save, cv2.ROTATE_90_CLOCKWISE)
            
            # Convert RGB to BGR for saving
            bgr_image = cv2.cvtColor(image_to_save, cv2.COLOR_RGB2BGR)
            cv2.imwrite(output_path, bgr_image)
            
            messagebox.showinfo("Success", f"Image saved as: {output_filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save image: {str(e)}")

    def select_video(self):
        video_path = filedialog.askopenfilename(
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv")]
        )
        if not video_path:
            return
        
        try:
            self.process_video(video_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process video: {str(e)}")

    def process_video(self, video_path):
        """Process video with progress tracking"""
        # Create progress window
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Processing Video")
        progress_window.geometry("500x200")
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        # Progress variables
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(progress_window, variable=progress_var, maximum=100)
        progress_bar.pack(pady=20, padx=20, fill=tk.X)
        
        # Preview frame
        preview_frame = tk.Frame(progress_window, bg='black')
        preview_frame.pack(pady=10, padx=20, fill=tk.X)
        preview = tk.Label(preview_frame, bg='black')
        preview.pack()
        
        progress_label = ttk.Label(progress_window, text="Processing frames...")
        progress_label.pack(pady=5)
        
        # Cancel button
        cancel_requested = threading.Event()
        cancel_btn = tk.Button(progress_window, text="Cancel", 
                              command=lambda: cancel_requested.set())
        cancel_btn.pack(pady=5)
        
        def process_video_thread():
            try:
                # Collect parameters
                params = {
                    'enable_white_balance': self.enable_white_balance.get(),
                    'wb_method': self.wb_method.get(),
                    'white_balance_strength': self.white_balance_strength.get(),
                    'robust_lower': self.robust_lower.get(),
                    'robust_upper': self.robust_upper.get(),
                    'retinex_percentile': self.retinex_percentile.get(),
                    'enable_red_channel': self.enable_red_channel.get(),
                    'red_scale': self.red_scale.get(),
                    'enable_dehaze': self.enable_dehaze.get(),
                    'dehaze_strength': self.dehaze_strength.get(),
                    'enable_saturation': self.enable_saturation.get(),
                    'saturation': self.saturation.get(),
                    'enable_clahe': self.enable_clahe.get(),
                    'clahe_clip': self.clahe_clip.get(),
                    'enable_fusion': self.enable_fusion.get(),
                    'fusion_method': self.fusion_method.get(),
                    'unsharp_amount': self.unsharp_amount.get(),
                    'unsharp_radius': self.unsharp_radius.get(),
                    'fusion_balance': self.fusion_balance.get()
                }
                
                # Process video with callback
                def progress_callback(frame_count, total_frames, preview_frame=None):
                    progress = (frame_count / total_frames) * 100
                    progress_var.set(progress)
                    progress_label.config(text=f"Processing: {frame_count}/{total_frames} frames ({progress:.1f}%)")
                    
                    # Update preview if provided
                    if preview_frame is not None:
                        try:
                            # Convert BGR to RGB for display
                            rgb_frame = cv2.cvtColor(preview_frame, cv2.COLOR_BGR2RGB)
                            # Resize for preview
                            height, width = rgb_frame.shape[:2]
                            if width > 300:
                                ratio = 300 / width
                                new_width = 300
                                new_height = int(height * ratio)
                                rgb_frame = cv2.resize(rgb_frame, (new_width, new_height))
                            
                            pil_image = Image.fromarray(rgb_frame)
                            photo = ImageTk.PhotoImage(pil_image)
                            preview.configure(image=photo)
                            preview.image = photo
                        except:
                            pass  # Ignore preview errors
                    
                    progress_window.update_idletasks()
                    return not cancel_requested.is_set()
                
                output_path = self.processor.process_video(video_path, progress_callback, **params)
                
                if not cancel_requested.is_set():
                    progress_window.destroy()
                    messagebox.showinfo("Success", f"Video processed successfully!\nSaved as: {output_path}")
                else:
                    progress_window.destroy()
                    messagebox.showinfo("Cancelled", "Video processing was cancelled.")
                    
            except Exception as e:
                progress_window.destroy()
                messagebox.showerror("Error", f"Video processing failed: {str(e)}")
        
        # Start processing in separate thread
        thread = threading.Thread(target=process_video_thread)
        thread.daemon = True
        thread.start()

    def view_log(self):
        """Open log file in default text editor"""
        try:
            # Find the most recent log file
            log_files = [f for f in os.listdir('.') if f.startswith('color_correction_') and f.endswith('.log')]
            if not log_files:
                messagebox.showinfo("Info", "No log files found.")
                return
            
            # Get the most recent log file
            log_files.sort(reverse=True)
            most_recent_log = log_files[0]
            
            # Open with default text editor
            os.startfile(most_recent_log)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open log file: {str(e)}")

def main():
    root = tk.Tk()
    app = ColorCorrectionGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
