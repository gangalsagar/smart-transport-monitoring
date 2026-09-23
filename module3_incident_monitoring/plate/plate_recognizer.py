from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict, Any, List
from collections import Counter
import numpy as np
import cv2


class BasePlateRecognizer(ABC):
    """
    Abstract interface for Automatic Number Plate Recognition (ANPR / ALPR).
    Allows plugging in trained plate detection models (e.g. YOLO-Plate + PaddleOCR / EasyOCR / LPRNet).
    """

    @abstractmethod
    def recognize_plate(self, vehicle_crop: np.ndarray) -> Tuple[Optional[str], float, str]:
        """
        Extract and read license plate text from a single vehicle crop image.
        
        Returns:
            (plate_text, confidence, status):
                plate_text: String (e.g. 'KA01MJ5005' or None)
                confidence: Float (0.0 to 1.0)
                status: 'unavailable' | 'simulated' | 'detected_unreadable' | 'recognized' | 'insufficient_consensus'
        """
        pass

    def _score_crop_quality(self, crop: np.ndarray) -> float:
        """Score candidate vehicle crop by size and Laplacian edge sharpness."""
        if crop is None or crop.size == 0:
            return 0.0
        h, w = crop.shape[:2]
        area_score = min(1.0, (w * h) / (320 * 240))
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if len(crop.shape) == 3 else crop
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness_score = min(1.0, sharpness / 500.0)
        return 0.6 * area_score + 0.4 * sharpness_score

    def recognize_plate_temporal(
        self,
        vehicle_crops: List[np.ndarray],
    ) -> Tuple[Optional[str], float, str, Dict[str, Any]]:
        """
        Extract and vote on license plate across multiple selected best candidate frame crops.
        """
        if not vehicle_crops:
            return None, 0.0, "unavailable", {}

        # 1. Best Frame Selection: Sort by crop quality and select top candidates (max 3)
        valid_crops = [c for c in vehicle_crops if c is not None and c.size > 0]
        if not valid_crops:
            return None, 0.0, "unavailable", {}

        scored_crops = sorted(valid_crops, key=self._score_crop_quality, reverse=True)
        selected_candidates = scored_crops[:3]

        readings: List[str] = []
        confidences: List[float] = []

        for crop in selected_candidates:
            # Downscale oversized crops if necessary to protect edge memory
            ch, cw = crop.shape[:2]
            if cw > 640 or ch > 480:
                scale = min(640 / cw, 480 / ch)
                crop_proc = cv2.resize(crop, (int(cw * scale), int(ch * scale)), interpolation=cv2.INTER_AREA)
            else:
                crop_proc = crop

            plate_text, conf, stat = self.recognize_plate(crop_proc)
            if plate_text and len(plate_text) >= 4 and stat in {"recognized", "low_confidence"}:
                readings.append(plate_text)
                confidences.append(conf)

        if not readings:
            # Fallback to single best candidate
            p_text, conf, stat = self.recognize_plate(selected_candidates[0])
            return p_text, conf, stat, {"total_crops": len(vehicle_crops), "selected_candidates": len(selected_candidates), "valid_reads": 0}

        # Majority voting consensus
        counts = Counter(readings)
        most_common_plate, vote_count = counts.most_common(1)[0]

        matching_confs = [c for p, c in zip(readings, confidences) if p == most_common_plate]
        avg_conf = float(np.mean(matching_confs)) if matching_confs else 0.70

        if avg_conf < 0.70:
            status = "low_confidence"
        elif vote_count < (len(readings) / 2):
            status = "insufficient_consensus"
        else:
            status = "recognized"

        consensus_info = {
            "total_crops": len(vehicle_crops),
            "valid_reads": len(readings),
            "vote_count": vote_count,
            "candidates": dict(counts),
        }

        return most_common_plate, round(avg_conf, 3), status, consensus_info


class PlaceholderPlateRecognizer(BasePlateRecognizer):
    """
    Event-triggered placeholder plate recognizer.
    Returns explicit simulated plate values and statuses for testing pipeline flow,
    NEVER fabricating realistic fake vehicle registrations.
    """

    def __init__(self, mode: str = "simulated"):
        self.mode = mode

    def recognize_plate(self, vehicle_crop: np.ndarray) -> Tuple[Optional[str], float, str]:
        if vehicle_crop is None or vehicle_crop.size == 0:
            return None, 0.0, "unavailable"

        if self.mode == "simulated":
            return "SIMULATED-TEST-PLATE", 0.75, "simulated"

        return None, 0.0, "unavailable"


class ProductionANPRRecognizer(BasePlateRecognizer):
    """
    Real-world ANPR Recognizer wrapping Stage 1 Plate Detection and Stage 2 CRNN OCR.
    Safely executes baseline OCR model weights (best_ocr_model.pt).
    """

    def __init__(self, checkpoint_path: Optional[str] = None):
        try:
            from module3_incident_monitoring.anpr.inference.anpr_engine import ANPREngine
        except ImportError:
            from module3_incident_anpr.inference.anpr_engine import ANPREngine
        self.engine = ANPREngine(checkpoint_path=checkpoint_path)

    def recognize_plate(self, vehicle_crop: np.ndarray) -> Tuple[Optional[str], float, str]:
        if vehicle_crop is None or vehicle_crop.size == 0:
            return None, 0.0, "unavailable"

        res = self.engine.process_vehicle_image(vehicle_crop)
        return res.plate_text, res.ocr_confidence, res.status

    def locate_plate_crop(self, vehicle_crop: np.ndarray) -> Optional[np.ndarray]:
        """Extract cropped plate image if plate is detected."""
        if vehicle_crop is None or vehicle_crop.size == 0:
            return None
        detections = self.engine.detector.detect(vehicle_crop)
        if detections:
            return detections[0].crop
        return None
