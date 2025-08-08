import unittest
from src.color_correction import ColorCorrector
from src.utils import load_image, save_image

class TestColorCorrector(unittest.TestCase):

    def setUp(self):
        self.color_corrector = ColorCorrector()
        self.test_image_path = 'path/to/test/image.jpg'
        self.test_image = load_image(self.test_image_path)

    def test_apply_correction(self):
        corrected_image = self.color_corrector.apply_correction(self.test_image)
        self.assertIsNotNone(corrected_image)

    def test_adjust_brightness(self):
        factor = 1.5
        brightened_image = self.color_corrector.adjust_brightness(self.test_image, factor)
        self.assertIsNotNone(brightened_image)

if __name__ == '__main__':
    unittest.main()