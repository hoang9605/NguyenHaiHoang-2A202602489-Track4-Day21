"""Tests catch KITTI bottom-center/yaw errors and changing metric denominators."""
import unittest
import numpy as np
from starter.kitti_io import KittiObject
from src.benchmark import points_in_box, box_hit_counts
from src.benchmark import benchmark


class MetricTests(unittest.TestCase):
    def test_translation_changes_pixels_without_reselecting_objects(self):
        baseline, frames0, selected0 = benchmark("data/kitti_mini", ["000001"], [0], 10)
        shifted, frames1, selected1 = benchmark("data/kitti_mini", ["000001"], [0], 10,
                                                lateral_shift_m=.1)
        np.testing.assert_array_equal(baseline.n_points, shifted.n_points)
        self.assertTrue(selected0.equals(selected1))
        self.assertEqual(frames0.shift_p50_px.iloc[0], 0)
        self.assertGreater(frames1.shift_p50_px.iloc[0], 0)

    def test_rotated_box_uses_bottom_center_and_hwl(self):
        obj = KittiObject("Car", 0, 0, 0, np.array([0, 0, 100, 100]),
                          np.array([2, 2, 4]), np.array([0, 1, 10]), np.pi / 2)
        points = np.array([[0, 0, 11.9], [1.1, 0, 10], [0, 1.1, 10],
                           [0, -1, 10], [0, -1.1, 10], [np.nan, 0, 10]])
        np.testing.assert_array_equal(points_in_box(points, obj),
                                      [True, False, False, True, False, False])

    def test_fov_loss_counts_as_miss_in_fixed_object_population(self):
        p = np.array([[10, 0, 50, 0], [0, 10, 50, 0], [0, 0, 1, 0]])
        points = np.array([[0, 0, 1], [10, 0, 1], [1, 0, 1]])
        hits, visible = box_hit_counts(points, p, (100, 100), np.array([45, 45, 55, 55]))
        self.assertEqual(hits, 1)
        self.assertEqual(visible, 2)
        self.assertAlmostEqual(hits / len(points), 1 / 3)


if __name__ == "__main__":
    unittest.main()
