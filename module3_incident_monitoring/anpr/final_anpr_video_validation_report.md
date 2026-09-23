# Module 3 ANPR: Final End-to-End Video Validation Report

**Evaluation Date**: September 4, 2026  
**Input Video**: `module3_incident_anpr/test video/test_video.mp4` ($1280 \times 720\text{ HD}$, 240 frames @ 24 FPS)  
**Annotated Output Artifact**: [`module3_incident_anpr/output_videos/anpr_annotated_test_video.mp4`](file:///c:/SIH/prototype/smart-transport-monitoring/module3_incident_anpr/output_videos/anpr_annotated_test_video.mp4)  
**Telemetry File**: [`module3_incident_anpr/results/anpr_video_test_results_test_video.json`](file:///c:/SIH/prototype/smart-transport-monitoring/module3_incident_anpr/results/anpr_video_test_results_test_video.json)  
**Trained Weights**: `module3_incident_anpr/ocr_checkpoints/best_ocr_model.pt`

---

## 1. Executive Summary & Verification Methodology

This report presents a scientifically grounded review of the first end-to-end video execution of the Module 3 ANPR pipeline across all 240 frames of the test clip.

### Distinction of Evidence Types:
1. **Measured Quantitative Metrics**: Directly recorded by the video test telemetry script and independent benchmark evaluators.
2. **Qualitative Observations**: Visual assessment of bounding box alignment, tracking continuity, and visual plate readability in the rendered output video.
3. **Unverifiable Predictions**: Cases where motion blur, distance, or lighting prevents definitive human verification of true license plate alphanumeric characters.

---

## 2. Track-by-Track Structured Validation Table

| Track ID | Vehicle Class | Visual Plate Region Detected | Final Consensus Plate | Reading Count (Voting) | Consensus Confidence | Validation Category | Forensic Observations |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Track 1** | Auto Rickshaw / Car | `[✓] Yes` (Rear plate) | **`MH1749`** | 20 | 0.548 | **Truncated / Partial** | State prefix (`MH`) and numeric digits (`1749`) recognized; intermediate district code collapsed. |
| **Track 6** | Car (Sedan) | `[✓] Yes` (Rear plate) | **`KH01AM`** | 20 | 0.282 | **Substituted / Partial** | Plate localized cleanly; state prefix predicted as `KH` (glyph substitution for `MH`/`KA`) with district `01`. |
| **Track 10** | Bus / Heavy Vehicle | `[✓] Yes` (Front/Rear) | **`MH01`** | 20 | 0.495 | **Truncated** | State prefix (`MH01`) resolved consistently; trailing registration digits omitted due to low vertical crop height. |
| **Track 13** | Auto Rickshaw | `[✓] Yes` (Yellow plate) | **`MH02BR3`** | 20 | 0.614 | **Substituted / Partial** | Prefix (`MH02`) and series (`BR`) resolved; final 4-digit sequence truncated to single digit `3`. |
| **Track 14** | Car (Hatchback) | `[✓] Yes` (White plate) | **`MH4BT`** | 20 | 0.571 | **Truncated** | Maharashtra prefix structure; intermediate digits partially collapsed. |
| **Track 15** | Two-Wheeler (Scooter) | `[✓] Yes` (Rear plate) | **`TL14`** | 20 | 0.328 | **Substituted / Partial** | Compact motorcycle vertical plate; candidate region localized, partial characters resolved. |
| **Track 17** | Car | `[✓] Yes` (Distant crop) | **`TN214`** | 10 | 0.368 | **Unverifiable** | Low resolution on distant vehicle prevents human verification of ground-truth plate text; model emits plausible prefix `TN`. |
| **Track 19** | Car | `[✓] Yes` (Front crop) | **`TR01`** | 19 | 0.247 | **Unverifiable** | High motion blur at frame perimeter prevents visual ground-truth confirmation. |
| **Tracks 2–5, 7–9, 11–12, 16, 18** | Distant / Partially Occluded | `[✗] No` (Below scale threshold) | *None* (`unavailable`) | 0 | 0.000 | **Correct Suppression** | Distant background vehicles were filtered out, avoiding false-positive OCR hallucinations. |

---

## 3. Directly Measured Quantitative Telemetry

All metrics below are extracted directly from [`module3_incident_anpr/results/anpr_video_test_results_test_video.json`](file:///c:/SIH/prototype/smart-transport-monitoring/module3_incident_anpr/results/anpr_video_test_results_test_video.json):

* **Total Video Frames Processed**: **240 / 240 frames** (10.0 seconds of footage at 24.0 FPS).
* **Total Execution Wall Time**: **38.55 seconds** (on host CPU).
* **Average Processing Throughput**: **6.23 FPS** (Mean frame latency: **159.21 ms / frame**).
* **Total Vehicle Bounding Box Detections**: **1,343 detections**.
* **Unique Vehicle Track IDs Assigned**: **19 tracks**.
* **Plate Candidates Localized by Stage 1**: **406 candidates**.
* **OCR Inference Passes Executed**: **406 passes**.
* **OCR Extractions Meeting Minimum Character Threshold ($\ge 4$ chars)**: **397 passes** ($97.78\%$ conversion rate of localized crops).
* **Unique Vehicle Tracks Reaching Consensus ($\ge 2$ agreeing votes)**: **8 tracks**.

---

## 4. Qualitative Assessment & Component Verification

### 1. Vehicle Detection & Tracking Continuity
* **Observation**: YOLO vehicle detection reliably bounded active vehicles across varying scales. Track IDs remained associated with their respective vehicles across their visible trajectories.

### 2. Number Plate Localization (`PlateDetector`)
* **Observation**: Visual review of the output video confirmed that Stage 1 bounding boxes successfully enclosed the physical license plate regions on foreground cars, buses, and auto-rickshaws.

### 3. OCR Performance vs. Independent Benchmark
* **Observation**: The OCR behavior observed in video inference is consistent with the independently evaluated static test benchmark:
  * **Independent Benchmark Baseline (`best_ocr_model.pt` on 170 test crops)**:
    * Exact Plate Match Accuracy: **20.59%**
    * Character Accuracy: **74.55%**
    * Character Error Rate (CER): **0.2545**
  * **Video Inference Behavior**: The model consistently identified state prefixes (`MH`, `01`, `02`) and prominent numeric clusters, but exhibited character truncation on compact/blurry crops, matching the static error audit (where deletions accounted for $29.05\%$ of alignment errors and mean prediction residual was $-0.66$ chars).

### 4. Temporal Aggregation Stability (`TrackPlateAggregator`)
* **Observation**: Single-frame OCR outputs displayed character variations between frames due to motion blur and perspective changes. Temporal voting across a sliding window of 10–20 frame observations stabilized the output into consistent track-level consensus strings.

---

## 5. Final Engineering Conclusion

1. **Pipeline Integration Status**: **FUNCTIONALLY SUCCESSFUL**.
   * The complete multi-stage data flow ($\text{Video Stream} \to \text{Vehicle Detection} \to \text{Tracking} \to \text{Plate Localization} \to \text{CRNN OCR} \to \text{Temporal Aggregation} \to \text{Video Annotation \& Telemetry}$) executed deterministically across all 240 frames at 6.23 FPS.
2. **Recognition Quality Separation**:
   * Pipeline functionality and data exchange are fully operational.
   * Final text reading accuracy remains strictly bounded by the current baseline OCR model weights (trained on 1,353 samples). The modular separation ensures that future OCR weight or architecture upgrades drop in directly without altering pipeline integration code.
