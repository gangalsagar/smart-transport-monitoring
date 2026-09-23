from pathlib import Path
import cv2
import numpy as np


def compute_iou(boxA, boxB):
    """Compute Intersection over Union (IoU) between two bounding boxes."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = max(0, boxA[2] - boxA[0]) * max(0, boxA[3] - boxA[1])
    boxBArea = max(0, boxB[2] - boxB[0]) * max(0, boxB[3] - boxB[1])
    unionArea = float(boxAArea + boxBArea - interArea)

    if unionArea == 0:
        return 0.0
    return interArea / unionArea


def non_max_suppression(detections, iou_threshold=0.35):
    """
    Filter duplicate / heavily overlapping detections before rendering evidence.
    Keeps highest confidence detection among overlapping boxes.
    """
    if not detections:
        return []

    # Sort descending by confidence
    sorted_dets = sorted(detections, key=lambda d: d.get("confidence", 0.0), reverse=True)
    kept = []

    for det in sorted_dets:
        bbox = det.get("bbox", {})
        box = [
            float(bbox.get("xmin", 0)),
            float(bbox.get("ymin", 0)),
            float(bbox.get("xmax", 0)),
            float(bbox.get("ymax", 0)),
        ]

        overlap = False
        for kept_det in kept:
            kbbox = kept_det.get("bbox", {})
            kbox = [
                float(kbbox.get("xmin", 0)),
                float(kbbox.get("ymin", 0)),
                float(kbbox.get("xmax", 0)),
                float(kbbox.get("ymax", 0)),
            ]
            if compute_iou(box, kbox) > iou_threshold:
                overlap = True
                break

        if not overlap:
            kept.append(det)

    return kept


class EvidenceGenerator:
    """
    Creates clean, professional visual evidence images from YOLO detections.

    Key Features:
    - Non-Maximum Suppression (NMS) to eliminate duplicate/redundant boxes
    - Dynamic font and line thickness scaling based on frame dimensions
    - Formatted confidence as percentage (e.g., 'Pothole 51%')
    - Compact, high-contrast dark badge pills with crisp borders
    - Intelligent multi-directional label collision avoidance
    - Strict canvas boundary clamping
    """

    def __init__(self, output_dir=None):
        project_root = Path(__file__).resolve().parents[2]

        if output_dir is None:
            output_dir = (
                project_root
                / "module1_road_defect"
                / "data"
                / "evidence"
            )

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

    def generate(
        self,
        image,
        detections,
        image_name,
        min_confidence=0.25,
        iou_threshold=0.35,
    ):
        """
        Draw clean, readable detections and save evidence image.

        Returns:
            Path to generated evidence image.
        """
        annotated = image.copy()
        height, width = annotated.shape[:2]

        # 1. Filter by minimum confidence
        valid_dets = [
            d for d in detections
            if float(d.get("confidence", 0.0)) >= min_confidence
        ]

        # 2. Filter duplicate overlapping detections via NMS
        filtered_dets = non_max_suppression(valid_dets, iou_threshold=iou_threshold)

        # 3. Dynamic font scale based on frame dimensions (clean and unobtrusive)
        diag = np.sqrt(width ** 2 + height ** 2)
        font_scale = max(0.38, min(0.55, diag / 1800.0))
        box_thickness = max(2, int(diag / 600.0))
        text_thickness = 1

        # 4. Prepare detection boxes and labels
        drawn_boxes = []
        placed_labels = []

        for detection in filtered_dets:
            bbox = detection.get("bbox", {})
            xmin = int(round(bbox.get("xmin", 0)))
            ymin = int(round(bbox.get("ymin", 0)))
            xmax = int(round(bbox.get("xmax", 0)))
            ymax = int(round(bbox.get("ymax", 0)))

            # Clamp coordinates to image boundaries
            xmin = max(0, min(xmin, width - 1))
            ymin = max(0, min(ymin, height - 1))
            xmax = max(0, min(xmax, width - 1))
            ymax = max(0, min(ymax, height - 1))

            if xmax <= xmin or ymax <= ymin:
                continue

            conf_val = float(detection.get("confidence", 0.0))
            class_name = detection.get("class_name", "Pothole").capitalize()
            # Clean percentage formatting e.g., "Pothole 51%"
            label = f"{class_name} {int(round(conf_val * 100))}%"

            drawn_boxes.append({
                "coords": (xmin, ymin, xmax, ymax),
                "label": label,
                "confidence": conf_val,
            })

        # Sort boxes top-to-bottom
        drawn_boxes.sort(key=lambda b: (b["coords"][1], b["coords"][0]))

        # Helper to check collision with already placed labels
        def collides(rect):
            for pl in placed_labels:
                if not (rect[2] < pl[0] or rect[0] > pl[2] or rect[3] < pl[1] or rect[1] > pl[3]):
                    return True
            return False

        # 5. Render bounding boxes and anti-collision text badges
        for box_item in drawn_boxes:
            xmin, ymin, xmax, ymax = box_item["coords"]
            label = box_item["label"]

            # Draw crisp bounding box
            box_color = (0, 235, 0)  # Clean bright green (BGR)
            cv2.rectangle(
                annotated,
                (xmin, ymin),
                (xmax, ymax),
                box_color,
                box_thickness,
                lineType=cv2.LINE_AA,
            )

            # Measure text size
            (tw, th), baseline = cv2.getTextSize(
                label,
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                text_thickness,
            )

            pad_x = 4
            pad_y = 3
            badge_w = tw + (2 * pad_x)
            badge_h = th + baseline + (2 * pad_y)

            # Candidate positions to test for non-overlapping placement
            candidate_positions = [
                (xmin, ymin - badge_h - 2),          # 1. Directly above box
                (xmin, ymin + 2),                    # 2. Inside top of box
                (xmin, ymax + 2),                    # 3. Directly below box
                (xmax - badge_w, ymin - badge_h - 2),# 4. Top-right aligned above
                (xmin + badge_w + 4, ymin - badge_h - 2), # 5. Shifted right above
                (max(0, xmin - badge_w - 4), ymin),  # 6. To the left of box
                (xmin, ymax + badge_h + 4),          # 7. Further below box
            ]

            chosen_rect = None

            for cx, cy in candidate_positions:
                # Clamp within frame bounds
                cx_clamped = max(2, min(cx, width - badge_w - 2))
                cy_clamped = max(2, min(cy, height - badge_h - 2))
                rect = [cx_clamped, cy_clamped, cx_clamped + badge_w, cy_clamped + badge_h]

                if not collides(rect):
                    chosen_rect = rect
                    break

            # Fallback if all standard slots collided
            if chosen_rect is None:
                cx = max(2, min(xmin, width - badge_w - 2))
                cy = max(2, min(ymin - badge_h - 2, height - badge_h - 2))
                while collides([cx, cy, cx + badge_w, cy + badge_h]) and cy < height - badge_h - 10:
                    cy += badge_h + 3
                chosen_rect = [cx, cy, cx + badge_w, cy + badge_h]

            placed_labels.append(chosen_rect)
            label_x, label_y, r_x, r_y = chosen_rect

            # Draw sleek dark pill badge background
            cv2.rectangle(
                annotated,
                (label_x, label_y),
                (r_x, r_y),
                (18, 18, 18),
                -1,
            )
            cv2.rectangle(
                annotated,
                (label_x, label_y),
                (r_x, r_y),
                box_color,
                1,
                lineType=cv2.LINE_AA,
            )

            # Draw white text for maximum readability
            text_baseline_y = label_y + badge_h - pad_y - baseline + 1
            cv2.putText(
                annotated,
                label,
                (label_x + pad_x, text_baseline_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                (255, 255, 255),
                text_thickness,
                lineType=cv2.LINE_AA,
            )

        # 6. Save evidence image
        image_stem = Path(image_name).stem
        output_path = (
            self.output_dir
            / f"{image_stem}_evidence.jpg"
        )

        cv2.imwrite(
            str(output_path),
            annotated,
            [int(cv2.IMWRITE_JPEG_QUALITY), 95],
        )

        return output_path