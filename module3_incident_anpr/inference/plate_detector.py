#!/usr/bin/env python3
"""
Module 3 Stage 1: Modular License Plate Detector
================================================
Locates Indian license plate candidate regions within full video frames
or vehicle bounding-box crops.

Outputs standardized plate bounding boxes, detection confidence, and image crops.
"""

from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import numpy as np
import cv2

@dataclass
class PlateDetection:
    bbox: Tuple[int, int, int, int]  # (xmin, ymin, xmax, ymax)
    confidence: float
    crop: np.ndarray
    label: str = "license_plate"

class PlateDetector:
    """
    High-performance modular Indian License Plate Localizer.
    Utilizes morphological gradient filtering, rectangular aspect-ratio constraints,
    and bilateral edge analysis to accurately segment plate candidates from vehicle crops.
    """

    def __init__(
        self,
        min_aspect_ratio: float = 1.8,
        max_aspect_ratio: float = 6.0,
        min_area: int = 400,
        max_area_ratio: float = 0.50,
        confidence_base: float = 0.85
    ):
        self.min_aspect_ratio = min_aspect_ratio
        self.max_aspect_ratio = max_aspect_ratio
        self.min_area = min_area
        self.max_area_ratio = max_area_ratio
        self.confidence_base = confidence_base

    def detect(self, image: np.ndarray) -> List[PlateDetection]:
        """
        Detect license plates in an image (either vehicle crop or full frame).
        
        Args:
            image: np.ndarray (BGR image)
            
        Returns:
            List[PlateDetection] containing bounding boxes, confidences, and crops.
        """
        if image is None or image.size == 0:
            return []

        img_h, img_w = image.shape[:2]
        total_image_area = img_h * img_w

        # Convert to Grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # 1. Bilateral filter to preserve edges while removing noise
        filtered = cv2.bilateralFilter(gray, 9, 75, 75)

        # 2. Blackhat morphological operation to highlight dark text on light plates
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (13, 5))
        blackhat = cv2.morphologyEx(filtered, cv2.MORPH_BLACKHAT, kernel)

        # 3. Morphological gradient & Sobel horizontal edge emphasis
        grad_x = cv2.Sobel(blackhat, ddepth=cv2.CV_32F, dx=1, dy=0, ksize=-1)
        grad_x = np.absolute(grad_x)
        min_v, max_v = np.min(grad_x), np.max(grad_x)
        if max_v > min_v:
            grad_x = (255 * ((grad_x - min_v) / (max_v - min_v))).astype("uint8")
        else:
            grad_x = grad_x.astype("uint8")

        # 4. Otsu adaptive thresholding
        blurred = cv2.GaussianBlur(grad_x, (5, 5), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # 5. Connect horizontal character regions
        close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 5))
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, close_kernel)

        # 6. Find external contours
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        candidates = []

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h

            # Filter by area
            if area < self.min_area or area > (total_image_area * self.max_area_ratio):
                continue

            aspect_ratio = float(w) / max(1, h)

            # Indian rectangular / square plate aspect ratio filter
            if self.min_aspect_ratio <= aspect_ratio <= self.max_aspect_ratio:
                # Add margin around plate
                pad_x = int(w * 0.05)
                pad_y = int(h * 0.10)

                xmin = max(0, x - pad_x)
                ymin = max(0, y - pad_y)
                xmax = min(img_w, x + w + pad_x)
                ymax = min(img_h, y + h + pad_y)

                crop = image[ymin:ymax, xmin:xmax].copy()
                if crop.size > 0:
                    # Score candidate based on standard Indian plate aspect ratio (~3.5)
                    ideal_ratio = 3.5
                    ratio_diff = abs(aspect_ratio - ideal_ratio) / ideal_ratio
                    conf = max(0.40, min(0.95, self.confidence_base - (0.2 * ratio_diff)))

                    candidates.append(PlateDetection(
                        bbox=(xmin, ymin, xmax, ymax),
                        confidence=round(conf, 3),
                        crop=crop,
                        label="license_plate"
                    ))

        # Sort candidates by area / confidence descending
        candidates.sort(key=lambda d: d.confidence * (d.bbox[2] - d.bbox[0]) * (d.bbox[3] - d.bbox[1]), reverse=True)

        # If no strict contour candidate passed, use lower half heuristic of vehicle crop
        if not candidates and img_h >= 24 and img_w >= 60:
            # Fallback: Bottom 45% central band of vehicle
            ymin = int(img_h * 0.50)
            ymax = int(img_h * 0.95)
            xmin = int(img_w * 0.15)
            xmax = int(img_w * 0.85)

            if (xmax > xmin) and (ymax > ymin):
                fallback_crop = image[ymin:ymax, xmin:xmax].copy()
                candidates.append(PlateDetection(
                    bbox=(xmin, ymin, xmax, ymax),
                    confidence=0.50,
                    crop=fallback_crop,
                    label="license_plate_heuristic"
                ))

        return candidates
