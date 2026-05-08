from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List
from pathlib import Path
import subprocess
import sys

from ..database import get_db, SessionLocal
from ..deps import get_current_user
from .. import models, schemas

router = APIRouter(prefix="/training", tags=["Training"])

TRAIN_SCRIPT = Path(__file__).resolve().parent.parent.parent / "training" / "train_finbert.py"


def _run_training(run_id: int, epochs: int, batch_size: int, lr: float):
    db = SessionLocal()
    try:
        run = db.query(models.TrainingRun).filter(models.TrainingRun.id == run_id).first()
        run.status     = models.TrainingStatus.running
        run.started_at = datetime.now(timezone.utc)
        db.commit()

        env_overrides = {
            "FINSENSE_EPOCHS":     str(epochs),
            "FINSENSE_BATCH_SIZE": str(batch_size),
            "FINSENSE_LR":         str(lr),
        }
        import os
        env = {**os.environ, **env_overrides}

        result = subprocess.run(
            [sys.executable, str(TRAIN_SCRIPT)],
            capture_output=True, text=True, env=env,
        )

        run.log_output  = (result.stdout + result.stderr)[-10000:]  # keep last 10k chars
        run.finished_at = datetime.now(timezone.utc)

        if result.returncode == 0:
            run.status = models.TrainingStatus.completed
            metrics_path = Path(__file__).resolve().parent.parent.parent / "training" / "metrics" / "metrics.json"
            if metrics_path.exists():
                import json
                m = json.loads(metrics_path.read_text())
                run.test_accuracy = m.get("test_accuracy")
                run.test_f1       = m.get("test_f1")
        else:
            run.status = models.TrainingStatus.failed

        db.commit()
    finally:
        db.close()


@router.post("", response_model=schemas.TrainingRunOut, status_code=202)
def start_training(
    payload: schemas.TrainingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    active = db.query(models.TrainingRun).filter(
        models.TrainingRun.status == models.TrainingStatus.running
    ).first()
    if active:
        raise HTTPException(status_code=409, detail="A training run is already in progress")

    run = models.TrainingRun(
        user_id=current_user.id,
        epochs=payload.epochs,
        batch_size=payload.batch_size,
        learning_rate=payload.learning_rate,
        status=models.TrainingStatus.pending,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    background_tasks.add_task(_run_training, run.id, payload.epochs, payload.batch_size, payload.learning_rate)
    return run


@router.get("", response_model=List[schemas.TrainingRunOut])
def list_runs(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    return db.query(models.TrainingRun).order_by(
        models.TrainingRun.created_at.desc()
    ).offset(skip).limit(limit).all()


@router.get("/latest", response_model=schemas.TrainingRunOut)
def latest_run(
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    run = db.query(models.TrainingRun).order_by(models.TrainingRun.created_at.desc()).first()
    if not run:
        raise HTTPException(status_code=404, detail="No training runs found")
    return run


@router.get("/{run_id}", response_model=schemas.TrainingRunOut)
def get_run(
    run_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    run = db.query(models.TrainingRun).filter(models.TrainingRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Training run not found")
    return run
