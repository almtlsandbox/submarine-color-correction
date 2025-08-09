"""
Comprehensive parameter control panel with all settings.
Modular widget for managing all processing parameters with tabbed interface.
"""
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional
import logging

from models.processing_params import ProcessingParameters
from services.logger_service import get_logger


class ParameterPanel:
    """Comprehensive parameter control panel with tabbed interface."""
    
    def __init__(self, parent: tk.Widget, params: ProcessingParameters, 
                 on_change_callback: Optional[Callable] = None):
        self.parent = parent
        self.params = params
        self.on_change_callback = on_change_callback
        self.logger = get_logger('parameter_panel')
        
        # Variable holders for UI controls
        self._create_variables()
        
        # Create the UI
        self.create_ui()
        
        # Initialize with current parameters
        self.update_ui_from_parameters()
    
    def _create_variables(self):
        """Create tkinter variables for all parameters."""
        # White Balance variables
        self.enable_white_balance_var = tk.BooleanVar()
        self.wb_method_var = tk.StringVar()
        self.white_balance_strength_var = tk.DoubleVar()
        self.robust_lower_var = tk.DoubleVar()
        self.robust_upper_var = tk.DoubleVar()
        self.retinex_percentile_var = tk.DoubleVar()
        
        # Basic Corrections variables
        self.enable_red_channel_var = tk.BooleanVar()
        self.red_scale_var = tk.DoubleVar()
        self.enable_dehaze_var = tk.BooleanVar()
        self.dehaze_strength_var = tk.DoubleVar()
        self.enable_saturation_var = tk.BooleanVar()
        self.saturation_var = tk.DoubleVar()
        
        # Advanced Processing variables
        self.enable_clahe_var = tk.BooleanVar()
        self.clahe_clip_var = tk.DoubleVar()
        
        # Fusion Processing variables
        self.enable_fusion_var = tk.BooleanVar()
        self.fusion_method_var = tk.StringVar()
        self.unsharp_amount_var = tk.DoubleVar()
        self.unsharp_radius_var = tk.DoubleVar()
        self.fusion_balance_var = tk.DoubleVar()
        
        # Green Water variables
        self.water_type_var = tk.StringVar()
        self.green_water_detection_var = tk.BooleanVar()
        self.magenta_compensation_var = tk.DoubleVar()
        self.enhanced_dehazing_var = tk.BooleanVar()
        self.turbidity_compensation_var = tk.DoubleVar()
    
    def create_ui(self):
        """Create the complete parameter interface."""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.parent)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create tabs
        self._create_white_balance_tab()
        self._create_basic_tab()
        self._create_advanced_tab()
        self._create_fusion_tab()
        self._create_green_water_tab()
    
    def _create_white_balance_tab(self):
        """Create white balance parameter tab."""
        wb_tab = ttk.Frame(self.notebook)
        self.notebook.add(wb_tab, text="White Balance")
        
        row = 0
        
        # Enable white balance
        tk.Checkbutton(wb_tab, text="Enable White Balance", 
                      variable=self.enable_white_balance_var,
                      command=self._on_parameter_change).grid(row=row, column=0, sticky='w', padx=5, pady=5)
        
        # Method selection
        tk.Label(wb_tab, text="Method:").grid(row=row, column=1, sticky='w', padx=(10,5))
        method_frame = tk.Frame(wb_tab)
        method_frame.grid(row=row, column=2, sticky='w', padx=5)
        
        tk.Radiobutton(method_frame, text="Robust", variable=self.wb_method_var, 
                      value="robust", command=self._on_parameter_change).pack(side=tk.LEFT)
        tk.Radiobutton(method_frame, text="White Patch", variable=self.wb_method_var, 
                      value="white_patch", command=self._on_parameter_change).pack(side=tk.LEFT)
        tk.Radiobutton(method_frame, text="Gray World", variable=self.wb_method_var, 
                      value="gray_world", command=self._on_parameter_change).pack(side=tk.LEFT)
        row += 1
        
        # Strength
        tk.Label(wb_tab, text="Strength").grid(row=row, column=0, sticky='w', padx=5)
        strength_scale = tk.Scale(wb_tab, from_=0.0, to=2.0, resolution=0.1, orient=tk.HORIZONTAL,
                                 variable=self.white_balance_strength_var, command=self._on_parameter_change)
        strength_scale.grid(row=row, column=1, columnspan=2, sticky='ew', padx=5, pady=2)
        row += 1
        
        # Percentile Low
        tk.Label(wb_tab, text="Percentile Low").grid(row=row, column=0, sticky='w', padx=5)
        self.lower_scale = tk.Scale(wb_tab, from_=0, to=49, resolution=1, orient=tk.HORIZONTAL,
                                   variable=self.robust_lower_var, command=self._update_upper_min)
        self.lower_scale.grid(row=row, column=1, columnspan=2, sticky='ew', padx=5, pady=2)
        row += 1
        
        # Percentile High
        tk.Label(wb_tab, text="Percentile High").grid(row=row, column=0, sticky='w', padx=5)
        self.upper_scale = tk.Scale(wb_tab, from_=51, to=100, resolution=1, orient=tk.HORIZONTAL,
                                   variable=self.robust_upper_var, command=self._update_lower_max)
        self.upper_scale.grid(row=row, column=1, columnspan=2, sticky='ew', padx=5, pady=2)
        row += 1
        
        # Retinex Percentile
        tk.Label(wb_tab, text="Retinex Percentile").grid(row=row, column=0, sticky='w', padx=5)
        tk.Scale(wb_tab, from_=0.1, to=10.0, resolution=0.1, orient=tk.HORIZONTAL,
                variable=self.retinex_percentile_var, command=self._on_parameter_change).grid(
                row=row, column=1, columnspan=2, sticky='ew', padx=5, pady=2)
        
        # Configure column weights
        wb_tab.columnconfigure(1, weight=1)
        wb_tab.columnconfigure(2, weight=1)
    
    def _create_basic_tab(self):
        """Create basic corrections tab."""
        basic_tab = ttk.Frame(self.notebook)
        self.notebook.add(basic_tab, text="Basic")
        
        row = 0
        
        # Red channel enhancement
        tk.Checkbutton(basic_tab, text="Red Channel Enhancement", 
                      variable=self.enable_red_channel_var,
                      command=self._on_parameter_change).grid(row=row, column=0, sticky='w', padx=5, pady=5)
        tk.Scale(basic_tab, from_=1.0, to=3.0, resolution=0.1, orient=tk.HORIZONTAL,
                variable=self.red_scale_var, command=self._on_parameter_change).grid(
                row=row, column=1, columnspan=2, sticky='ew', padx=5, pady=2)
        row += 1
        
        # Dehazing
        tk.Checkbutton(basic_tab, text="Dehazing", 
                      variable=self.enable_dehaze_var,
                      command=self._on_parameter_change).grid(row=row, column=0, sticky='w', padx=5, pady=5)
        tk.Scale(basic_tab, from_=0.1, to=2.0, resolution=0.1, orient=tk.HORIZONTAL,
                variable=self.dehaze_strength_var, command=self._on_parameter_change).grid(
                row=row, column=1, columnspan=2, sticky='ew', padx=5, pady=2)
        row += 1
        
        # Saturation
        tk.Checkbutton(basic_tab, text="Saturation", 
                      variable=self.enable_saturation_var,
                      command=self._on_parameter_change).grid(row=row, column=0, sticky='w', padx=5, pady=5)
        tk.Scale(basic_tab, from_=0.5, to=3.0, resolution=0.1, orient=tk.HORIZONTAL,
                variable=self.saturation_var, command=self._on_parameter_change).grid(
                row=row, column=1, columnspan=2, sticky='ew', padx=5, pady=2)
        row += 1
        
        # CLAHE
        tk.Checkbutton(basic_tab, text="CLAHE (Adaptive Histogram Equalization)", 
                      variable=self.enable_clahe_var,
                      command=self._on_parameter_change).grid(row=row, column=0, sticky='w', padx=5, pady=5)
        row += 1
        
        tk.Label(basic_tab, text="CLAHE Clip Limit").grid(row=row, column=0, sticky='w', padx=5)
        tk.Scale(basic_tab, from_=1.0, to=5.0, resolution=0.1, orient=tk.HORIZONTAL,
                variable=self.clahe_clip_var, command=self._on_parameter_change).grid(
                row=row, column=1, columnspan=2, sticky='ew', padx=5, pady=2)
        
        # Configure column weights
        basic_tab.columnconfigure(1, weight=1)
        basic_tab.columnconfigure(2, weight=1)
    
    def _create_advanced_tab(self):
        """Create advanced processing tab."""
        advanced_tab = ttk.Frame(self.notebook)
        self.notebook.add(advanced_tab, text="Advanced")
        
        # Note about fusion
        note_frame = tk.Frame(advanced_tab, bg='lightgray')
        note_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(note_frame, text="💡 Advanced settings for fine-tuning processing algorithms", 
                bg='lightgray', font=('Arial', 9, 'italic')).pack(pady=5)
        
        # Processing method selection
        method_frame = tk.LabelFrame(advanced_tab, text="Processing Method", padx=5, pady=5)
        method_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Radiobutton(method_frame, text="Standard Processing", 
                      value=False, variable=self.enable_fusion_var,
                      command=self._on_parameter_change).pack(anchor='w')
        tk.Radiobutton(method_frame, text="Fusion Processing (Advanced)", 
                      value=True, variable=self.enable_fusion_var,
                      command=self._on_parameter_change).pack(anchor='w')
        
        # Info about methods
        info_frame = tk.Frame(advanced_tab)
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        info_text = """Standard: Apply corrections sequentially
Fusion: Combine multiple processing paths for better results"""
        tk.Label(info_frame, text=info_text, font=('Arial', 8), 
                justify=tk.LEFT, fg='gray').pack(anchor='w')
    
    def _create_fusion_tab(self):
        """Create fusion processing tab."""
        fusion_tab = ttk.Frame(self.notebook)
        self.notebook.add(fusion_tab, text="Fusion")
        
        row = 0
        
        # Fusion method
        tk.Label(fusion_tab, text="Fusion Method:").grid(row=row, column=0, sticky='w', padx=5, pady=5)
        method_frame = tk.Frame(fusion_tab)
        method_frame.grid(row=row, column=1, columnspan=2, sticky='w', padx=5)
        
        tk.Radiobutton(method_frame, text="Average", variable=self.fusion_method_var, 
                      value="average", command=self._on_parameter_change).pack(side=tk.LEFT)
        tk.Radiobutton(method_frame, text="PCA", variable=self.fusion_method_var, 
                      value="pca", command=self._on_parameter_change).pack(side=tk.LEFT)
        tk.Radiobutton(method_frame, text="Weighted", variable=self.fusion_method_var, 
                      value="weighted", command=self._on_parameter_change).pack(side=tk.LEFT)
        row += 1
        
        # Sharpen Amount
        tk.Label(fusion_tab, text="Sharpen Amount").grid(row=row, column=0, sticky='w', padx=5)
        tk.Scale(fusion_tab, from_=0.0, to=3.0, resolution=0.1, orient=tk.HORIZONTAL,
                variable=self.unsharp_amount_var, command=self._on_parameter_change).grid(
                row=row, column=1, columnspan=2, sticky='ew', padx=5, pady=2)
        row += 1
        
        # Sharpen Radius
        tk.Label(fusion_tab, text="Sharpen Radius").grid(row=row, column=0, sticky='w', padx=5)
        tk.Scale(fusion_tab, from_=0.5, to=3.0, resolution=0.1, orient=tk.HORIZONTAL,
                variable=self.unsharp_radius_var, command=self._on_parameter_change).grid(
                row=row, column=1, columnspan=2, sticky='ew', padx=5, pady=2)
        row += 1
        
        # Balance
        tk.Label(fusion_tab, text="Balance (Dehaze ← → Detail)").grid(row=row, column=0, sticky='w', padx=5)
        tk.Scale(fusion_tab, from_=0.0, to=1.0, resolution=0.01, orient=tk.HORIZONTAL,
                variable=self.fusion_balance_var, command=self._on_parameter_change).grid(
                row=row, column=1, columnspan=2, sticky='ew', padx=5, pady=2)
        
        # Configure column weights
        fusion_tab.columnconfigure(1, weight=1)
        fusion_tab.columnconfigure(2, weight=1)
    
    def _create_green_water_tab(self):
        """Create green water (lake/freshwater) parameter tab."""
        gw_tab = ttk.Frame(self.notebook)
        self.notebook.add(gw_tab, text="🌿 Green Water")
        
        row = 0
        
        # Water type selection
        ttk.Label(gw_tab, text="Water Type:").grid(row=row, column=0, sticky="w", padx=5, pady=5)
        water_type_combo = ttk.Combobox(gw_tab, textvariable=self.water_type_var, 
                                       values=["auto", "ocean", "lake"], state="readonly")
        water_type_combo.bind('<<ComboboxSelected>>', self._on_water_type_change)
        water_type_combo.grid(row=row, column=1, columnspan=2, sticky="ew", padx=5, pady=5)
        row += 1
        
        # Auto detection
        tk.Checkbutton(gw_tab, text="Enable Auto Water Type Detection", 
                      variable=self.green_water_detection_var,
                      command=self._on_parameter_change).grid(
            row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        row += 1
        
        # Separator
        ttk.Separator(gw_tab, orient='horizontal').grid(row=row, column=0, columnspan=3, 
                                                       sticky="ew", padx=5, pady=10)
        row += 1
        
        # Magenta compensation
        ttk.Label(gw_tab, text="Magenta Compensation:").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        magenta_scale = tk.Scale(gw_tab, from_=0.1, to=3.0, resolution=0.1, orient='horizontal',
                               variable=self.magenta_compensation_var, command=self._on_magenta_change)
        magenta_scale.grid(row=row, column=1, columnspan=2, sticky="ew", padx=5, pady=2)
        row += 1
        
        ttk.Label(gw_tab, text="(Reduces green cast in lake water)", 
                 font=('TkDefaultFont', 8)).grid(row=row, column=1, columnspan=2, sticky="w", padx=5)
        row += 1
        
        # Enhanced dehazing
        tk.Checkbutton(gw_tab, text="Enhanced Dehazing for Turbid Water", 
                      variable=self.enhanced_dehazing_var,
                      command=self._on_parameter_change).grid(
            row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        row += 1
        
        # Turbidity compensation
        ttk.Label(gw_tab, text="Turbidity Compensation:").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        turbidity_scale = tk.Scale(gw_tab, from_=0.5, to=3.0, resolution=0.1, orient='horizontal',
                                 variable=self.turbidity_compensation_var, command=self._on_parameter_change)
        turbidity_scale.grid(row=row, column=1, columnspan=2, sticky="ew", padx=5, pady=2)
        row += 1
        
        ttk.Label(gw_tab, text="(Compensates for backscattering in murky water)", 
                 font=('TkDefaultFont', 8)).grid(row=row, column=1, columnspan=2, sticky="w", padx=5)
        row += 1
        
        # Information text
        info_text = ("Green Water Mode optimizes for lakes and freshwater environments:\n"
                    "• Detects green-dominant images automatically\n" 
                    "• Applies magenta compensation to reduce green cast\n"
                    "• Uses lake-specific attenuation coefficients\n"
                    "• Enhanced dehazing for turbid/murky conditions")
        
        info_label = tk.Label(gw_tab, text=info_text, justify='left', wraplength=300,
                            font=('TkDefaultFont', 8), fg='#666666')
        info_label.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=10)
        
        # Configure column weights
        gw_tab.columnconfigure(1, weight=1)
        gw_tab.columnconfigure(2, weight=1)
    
    def _update_upper_min(self, val=None):
        """Update upper scale minimum based on lower value."""
        lower = int(float(self.robust_lower_var.get()))
        self.upper_scale.config(from_=lower + 1)
        if self.robust_upper_var.get() <= lower:
            self.robust_upper_var.set(lower + 1)
        self._on_parameter_change()
    
    def _update_lower_max(self, val=None):
        """Update lower scale maximum based on upper value."""
        upper = int(float(self.robust_upper_var.get()))
        self.lower_scale.config(to=upper - 1)
        if self.robust_lower_var.get() >= upper:
            self.robust_lower_var.set(upper - 1)
        self._on_parameter_change()
    
    def _on_parameter_change(self, val=None):
        """Called when any parameter changes."""
        # Only update parameters and notify callback if callback is provided
        # This allows disabling real-time updates when callback is None
        if self.on_change_callback:
            # Update the parameters object
            self.update_parameters_from_ui()
            # Notify callback
            self.on_change_callback()

    def _on_water_type_change(self, event=None):
        """Handle water type changes with smart parameter adjustments."""
        try:
            water_type = self.water_type_var.get()
            
            # Smart adjustment: When lake mode is selected, provide intelligent recommendations
            if water_type == "lake":
                # Check current magenta compensation level
                magenta_comp = self.magenta_compensation_var.get()
                
                # If user has set high magenta compensation, suggest reducing/disabling red channel and dehaze
                if magenta_comp > 1.3:
                    # Reduce red channel enhancement since magenta compensation already boosts red
                    if self.enable_red_channel_var.get() and self.red_scale_var.get() > 1.2:
                        self.red_scale_var.set(min(self.red_scale_var.get(), 1.2))
                        print("Auto-adjusted: Reduced red scale due to high magenta compensation")
                    
                    if self.red_scale_var.get() <= 1.05:
                        self.enable_red_channel_var.set(False)
                        print("Auto-adjusted: Disabled red channel enhancement due to high magenta compensation")
                
                # If magenta compensation is very high, also reduce dehaze
                if magenta_comp > 1.4:
                    if self.enable_dehaze_var.get() and self.dehaze_strength_var.get() > 0.5:
                        new_dehaze = self.dehaze_strength_var.get() * 0.7  # Reduce by 30%
                        self.dehaze_strength_var.set(new_dehaze)
                        print(f"Auto-adjusted: Reduced dehaze strength to {new_dehaze:.2f} due to high magenta compensation")
                    
                    if self.dehaze_strength_var.get() <= 0.3:
                        self.enable_dehaze_var.set(False)
                        print("Auto-adjusted: Disabled dehaze due to high magenta compensation")
            
            # Call the normal parameter change handler
            self._on_parameter_change(val=event)
            
        except Exception as e:
            print(f"Water type change error: {e}")
            # Fallback to normal parameter change
            self._on_parameter_change(val=event)

    def _on_magenta_change(self, val=None):
        """Handle magenta compensation changes with smart parameter adjustments."""
        try:
            magenta_comp = float(val) if val else self.magenta_compensation_var.get()
            water_type = self.water_type_var.get()
            
            # Smart adjustment: Only apply when in lake mode
            if water_type == "lake" and magenta_comp > 1.3:
                # Reduce red channel enhancement since magenta compensation already boosts red
                if self.enable_red_channel_var.get() and self.red_scale_var.get() > 1.2:
                    new_red_scale = min(self.red_scale_var.get(), 1.2)
                    self.red_scale_var.set(new_red_scale)
                    print(f"Auto-adjusted: Reduced red scale to {new_red_scale:.2f} due to high magenta compensation")
                
                if self.red_scale_var.get() <= 1.05:
                    self.enable_red_channel_var.set(False)
                    print("Auto-adjusted: Disabled red channel enhancement due to high magenta compensation")
            
                # If magenta compensation is very high, also reduce dehaze
                if magenta_comp > 1.4:
                    if self.enable_dehaze_var.get() and self.dehaze_strength_var.get() > 0.5:
                        new_dehaze = self.dehaze_strength_var.get() * 0.7  # Reduce by 30%
                        self.dehaze_strength_var.set(new_dehaze)
                        print(f"Auto-adjusted: Reduced dehaze strength to {new_dehaze:.2f} due to high magenta compensation")
                    
                    if self.dehaze_strength_var.get() <= 0.3:
                        self.enable_dehaze_var.set(False)
                        print("Auto-adjusted: Disabled dehaze due to high magenta compensation")
            
            # Call the normal parameter change handler
            self._on_parameter_change(val=val)
            
        except Exception as e:
            print(f"Magenta compensation change error: {e}")
            # Fallback to normal parameter change
            self._on_parameter_change(val=val)
    
    def update_parameters_from_ui(self):
        """Update parameters object from UI controls."""
        # White Balance
        self.params.enable_white_balance = self.enable_white_balance_var.get()
        self.params.wb_method = self.wb_method_var.get()
        self.params.white_balance_strength = self.white_balance_strength_var.get()
        self.params.robust_lower = self.robust_lower_var.get()
        self.params.robust_upper = self.robust_upper_var.get()
        self.params.retinex_percentile = self.retinex_percentile_var.get()
        
        # Basic Corrections
        self.params.enable_red_channel = self.enable_red_channel_var.get()
        self.params.red_scale = self.red_scale_var.get()
        self.params.enable_dehaze = self.enable_dehaze_var.get()
        self.params.dehaze_strength = self.dehaze_strength_var.get()
        self.params.enable_saturation = self.enable_saturation_var.get()
        self.params.saturation = self.saturation_var.get()
        
        # Advanced Processing
        self.params.enable_clahe = self.enable_clahe_var.get()
        self.params.clahe_clip = self.clahe_clip_var.get()
        
        # Fusion Processing
        self.params.enable_fusion = self.enable_fusion_var.get()
        self.params.fusion_method = self.fusion_method_var.get()
        self.params.unsharp_amount = self.unsharp_amount_var.get()
        self.params.unsharp_radius = self.unsharp_radius_var.get()
        self.params.fusion_balance = self.fusion_balance_var.get()
        
        # Green Water Processing
        self.params.water_type = self.water_type_var.get()
        self.params.green_water_detection = self.green_water_detection_var.get()
        self.params.magenta_compensation = self.magenta_compensation_var.get()
        self.params.enhanced_dehazing = self.enhanced_dehazing_var.get()
        self.params.turbidity_compensation = self.turbidity_compensation_var.get()
    
    def update_ui_from_parameters(self):
        """Update UI controls from parameters object."""
        # White Balance
        self.enable_white_balance_var.set(self.params.enable_white_balance)
        self.wb_method_var.set(self.params.wb_method)
        self.white_balance_strength_var.set(self.params.white_balance_strength)
        self.robust_lower_var.set(self.params.robust_lower)
        self.robust_upper_var.set(self.params.robust_upper)
        self.retinex_percentile_var.set(self.params.retinex_percentile)
        
        # Basic Corrections
        self.enable_red_channel_var.set(self.params.enable_red_channel)
        self.red_scale_var.set(self.params.red_scale)
        self.enable_dehaze_var.set(self.params.enable_dehaze)
        self.dehaze_strength_var.set(self.params.dehaze_strength)
        self.enable_saturation_var.set(self.params.enable_saturation)
        self.saturation_var.set(self.params.saturation)
        
        # Advanced Processing
        self.enable_clahe_var.set(self.params.enable_clahe)
        self.clahe_clip_var.set(self.params.clahe_clip)
        
        # Fusion Processing
        self.enable_fusion_var.set(self.params.enable_fusion)
        self.fusion_method_var.set(self.params.fusion_method)
        self.unsharp_amount_var.set(self.params.unsharp_amount)
        self.unsharp_radius_var.set(self.params.unsharp_radius)
        self.fusion_balance_var.set(self.params.fusion_balance)
        
        # Green Water Processing
        self.water_type_var.set(self.params.water_type)
        self.green_water_detection_var.set(self.params.green_water_detection)
        self.magenta_compensation_var.set(self.params.magenta_compensation)
        self.enhanced_dehazing_var.set(self.params.enhanced_dehazing)
        self.turbidity_compensation_var.set(self.params.turbidity_compensation)
