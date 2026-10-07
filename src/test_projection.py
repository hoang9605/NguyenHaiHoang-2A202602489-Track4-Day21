"""Hand-checked geometry regressions. Run: python -m unittest src.test_projection -v."""
import unittest

import numpy as np

from starter.datasets import load_frame
from starter.projection import cam_to_image, velo_to_cam


class ProjectionTests(unittest.TestCase):
    def test_synthetic_reference_point(self):
        fr = load_frame("data/synthetic", "000000")
        cam = velo_to_cam(np.array([[10., 0., 0.]]), fr["calib"])
        self.assertAlmostEqual(cam[0, 2], 9.73, delta=0.02)
        uv, depth, mask = cam_to_image(cam, fr["calib"].P2, fr["image"].shape)
        np.testing.assert_allclose(uv[0], [614, 175], atol=1)
        self.assertTrue(mask[0])

    def test_filters_invalid_depth_boundaries_and_preserves_indices(self):
        p = np.array([[0, 0, 2], [0, 0, -1], [np.nan, 0, 2],
                      [np.inf, 0, 2], [2, 0, 2], [-1, -1, 2], [0, 0, .1]])
        projection = np.array([[100, 0, 50, 0], [0, 100, 50, 0], [0, 0, 1, 0]])
        with np.errstate(all="raise"):
            uv, depth, mask = cam_to_image(p, projection, (100, 100, 3))
        np.testing.assert_array_equal(mask, [True, False, False, False, False, True, False])
        np.testing.assert_allclose(uv, [[50, 50], [0, 0]])
        np.testing.assert_allclose(depth, [2, 2])

    def test_divides_by_projective_scale_not_camera_depth(self):
        projection = np.array([[100, 0, 0, 0], [0, 100, 0, 0], [0, 0, 1, 1]])
        uv, depth, mask = cam_to_image(np.array([[1., 1., 1.]]), projection, (100, 100))
        np.testing.assert_allclose(uv, [[50, 50]])
        np.testing.assert_allclose(depth, [1])

    def test_empty_and_zero_projective_scale(self):
        projection = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, -1]])
        for points in (np.empty((0, 3)), np.array([[0., 0., 1.]])):
            with np.errstate(all="raise"):
                uv, depth, mask = cam_to_image(points, projection, (100, 100))
            self.assertEqual(uv.shape, (0, 2))
            self.assertEqual(depth.shape, (0,))
            self.assertFalse(mask.any())


if __name__ == "__main__":
    unittest.main()
