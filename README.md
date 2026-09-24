# AI-Powered Landslide Early Warning & Monitoring

Software-only hackathon prototype for dynamic landslide risk, escalation and evacuation assessment.

## Important demo behavior

The dashboard uses a **hybrid decision-support score**:
- a trained Random Forest model remains part of the pipeline;
- physically grounded rainfall, soil moisture, slope, terrain and historical-risk evidence is blended with the ML output;
- because the bundled training data is synthetic and highly imbalanced, the ML probability is deliberately prevented from acting as a standalone risk score;
- **if rainfall (1h/3h/24h), soil moisture and slope are all zero, the immediate-trigger risk is exactly 0%** rather than a non-zero class-prior prediction.

This is a prototype and must not be used as an operational warning/evacuation system without validated observations, calibrated thresholds, spatial validation and domain review.

## Run

```powershell
python -m venv venv
.\\venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt
python ml\\train_model.py
python app.py
```

Open `http://127.0.0.1:5000`.

## Dependencies

The requirements use compatible version ranges rather than forcing a pandas source build on newer Python versions.


## India-only GIS behavior
- The risk map is constrained to the India geographic region.
- LOW/no-significant-risk cells are not rendered as green overlays.
- Moderate, High and Critical cells are the only risk overlays shown.
- When there is no significant risk, the map shows no colored risk grid and displays a LOW/no-risk status message.
- The GIS cells are demonstration geometry and must be replaced with validated authoritative spatial observations for operational use.


## Authentication
The prototype includes a local login system. Users register with a Gmail address and a website password. Passwords are stored as secure hashes; the application never stores a Gmail/Google account password. Dashboard, GIS map and API routes require an authenticated session.

## Map behavior
The risk system is India-focused. When the current risk is 0%/LOW, no risk overlay cells are rendered. Low-risk cells are intentionally invisible. Only MODERATE, HIGH and CRITICAL overlays are shown when meaningful risk evidence exists. The Leaflet viewport is constrained to the India geographic region for the prototype.
