````markdown
# Submarine Color Correction

A GUI application for performing advanced color correction on submarine and underwater images. This tool provides white balance correction, red channel enhancement, dehazing, image fusion, and other specialized filters designed to improve underwater photography.

## Features

- **Interactive GUI**: Professional tabbed interface built with Tkinter
- **White Balance Correction**: Manual and automatic white balance adjustment
- **Red Channel Enhancement**: Boost red tones lost in underwater photography
- **Advanced Dehazing**: Remove water haze using dark channel prior techniques
- **Image Fusion**: Combine multiple processing techniques for optimal results
- **CLAHE Enhancement**: Contrast Limited Adaptive Histogram Equalization
- **Saturation Control**: Fine-tune color saturation
- **Auto-tune Parameters**: Intelligent automatic parameter optimization
- **Image Navigation**: Zoom, pan, and rotate functionality
- **Batch Processing**: Process multiple images efficiently

## Project Structure

```
submarine-color-correction/
├── src/
│   ├── main.py              # Main GUI application
│   ├── color_correction.py  # Core color correction algorithms
│   ├── ColorCorrection.py   # Enhanced ColorCorrection class
│   └── utils.py            # Utility functions
├── tests/
│   └── test_color_correction.py # Unit tests
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Installation

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/submarine-color-correction.git
cd submarine-color-correction
```

2. **Create a virtual environment** (recommended):
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

## Usage

### GUI Application

Launch the interactive application:
```bash
python src/main.py
```

**Features:**
- Load images using the "Load Image" button
- Adjust parameters in the organized tabs:
  - **White Balance**: Color temperature and tint adjustment
  - **Basic**: Red enhancement, dehazing, CLAHE, saturation
  - **Advanced**: Fusion processing and advanced algorithms
- Use "Auto Tune" for intelligent parameter optimization
- Navigate with zoom, pan, and rotate controls
- Save corrected images with "Save Image" button

### Key Controls

- **Load Image**: Select submarine/underwater image to correct
- **Auto Tune**: Automatically optimize correction parameters
- **Apply Correction**: Process image with current settings
- **Save Image**: Export corrected image
- **Zoom In/Out**: Navigate image details
- **Pan**: Click and drag to move around zoomed images
- **Rotate**: 90-degree rotation controls (↺ ↻)

## Technical Details

### Color Correction Pipeline

1. **White Balance**: Adjusts color temperature and removes color casts
2. **Red Channel Enhancement**: Compensates for red light absorption underwater
3. **Dehazing**: Uses dark channel prior algorithm to remove water haze
4. **CLAHE**: Improves local contrast without over-amplifying noise
5. **Saturation**: Fine-tunes color vibrancy
6. **Fusion**: Combines multiple processing techniques

### Auto-tune Algorithm

The auto-tune feature analyzes image characteristics and automatically adjusts:
- White balance based on gray-world assumption
- Red channel enhancement based on blue/green dominance
- Dehazing strength based on contrast analysis
- CLAHE parameters for optimal local contrast
- Saturation to maintain natural appearance

## Contributing

Contributions are welcome! Please feel free to:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Requirements

- Python 3.7+
- OpenCV 4.5+
- Pillow 8.0+
- NumPy 1.21+
- Tkinter (usually included with Python)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenCV community for computer vision algorithms
- Python Imaging Library (Pillow) for image processing
- Dark channel prior dehazing algorithm research
