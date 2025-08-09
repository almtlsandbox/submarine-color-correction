"""
Data models for processing parameters.
Centralizes parameter definitions, validation, and defaults.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import logging

@dataclass
class ProcessingParameters:
    """Holds all image processing parameters with validation."""
    
    # White Balance
    enable_white_balance: bool = True
    wb_method: str = "robust"  # "robust", "white_patch", "gray_world"
    white_balance_strength: float = 1.0
    robust_lower: float = 5.0
    robust_upper: float = 95.0
    retinex_percentile: float = 1.0
    
    # Basic Corrections
    enable_red_channel: bool = True
    red_scale: float = 1.3
    enable_dehaze: bool = True
    dehaze_strength: float = 0.8
    enable_saturation: bool = True
    saturation: float = 1.2
    
    # Advanced Processing
    enable_clahe: bool = True
    clahe_clip: float = 2.5
    
    # Fusion Processing
    enable_fusion: bool = False
    fusion_method: str = "average"  # "average", "pca", "weighted"
    unsharp_amount: float = 1.5
    unsharp_radius: float = 1.0
    fusion_balance: float = 0.5
    
    # Green Water Specific Parameters
    water_type: str = "ocean"  # "ocean", "lake", "auto"
    green_water_detection: bool = True
    magenta_compensation: float = 1.0  # Green channel dampening factor
    lake_attenuation_red: float = 0.45  # Lake-specific attenuation coefficients
    lake_attenuation_green: float = 0.25
    lake_attenuation_blue: float = 0.8
    enhanced_dehazing: bool = False  # Stronger dehazing for turbid water
    turbidity_compensation: float = 1.2  # Backscatter compensation factor
    
    def __post_init__(self):
        """Validate parameters after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """Validate all parameters are within acceptable ranges."""
        # White balance validation
        if self.wb_method not in ["robust", "white_patch", "gray_world"]:
            raise ValueError(f"Invalid wb_method: {self.wb_method}")
        
        if not (0.0 <= self.white_balance_strength <= 2.0):
            raise ValueError(f"white_balance_strength must be 0.0-2.0, got {self.white_balance_strength}")
        
        # Water type validation
        if self.water_type not in ["ocean", "lake", "auto"]:
            raise ValueError(f"Invalid water_type: {self.water_type}")
        
        # Green water parameters validation
        if not (0.1 <= self.magenta_compensation <= 3.0):
            raise ValueError(f"magenta_compensation must be 0.1-3.0, got {self.magenta_compensation}")
        
        if not (0.1 <= self.turbidity_compensation <= 3.0):
            raise ValueError(f"turbidity_compensation must be 0.1-3.0, got {self.turbidity_compensation}")
        
        if not (0.0 <= self.robust_lower < self.robust_upper <= 100.0):
            raise ValueError(f"Invalid percentile range: {self.robust_lower}-{self.robust_upper}")
        
        # Basic corrections validation
        if not (1.0 <= self.red_scale <= 3.0):
            raise ValueError(f"red_scale must be 1.0-3.0, got {self.red_scale}")
        
        if not (0.1 <= self.dehaze_strength <= 2.0):
            raise ValueError(f"dehaze_strength must be 0.1-2.0, got {self.dehaze_strength}")
        
        if not (0.5 <= self.saturation <= 3.0):
            raise ValueError(f"saturation must be 0.5-3.0, got {self.saturation}")
        
        # Advanced processing validation
        if not (1.0 <= self.clahe_clip <= 5.0):
            raise ValueError(f"clahe_clip must be 1.0-5.0, got {self.clahe_clip}")
        
        # Fusion validation
        if self.fusion_method not in ["average", "pca", "weighted"]:
            raise ValueError(f"Invalid fusion_method: {self.fusion_method}")
        
        if not (0.0 <= self.unsharp_amount <= 3.0):
            raise ValueError(f"unsharp_amount must be 0.0-3.0, got {self.unsharp_amount}")
        
        if not (0.5 <= self.unsharp_radius <= 3.0):
            raise ValueError(f"unsharp_radius must be 0.5-3.0, got {self.unsharp_radius}")
        
        if not (0.0 <= self.fusion_balance <= 1.0):
            raise ValueError(f"fusion_balance must be 0.0-1.0, got {self.fusion_balance}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert parameters to dictionary for processing."""
        return {
            'enable_white_balance': self.enable_white_balance,
            'wb_method': self.wb_method,
            'white_balance_strength': self.white_balance_strength,
            'robust_lower': self.robust_lower,
            'robust_upper': self.robust_upper,
            'retinex_percentile': self.retinex_percentile,
            'enable_red_channel': self.enable_red_channel,
            'red_scale': self.red_scale,
            'enable_dehaze': self.enable_dehaze,
            'dehaze_strength': self.dehaze_strength,
            'enable_saturation': self.enable_saturation,
            'saturation': self.saturation,
            'enable_clahe': self.enable_clahe,
            'clahe_clip': self.clahe_clip,
            'enable_fusion': self.enable_fusion,
            'fusion_method': self.fusion_method,
            'unsharp_amount': self.unsharp_amount,
            'unsharp_radius': self.unsharp_radius,
            'fusion_balance': self.fusion_balance
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessingParameters':
        """Create parameters from dictionary."""
        # Filter only known parameters
        valid_params = {k: v for k, v in data.items() if hasattr(cls, k)}
        return cls(**valid_params)
    
    def reset_to_defaults(self) -> None:
        """Reset all parameters to default values."""
        defaults = ProcessingParameters()
        for field_name in self.__dataclass_fields__:
            setattr(self, field_name, getattr(defaults, field_name))
    
    def update(self, **kwargs) -> None:
        """Update parameters with validation."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                logging.warning(f"Unknown parameter: {key}")
        self.validate()

@dataclass 
class ViewParameters:
    """Parameters for image display and navigation."""
    zoom_factor: float = 1.0
    pan_x: int = 0
    pan_y: int = 0
    rotation_angle: int = 0
    
    def reset_view(self) -> None:
        """Reset view to defaults."""
        self.zoom_factor = 1.0
        self.pan_x = 0
        self.pan_y = 0
    
    def reset_rotation(self) -> None:
        """Reset only rotation."""
        self.rotation_angle = 0

@dataclass
class AutoTuneResult:
    """Result of auto-tuning parameters."""
    parameters: ProcessingParameters
    confidence: float  # 0.0 to 1.0
    analysis_notes: Dict[str, str] = field(default_factory=dict)
