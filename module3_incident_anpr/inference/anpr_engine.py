#!/usr/bin/env python3
"""
Module 3: Unified ANPR Engine (Stage 1 Detection + Stage 2 OCR)
==============================================================
Provides modular end-to-end number plate recognition:
- Uses PlateDetector for Stage 1 localization
- Uses Baseline CRNNOcrModel (best_ocr_model.pt) for Stage 2 OCR
- Returns structured predictions with bounding boxes, text, and confidence
"""

from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass
import numpy as np
from PIL import Image
import torch
import cv2

# Import plate detector and OCR components
from module3_incident_anpr.inference.plate_detector import PlateDetector, PlateDetection
from module3_incident_anpr.train_ocr import (
    CRNNOcrModel, NUM_CLASSES, CHAR_TO_IDX, IDX_TO_CHAR,
    BLANK_IDX, resize_and_pad, greedy_ctc_decode
)

@dataclass
class ANPRResult:
    plate_text: Optional[str]
    ocr_confidence: float
    detection_confidence: float
    plate_bbox: Optional[Tuple[int, int, int, int]]
    status: str  # "recognized" | "detected_unreadable" | "unavailable"

class ANPREngine:
    """
    Unified ANPR Engine combining Stage 1 Plate Detection with Stage 2 CRNN OCR.
    Loads the trained baseline model weights safely on CPU or CUDA.
    """

    def __init__(
        self,
        checkpoint_path: Optional[str | Path] = None,
        device: Optional[str] = None
    ):
        if checkpoint_path is None:
            checkpoint_path = Path("module3_incident_anpr/ocr_checkpoints/best_ocr_model.pt")
        else:
            checkpoint_path = Path(checkpoint_path)

        self.checkpoint_path = checkpoint_path
        self.device = torch.device(device if device else ("cuda" if torch.cuda.is_available() else "cpu"))

        # Initialize Stage 1 Detector
        self.detector = PlateDetector()

        # Initialize Stage 2 OCR Model
        self.ocr_model = None
        self.img_h = 48
        self.img_w = 160
        self.num_classes = NUM_CLASSES
        self._load_ocr_model()

    def _load_ocr_model(self):
        if not self.checkpoint_path.exists():
            print(f"[-] WARNING: ANPR OCR Checkpoint not found at {self.checkpoint_path}")
            return

        try:
            checkpoint = torch.load(self.checkpoint_path, map_location=self.device)
            self.img_h = checkpoint.get("img_height", 48)
            self.img_w = checkpoint.get("img_width", 160)
            self.num_classes = checkpoint.get("num_classes", NUM_CLASSES)

            self.ocr_model = CRNNOcrModel(num_classes=self.num_classes).to(self.device)
            self.ocr_model.load_state_dict(checkpoint["model_state_dict"])
            self.ocr_model.eval()
            # print(f"[+] ANPREngine successfully loaded OCR weights from {self.checkpoint_path}")
        except Exception as e:
            print(f"[-] ERROR loading OCR model: {e}")
            self.ocr_model = None

    def recognize_crop(self, plate_crop: np.ndarray) -> Tuple[Optional[str], float]:
        """
        Run OCR inference directly on an already cropped plate image.
        """
        if self.ocr_model is None or plate_crop is None or plate_crop.size == 0:
            return None, 0.0

        try:
            # Convert crop to grayscale PIL Image
            if len(plate_crop.shape) == 3:
                gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)
            else:
                gray = plate_crop.copy()

            pil_img = Image.fromarray(gray)
            img_arr = resize_and_pad(pil_img, self.img_h, self.img_w)
            tensor_img = torch.tensor(img_arr, dtype=torch.float32).unsqueeze(0).unsqueeze(0).to(self.device)

            with torch.no_grad():
                logits_ctc = self.ocr_model(tensor_img)
                # Compute softmax confidence
                probs = logits_ctc.softmax(dim=2)  # [T, 1, C]
                max_probs, preds = torch.max(probs, dim=2)  # [T, 1]
                
                decoded = greedy_ctc_decode(logits_ctc)
                plate_text = decoded[0] if decoded else ""

                # Mean probability over non-blank character emissions
                non_blank_mask = (preds.squeeze(1) != BLANK_IDX)
                if non_blank_mask.sum() > 0:
                    ocr_conf = float(max_probs.squeeze(1)[non_blank_mask].mean().item())
                else:
                    ocr_conf = 0.50

            if len(plate_text) >= 4:
                return plate_text, round(ocr_conf, 3)
            return None, 0.0

        except Exception as e:
            return None, 0.0

    def process_vehicle_image(self, vehicle_image: np.ndarray) -> ANPRResult:
        """
        Run full 2-stage ANPR pipeline on a vehicle bounding box image or camera frame.
        """
        if vehicle_image is None or vehicle_image.size == 0:
            return ANPRResult(
                plate_text=None,
                ocr_confidence=0.0,
                detection_confidence=0.0,
                plate_bbox=None,
                status="unavailable"
            )

        # Stage 1: Detect Plate
        plate_detections = self.detector.detect(vehicle_image)

        if not plate_detections:
            return ANPRResult(
                plate_text=None,
                ocr_confidence=0.0,
                detection_confidence=0.0,
                plate_bbox=None,
                status="unavailable"
            )

        # Stage 2: Recognize candidate crops
        best_result = None
        for det in plate_detections:
            plate_text, ocr_conf = self.recognize_crop(det.crop)
            if plate_text:
                return ANPRResult(
                    plate_text=plate_text,
                    ocr_confidence=ocr_conf,
                    detection_confidence=det.confidence,
                    plate_bbox=det.bbox,
                    status="recognized"
                )

        # Plate candidate located, but OCR was unreadable
        top_det = plate_detections[0]
        return ANPRResult(
            plate_text=None,
            ocr_confidence=0.0,
            detection_confidence=top_det.confidence,
            plate_bbox=top_det.bbox,
            status="detected_unreadable"
        )
