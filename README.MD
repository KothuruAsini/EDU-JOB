# Edu2Job - Django + RandomForest Job Role Predictor

## Overview
This project trains a RandomForest model on your JobRole dataset and serves predictions via Django REST API with JWT auth. Frontend is simple static HTML + Bootstrap.

## Dataset
Uploaded dataset path: `/mnt/data/JobRole.xlsx`
(if running locally on Windows, copy `JobRole.xlsx` into project root or change `DATA_PATH` in `train_pipeline.py`)

## Steps to reproduce

1. Create and activate virtualenv:
   - Windows (PowerShell):
     ```
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     pip install -r requirements.txt
     ```
   - Linux/Mac:
     ```
     python3 -m venv venv
     source venv/bin/activate
     pip install -r requirements.txt
     ```

2. Train pipeline & generate artifacts:
