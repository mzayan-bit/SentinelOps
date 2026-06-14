# SentinelOps Architecture

This document describes the MLOps architecture for the SentinelOps project.

## Dataset Flow
Raw data is ingested, validated, and versioned using DVC. We track data provenance and preprocessing scripts, ensuring full reproducibility from raw data to the final training sets.

## Training Flow
Model training is triggered locally or via CI/CD. The Ultralytics YOLO framework is used for computer vision tasks. The training code accesses versioned data through DVC.

## Experiment Tracking
MLflow is used to track all experiments, including hyperparameters, evaluation metrics (e.g., mAP, loss), and metadata. This allows for systematically comparing different model versions.

## Model Registry
Validated models are registered in the MLflow Model Registry. This provides a central repository for model artifacts, tracking stage transitions from Staging to Production.

## Inference Pipeline
A FastAPI application serves the model for inference. It loads the production model from the registry and provides REST endpoints for predictions.

## Monitoring Pipeline
Evidently is used to monitor model performance and data drift in production. We track input feature distributions and target predictions to detect degradation early.
