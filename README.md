# Submarine Color Correction v2.0

A professional GUI application for advanced underwater image color correction. This tool specializes in submarine, scuba diving, and underwater photography enhancement with intelligent algorithms for both ocean (blue water) and lake (green water) environments.

## 🆕 What's New in v2.0

### 🎯 **Smart Lake Mode Management**
- **Automatic Water Type Detection**: AI-powered detection of lake vs ocean water
- **Intelligent Parameter Coordination**: Automatically adjusts red channel and dehaze when magenta compensation is applied
- **Specialized Lake Algorithms**: Beer-Lambert law implementation with lake-specific attenuation coefficients

### 🧠 **Enhanced Auto-Tuning**
- **Dual-Mode Intelligence**: Separate optimization for ocean vs lake environments
- **Scientific Parameter Balancing**: Prevents over-correction by coordinating different algorithms
- **High Confidence Results**: 0.95 confidence for lake mode, 0.80 for ocean mode

### 🖼️ **Advanced Image Viewer**
- **Smart View Management**: Automatically clears corrected previews when loading new images
- **View Mode Intelligence**: Switches from "corrected" to "original" view, preserves "split" view
- **Professional Navigation**: Zoom, pan, rotate with real-time preview

### 🏗️ **Modern Architecture**
- **Modular Design**: Clean separation of concerns with services, models, and core processors
- **Specialized Processors**: Dedicated green water processor for lake environments
- **Professional Logging**: Comprehensive debugging and performance monitoring

## Features

### 🌊 **Water Type Specialization**
- **Ocean Water**: Traditional blue water correction algorithms
- **Lake Water**: Specialized green water processing with magenta compensation
- **Auto Detection**: Intelligent water type recognition
- **Manual Override**: Full user control when needed

### 🎨 **Advanced Color Correction**
- **Multi-Method White Balance**: Robust, Gray World, White Patch algorithms
- **Scientific Red Channel Enhancement**: Beer-Lambert law based corrections
- **Advanced Dehazing**: Dark channel prior with turbidity compensation
- **Magenta Compensation**: Lake-specific green cast removal
- **CLAHE Enhancement**: Adaptive histogram equalization
- **Intelligent Saturation**: Context-aware color enhancement

### 🔧 **Professional Tools**
- **Auto-Tune System**: AI-powered parameter optimization
- **Real-time Processing**: Live preview of corrections
- **Batch Processing**: Handle multiple images efficiently
- **Professional Export**: High-quality image output

### 🖥️ **User Interface**
- **Tabbed Interface**: Organized parameter controls
- **Visual Feedback**: Real-time parameter impact display
- **Smart Adjustments**: UI automatically suggests optimal settings
- **Professional Layout**: Clean, intuitive design

## Installation

### Quick Start
```bash
# Clone the repository
git clone https://github.com/almtlsandbox/submarine-color-correction.git
cd submarine-color-correction

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Launch application
python src/main.py
```

## Usage Guide

### 🚀 **Quick Start**
1. Launch the application: `python src/main.py`
2. Click "Load Images" to select underwater photos
3. Click "Auto-Tune" for intelligent optimization
4. Fine-tune parameters if needed
5. Save your enhanced images

### 🎛️ **Parameter Tabs**
- **Basic**: Essential corrections (white balance, red channel, dehaze)
- **Green Water**: Lake-specific settings (water type, magenta compensation)
- **Advanced**: Professional tools (CLAHE, saturation, fusion)

### 🧠 **Auto-Tune System**
The intelligent auto-tune analyzes your image and:
- Detects water type (ocean vs lake)
- Optimizes white balance for underwater conditions
- Balances red channel enhancement with magenta compensation
- Adjusts dehazing for water clarity
- Prevents over-processing through smart parameter coordination

### 🌊 **Water Type Modes**
- **Auto**: Intelligent detection (recommended)
- **Ocean**: Traditional blue water algorithms
- **Lake**: Specialized green water processing

## Technical Highlights

### 🔬 **Scientific Algorithms**
- **Beer-Lambert Law**: Accurate light attenuation modeling
- **Dark Channel Prior**: Advanced haze removal
- **Gray World Assumption**: Robust white balance
- **CLAHE**: Contrast enhancement without artifacts

### 🧠 **Intelligence Features**
- **Water Type Detection**: Green dominance analysis
- **Parameter Coordination**: Prevents algorithm conflicts
- **Confidence Scoring**: Reliability metrics for auto-tune
- **Smart UI Behavior**: Automatic parameter suggestions

### 🏆 **Performance**
- **Real-time Preview**: Instant visual feedback
- **Optimized Processing**: Efficient image handling
- **Memory Management**: Handles large images
- **Professional Output**: High-quality results

## Development

### Building Executables
```bash
# Using cx_Freeze (recommended)
python setup_cxfreeze_singlefile.py build_exe

# Using build script
.\build_exe.bat
```

### Running Tests
```bash
python -m pytest tests/
```

## Requirements

- **Python**: 3.9+
- **OpenCV**: 4.5+
- **NumPy**: 1.21+
- **Pillow**: 8.0+
- **Tkinter**: (included with Python)

## Contributing

We welcome contributions! Please see our development docs:
- `SMART_LAKE_MODE_MANAGEMENT.md` - Lake processing algorithms
- `IMAGE_LOADING_ENHANCEMENT.md` - UI improvements
- `AUTO_DETECTION_FIX_COMPLETE.md` - Auto-detection system

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- Underwater photography community for testing and feedback
- OpenCV team for computer vision algorithms
- Scientific research on underwater light attenuation
- Beta testers for lake water processing improvements

---

**Version 2.0** - Major release with lake water specialization and intelligent parameter management
