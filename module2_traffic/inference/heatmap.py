from typing import List, Tuple, Optional
import numpy as np
import cv2

from shared.config import Config


class TrafficHeatmap:
    """
    Incremental spatial traffic density heatmap accumulator.

    Features:
    - Maintains a float32 2D spatial accumulation grid matching frame dimensions.
    - Applies a pre-calculated 2D Gaussian kernel at each vehicle centroid.
    - Incremental per-frame updates without reprocessing past frames or storing frame buffers.
    - Safe normalization handling zero or low-heat states.
    - Color mapping using OpenCV COLORMAP_JET and alpha blending with original frames.
    """

    def __init__(
        self,
        width: int,
        height: int,
        radius: Optional[int] = None,
        decay: Optional[float] = None,
        alpha: Optional[float] = None,
        colormap: int = cv2.COLORMAP_JET,
    ):
        config = Config()

        self.width = int(width)
        self.height = int(height)

        self.radius = int(
            radius
            if radius is not None
            else getattr(config, "traffic_heatmap_radius", 30)
        )

        self.decay = float(
            decay
            if decay is not None
            else getattr(config, "traffic_heatmap_decay", 1.0)
        )

        self.alpha = float(
            alpha
            if alpha is not None
            else getattr(config, "traffic_heatmap_alpha", 0.45)
        )

        self.colormap = colormap

        # Floating-point accumulation map
        self.accumulator = np.zeros((self.height, self.width), dtype=np.float32)

        # Precompute 2D Gaussian kernel for efficient splatting
        self.kernel, self.kernel_radius = self._create_gaussian_kernel(self.radius)

    @staticmethod
    def _create_gaussian_kernel(radius: int) -> Tuple[np.ndarray, int]:
        """
        Generate a normalized 2D Gaussian kernel matrix centered in a square window.
        """
        size = 2 * radius + 1
        sigma = radius / 3.0
        x = np.linspace(-radius, radius, size)
        y = np.linspace(-radius, radius, size)
        xx, yy = np.meshgrid(x, y)
        kernel = np.exp(-(xx**2 + yy**2) / (2.0 * sigma**2)).astype(np.float32)
        
        # Max normalized to 1.0 so each detection adds a peak intensity of 1.0
        kernel_max = np.max(kernel)
        if kernel_max > 0:
            kernel /= kernel_max

        return kernel, radius

    def update(
        self,
        centroids: List[Tuple[float, float]],
        intensity: float = 1.0,
    ) -> None:
        """
        Accumulate spatial density from a list of vehicle centroids for the current frame.
        """
        if self.decay < 1.0:
            self.accumulator *= self.decay

        if not centroids:
            return

        r = self.kernel_radius
        h, w = self.height, self.width

        for pt in centroids:
            if pt is None or len(pt) < 2:
                continue

            cx, cy = int(round(pt[0])), int(round(pt[1]))

            # Discard points fully outside frame bounds
            if cx < 0 or cx >= w or cy < 0 or cy >= h:
                continue

            # Determine bounding coordinates on the accumulator
            x_min = max(0, cx - r)
            x_max = min(w, cx + r + 1)
            y_min = max(0, cy - r)
            y_max = min(h, cy + r + 1)

            # Determine corresponding sub-region on the precomputed kernel
            k_x_min = x_min - (cx - r)
            k_x_max = k_x_min + (x_max - x_min)
            k_y_min = y_min - (cy - r)
            k_y_max = k_y_min + (y_max - y_min)

            # Additive splat
            self.accumulator[y_min:y_max, x_min:x_max] += (
                self.kernel[k_y_min:k_y_max, k_x_min:k_x_max] * intensity
            )

    def render(
        self,
        frame: np.ndarray,
        alpha: Optional[float] = None,
    ) -> np.ndarray:
        """
        Normalize accumulated heat, apply colormap, and blend onto the provided frame.
        """
        blend_alpha = self.alpha if alpha is None else float(alpha)
        blend_alpha = np.clip(blend_alpha, 0.0, 1.0)

        max_val = np.max(self.accumulator)

        if max_val <= 0.0:
            # If no heat has accumulated yet, return original frame
            return frame.copy()

        # Safe normalization to uint8 range [0, 255]
        normalized = np.clip((self.accumulator / max_val) * 255.0, 0, 255).astype(np.uint8)

        # Apply colormap
        heatmap_color = cv2.applyColorMap(normalized, self.colormap)

        # Mask out cold/zero areas to retain background visibility
        # Threshold at minimum non-zero heat to blend smoothly
        heat_mask = (normalized > 10).astype(np.float32)
        heat_mask_3ch = np.dstack([heat_mask, heat_mask, heat_mask])

        # Smooth alpha blend where heat exists
        blended = (
            frame.astype(np.float32) * (1.0 - (blend_alpha * heat_mask_3ch))
            + heatmap_color.astype(np.float32) * (blend_alpha * heat_mask_3ch)
        )

        return np.clip(blended, 0, 255).astype(np.uint8)

    def get_heatmap_raw(self) -> np.ndarray:
        """
        Return the raw float32 accumulator array.
        """
        return self.accumulator.copy()

    def get_heatmap_colored(self) -> np.ndarray:
        """
        Return a standalone colormapped image of the accumulated density without background.
        """
        max_val = np.max(self.accumulator)
        if max_val <= 0.0:
            return np.zeros((self.height, self.width, 3), dtype=np.uint8)

        normalized = np.clip((self.accumulator / max_val) * 255.0, 0, 255).astype(np.uint8)
        return cv2.applyColorMap(normalized, self.colormap)

    def reset(self) -> None:
        """
        Reset accumulator to zero.
        """
        self.accumulator.fill(0.0)


def main():
    """
    Self-test for TrafficHeatmap.
    """
    print("=" * 60)
    print("TRAFFIC HEATMAP TEST")
    print("=" * 60)

    h, w = 480, 640
    heatmap = TrafficHeatmap(width=w, height=h, radius=25)

    # Blank frame
    frame = np.full((h, w, 3), 50, dtype=np.uint8)

    # Initial frame render with no centroids
    rendered_empty = heatmap.render(frame)
    assert rendered_empty.shape == frame.shape
    assert np.max(heatmap.accumulator) == 0.0

    # Simulate centroids along a path
    centroids = [(100, 100), (105, 105), (110, 110), (300, 250)]
    heatmap.update(centroids)

    assert np.max(heatmap.accumulator) > 0.0
    rendered = heatmap.render(frame)
    assert rendered.shape == frame.shape
    assert rendered.dtype == np.uint8

    colored = heatmap.get_heatmap_colored()
    assert colored.shape == (h, w, 3)

    print("TrafficHeatmap component tests passed successfully.")


if __name__ == "__main__":
    main()
