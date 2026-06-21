# Training Evaluation Artifacts

This directory contains evaluation outputs from the YOLO11s PPE detector training run. Below is a guide to interpreting each artifact.

---

## 📈 Training Curves (`results.png`)

![Training Results](results.png)

This chart shows key metrics over each training epoch:

- **Box Loss** — How accurately the model predicts bounding-box coordinates. Lower is better.
- **Classification Loss** — How well the model distinguishes between classes (helmet vs. vest). Lower is better.
- **DFL Loss** (Distribution Focal Loss) — Measures fine-grained bounding-box regression quality.
- **Precision / Recall** — Trade-off between false positives and missed detections.
- **mAP50 / mAP50-95** — Mean Average Precision at various IoU thresholds.

> **What to look for:** Smooth, converging curves without sudden spikes indicate stable training. If losses plateau, the model has likely reached its capacity for the given architecture and data.

---

## 📊 Precision–Recall Curve (`BoxPR_curve.png`)

![PR Curve](BoxPR_curve.png)

The PR curve plots **Precision** (y-axis) against **Recall** (x-axis) at every possible confidence threshold.

- **Top-right corner** = ideal (high precision AND high recall).
- The **area under the curve (AUC)** equals **mAP50**.
- A curve that stays high across all recall values means the model rarely misses objects and rarely produces false positives.

> **Our result:** AUC ≈ **96.4%** — indicating excellent detection reliability across both classes.

---

## 📉 F1 Curve (`BoxF1_curve.png`)

![F1 Curve](BoxF1_curve.png)

The F1 score is the **harmonic mean of Precision and Recall**:

```
F1 = 2 × (Precision × Recall) / (Precision + Recall)
```

This curve shows F1 at every confidence threshold, helping you choose the **optimal operating point** — the confidence value where the model achieves the best balance.

> **Tip:** Pick the confidence threshold at the peak of this curve for deployment.

---

## 📉 Precision Curve (`BoxP_curve.png`)

![Precision Curve](BoxP_curve.png)

Shows how Precision changes as the confidence threshold increases. Higher thresholds reduce false positives but may miss valid detections.

---

## 🔲 Confusion Matrix (`confusion_matrix.png`)

![Confusion Matrix](confusion_matrix.png)

A standard confusion matrix showing **absolute counts** of predictions vs. ground truth. The diagonal represents correct predictions; off-diagonal cells represent errors.

---

## 🔲 Normalised Confusion Matrix (`confusion_matrix_normalized.png`)

![Normalised Confusion Matrix](confusion_matrix_normalized.png)

Same as above, but each row is normalised to percentages, making it easier to compare class-level accuracy regardless of class imbalance.

> **What to look for:** High values along the diagonal (close to 1.0) and low values off-diagonal.

---

## 🏷️ Label Distribution (`labels.jpg`)

![Labels](labels.jpg)

Visualises the distribution of bounding-box sizes, aspect ratios, and positions in the training dataset. This helps identify potential biases (e.g., if all helmets are always in the top half of the image).

---

## Why mAP50 and mAP50-95 Matter

| Metric | IoU Threshold | What It Measures |
|--------|:---:|---|
| **mAP50** | 0.50 | Detection accuracy with a lenient overlap requirement. Good for "did we find the object?" |
| **mAP50-95** | 0.50 – 0.95 (avg) | Averaged across stricter IoU thresholds. Rewards precise bounding boxes. This is the **COCO-standard** metric. |

- **mAP50 = 96.4%** — The model detects nearly all helmets and vests with reasonable localisation.
- **mAP50-95 = 77.9%** — Even under strict overlap requirements, the model performs well — indicating tight, accurate bounding boxes.

---

## Model Quality Assessment

| Indicator | Status |
|-----------|--------|
| Precision > 90% | ✅ 93.3% |
| Recall > 90% | ✅ 91.4% |
| mAP50 > 90% | ✅ 96.4% |
| mAP50-95 > 70% | ✅ 77.9% |
| Training converged | ✅ Stable loss curves |
| No severe class imbalance | ✅ Balanced confusion matrix |

> **Verdict:** This model is production-ready for real-time PPE compliance monitoring. It achieves strong performance across all key metrics with stable training dynamics.
