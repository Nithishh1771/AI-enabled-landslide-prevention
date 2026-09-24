from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session

from services.weather_service import get_live_weather
from services.data_service import demo_environment
from services.risk_engine import classify_risk, risk_indicators
from services.escalation import analyze_escalation, project_future
from services.evacuation import build_assessment_zone, evacuation_assessment

from ml.predict import predict_risk_probability

from database.db import (
    insert_environment,
    insert_risk,
    insert_alert,
    get_latest_environment,
    get_risk_history,
    get_alerts
)


# ============================================================
# API BLUEPRINT
# ============================================================

api_bp = Blueprint(
    "api",
    __name__,
    url_prefix="/api"
)


# ============================================================
# LOGIN PROTECTION
# ============================================================

@api_bp.before_request
def require_login():

    if "user_id" not in session:
        return fail(
            "Authentication required.",
            401
        )


# ============================================================
# NUMERIC INPUT LIMITS
# ============================================================

NUMERIC_INPUTS = {

    "rainfall_1h": (0, 500),

    "rainfall_3h": (0, 1000),

    "rainfall_24h": (0, 2000),

    "soil_moisture": (0, 100),

    "temperature": (-30, 60),

    "humidity": (0, 100),

    "elevation": (0, 9000),

    "slope": (0, 90),

    "aspect": (0, 360),

    "historical_landslide_density": (0, 1),
}


# ============================================================
# RESPONSE HELPERS
# ============================================================

def ok(data):

    return jsonify({
        "success": True,
        "data": data
    })


def fail(message, status=400):

    return jsonify({
        "success": False,
        "error": message
    }), status


# ============================================================
# PHYSICAL RISK SCORE
# ============================================================

def _physical_risk_score(reading):

    r1 = max(
        0.0,
        float(reading["rainfall_1h"])
    )

    r3 = max(
        r1,
        float(reading["rainfall_3h"])
    )

    r24 = max(
        r3,
        float(reading["rainfall_24h"])
    )

    soil = min(
        100.0,
        max(
            0.0,
            float(reading["soil_moisture"])
        )
    )

    slope = min(
        90.0,
        max(
            0.0,
            float(reading["slope"])
        )
    )

    hist = min(
        1.0,
        max(
            0.0,
            float(
                reading["historical_landslide_density"]
            )
        )
    )

    elevation = max(
        0.0,
        float(reading["elevation"])
    )

    components = {

        "rainfall_1h":
            min(
                r1 / 100.0,
                1.0
            ),

        "rainfall_3h":
            min(
                r3 / 200.0,
                1.0
            ),

        "rainfall_24h":
            min(
                r24 / 300.0,
                1.0
            ),

        "soil_moisture":
            soil / 100.0,

        "slope":
            min(
                slope / 45.0,
                1.0
            ),

        "historical_density":
            hist,

        "elevation":
            min(
                elevation / 2000.0,
                1.0
            )
    }

    weights = {

        "rainfall_1h": 0.20,

        "rainfall_3h": 0.15,

        "rainfall_24h": 0.15,

        "soil_moisture": 0.20,

        "slope": 0.15,

        "historical_density": 0.10,

        "elevation": 0.05
    }

    score = sum(

        components[key]
        *
        weights[key]

        for key in weights
    )

    return 100.0 * score


# ============================================================
# HYBRID RISK SCORE
# ============================================================

def predict_score(reading):

    """
    Final risk score:

        65% Physical Risk
        +
        35% Random Forest ML probability
    """

    physical = _physical_risk_score(
        reading
    )

    dynamic_signal = (

        float(
            reading["rainfall_1h"]
        )

        +

        float(
            reading["rainfall_3h"]
        )

        +

        float(
            reading["rainfall_24h"]
        )

        +

        float(
            reading["soil_moisture"]
        )

        +

        float(
            reading["slope"]
        )
    )

    if dynamic_signal <= 0.0:

        return 0.0

    try:

        ml_score = (

            predict_risk_probability(
                reading
            )

            *

            100.0
        )

    except FileNotFoundError:

        ml_score = physical

    score = (

        0.65 * physical

        +

        0.35 * ml_score
    )

    if physical < 15.0:

        score = min(
            score,
            20.0
        )

    elif physical < 30.0:

        score = min(
            score,
            35.0
        )

    score = max(
        0.0,
        min(
            100.0,
            score
        )
    )

    return round(
        score,
        2
    )


# ============================================================
# GET LIVE READING
# ============================================================

def get_live_reading():

    """
    Obtain the current live environmental conditions.

    Current prototype monitoring point:

        Latitude  = 27.33
        Longitude = 88.61

    Weather data:
        Open-Meteo

    Temporary GIS/terrain data:
        slope
        aspect
        historical density
        land cover

    These terrain values should later be replaced with
    authoritative GIS/DEM/historical datasets.
    """

    # --------------------------------------------------------
    # CURRENT INDIA MONITORING LOCATION
    # --------------------------------------------------------

    latitude = 27.33

    longitude = 88.61

    # --------------------------------------------------------
    # LIVE WEATHER
    # --------------------------------------------------------

    weather = get_live_weather(
        latitude,
        longitude
    )

    # --------------------------------------------------------
    # COMPLETE READING
    # --------------------------------------------------------

    reading = {

        "latitude":
            latitude,

        "longitude":
            longitude,

        "rainfall_1h":
            weather["rainfall_1h"],

        "rainfall_3h":
            weather["rainfall_3h"],

        "rainfall_24h":
            weather["rainfall_24h"],

        "soil_moisture":
            weather["soil_moisture"],

        "temperature":
            weather["temperature"],

        "humidity":
            weather["humidity"],

        "elevation":
            weather["elevation"],

        # ----------------------------------------------------
        # TEMPORARY TERRAIN VALUES
        # ----------------------------------------------------

        "slope":
            25.0,

        "aspect":
            180.0,

        "historical_landslide_density":
            0.20,

        "land_cover":
            "forest",

        # ----------------------------------------------------
        # METADATA
        # ----------------------------------------------------

        "timestamp":
            weather["timestamp"],

        "source":
            "Open-Meteo"
    }

    return reading


# ============================================================
# LIVE RISK CALCULATION
# ============================================================

def calculate_live_risk():

    reading = get_live_reading()

    score = predict_score(
        reading
    )

    category = classify_risk(
        score
    )

    try:

        ml_probability = (
            predict_risk_probability(
                reading
            )
        )

    except Exception:

        ml_probability = score / 100.0

    return (
        reading,
        score,
        category,
        ml_probability
    )


# ============================================================
# RISK ZONE GENERATOR
# ============================================================

def make_zones(
    center_lat,
    center_lon,
    base_score
):

    """
    Generate localized GIS risk cells around the
    CURRENT LIVE monitoring point.

    The center cell represents the live risk.

    Low-risk cells are intentionally hidden.
    """

    zones = []

    base_score = float(
        base_score
    )

    # --------------------------------------------------------
    # NO SIGNIFICANT RISK
    # --------------------------------------------------------

    if base_score <= 0:

        return zones

    # --------------------------------------------------------
    # LOCALIZED CELL SIZE
    # --------------------------------------------------------

    CELL_SIZE = 0.01

    # --------------------------------------------------------
    # 5 x 5 LOCAL GRID
    # --------------------------------------------------------

    for r in range(-2, 3):

        for c in range(-2, 3):

            distance = (

                abs(r)

                +

                abs(c)
            )

            # ------------------------------------------------
            # Risk decreases away from center
            # ------------------------------------------------

            score = (

                base_score

                +

                (2 - distance) * 3

                +

                ((r * c) % 3)
            )

            score = max(

                0.0,

                min(
                    100.0,
                    score
                )
            )

            category = classify_risk(
                score
            )

            # ------------------------------------------------
            # Hide LOW cells
            # ------------------------------------------------

            if category == "LOW":

                continue

            zone_lat = (

                center_lat

                +

                r * CELL_SIZE
            )

            zone_lon = (

                center_lon

                +

                c * CELL_SIZE
            )

            zones.append({

                "latitude":
                    round(
                        zone_lat,
                        5
                    ),

                "longitude":
                    round(
                        zone_lon,
                        5
                    ),

                "risk_score":
                    round(
                        score,
                        1
                    ),

                "risk_category":
                    category,

                "source":
                    "Live Open-Meteo + Hybrid Risk Engine"

            })

    return zones


# ============================================================
# CURRENT PACKAGE
# ============================================================

def current_package():

    """
    IMPORTANT:

    The dashboard, GIS, escalation, future projection
    and evacuation assessment all use the SAME LIVE
    Open-Meteo environmental reading.

    This prevents the GIS from displaying old SQLite/demo
    values while the dashboard displays live weather.
    """

    # --------------------------------------------------------
    # LIVE DATA
    # --------------------------------------------------------

    reading = get_live_reading()

    # --------------------------------------------------------
    # CURRENT RISK
    # --------------------------------------------------------

    score = predict_score(
        reading
    )

    category = classify_risk(
        score
    )

    # --------------------------------------------------------
    # DATABASE HISTORY
    # --------------------------------------------------------

    history = get_risk_history()

    # --------------------------------------------------------
    # CURRENT LIVE ENTRY
    # --------------------------------------------------------

    live_history_entry = {

        "timestamp":
            reading["timestamp"],

        "risk_score":
            score,

        "risk_category":
            category,

        "latitude":
            reading["latitude"],

        "longitude":
            reading["longitude"]
    }

    # --------------------------------------------------------
    # IF NO HISTORY EXISTS
    # --------------------------------------------------------

    if not history:

        history = [

            {

                "timestamp":
                    f"T-{i}h",

                "risk_score":
                    score,

                "risk_category":
                    category

            }

            for i in range(
                4,
                -1,
                -1
            )
        ]

    else:

        # ----------------------------------------------------
        # Add current live risk to the calculation history.
        # ----------------------------------------------------

        history = history + [
            live_history_entry
        ]

    # --------------------------------------------------------
    # ESCALATION
    # --------------------------------------------------------

    escalation = analyze_escalation(
        history
    )

    return (

        reading,

        score,

        category,

        history,

        escalation
    )


# ============================================================
# HEALTH
# ============================================================

@api_bp.get("/health")
def health():

    return ok({

        "status":
            "healthy",

        "service":
            "landslide-risk-api",

        "live_weather":
            "Open-Meteo",

        "risk_engine":
            "Random Forest + Physical Hybrid",

        "gis":
            "Connected to live risk"
    })


# ============================================================
# LIVE RISK
# ============================================================

@api_bp.get("/live-risk")
def live_risk():

    try:

        (
            reading,
            score,
            category,
            ml_probability
        ) = calculate_live_risk()

        return ok({

            "live":
                True,

            # ------------------------------------------------
            # LOCATION
            # ------------------------------------------------

            "location": {

                "latitude":
                    reading["latitude"],

                "longitude":
                    reading["longitude"]
            },

            # ------------------------------------------------
            # WEATHER
            # ------------------------------------------------

            "weather": {

                "rainfall_1h":
                    reading["rainfall_1h"],

                "rainfall_3h":
                    reading["rainfall_3h"],

                "rainfall_24h":
                    reading["rainfall_24h"],

                "soil_moisture":
                    reading["soil_moisture"],

                "temperature":
                    reading["temperature"],

                "humidity":
                    reading["humidity"],

                "elevation":
                    reading["elevation"]
            },

            # ------------------------------------------------
            # TERRAIN
            # ------------------------------------------------

            "terrain": {

                "slope":
                    reading["slope"],

                "aspect":
                    reading["aspect"],

                "historical_landslide_density":
                    reading[
                        "historical_landslide_density"
                    ],

                "land_cover":
                    reading["land_cover"]
            },

            # ------------------------------------------------
            # ML
            # ------------------------------------------------

            "ml_probability":
                round(
                    ml_probability,
                    4
                ),

            "ml_probability_percent":
                round(
                    ml_probability * 100,
                    2
                ),

            # ------------------------------------------------
            # FINAL RISK
            # ------------------------------------------------

            "risk_score":
                score,

            "risk_category":
                category,

            # ------------------------------------------------
            # INDICATORS
            # ------------------------------------------------

            "risk_indicators":
                risk_indicators(
                    reading
                ),

            # ------------------------------------------------
            # SOURCE
            # ------------------------------------------------

            "source":
                "Open-Meteo + Random Forest + Hybrid Risk Engine",

            # ------------------------------------------------
            # TIMESTAMP
            # ------------------------------------------------

            "timestamp":
                reading["timestamp"]
        })

    except Exception as e:

        return fail(

            f"Live risk calculation failed: {str(e)}",

            502
        )


# ============================================================
# LIVE WEATHER DATA
# ============================================================

@api_bp.get("/live-data")
def live_data():

    latitude = 27.33

    longitude = 88.61

    try:

        weather = get_live_weather(

            latitude,

            longitude
        )

        return ok(
            weather
        )

    except Exception as e:

        return fail(

            f"Unable to fetch live weather data: {str(e)}",

            502
        )


# ============================================================
# ENVIRONMENT
# ============================================================

@api_bp.get("/environment")
def environment():

    try:

        reading = get_live_reading()

        return ok(
            reading
        )

    except Exception as e:

        return fail(

            f"Unable to fetch live environment data: {str(e)}",

            502
        )


# ============================================================
# RISK HISTORY
# ============================================================

@api_bp.get("/risk-history")
def risk_history():

    return ok(

        current_package()[3]
    )


# ============================================================
# RISK
# ============================================================

@api_bp.get("/risk")
def risk():

    (
        reading,
        score,
        category,
        history,
        escalation
    ) = current_package()

    probability = (
        score / 100
    )

    return ok({

        "risk_score":
            round(
                score,
                1
            ),

        "risk_probability":
            round(
                probability,
                4
            ),

        "category":
            category,

        "indicators":
            risk_indicators(
                reading
            ),

        "escalation":
            escalation,

        "evacuation_assessment":
            evacuation_assessment(
                score,
                escalation
            )
    })


# ============================================================
# FUTURE RISK
# ============================================================

@api_bp.get("/future-risk")
def future_risk():

    return ok(

        project_future(
            current_package()[3]
        )
    )


# ============================================================
# RISK ZONES
# ============================================================

@api_bp.get("/zones")
def zones():

    (
        reading,
        score,
        category,
        history,
        escalation
    ) = current_package()

    zone_rows = make_zones(

        reading["latitude"],

        reading["longitude"],

        score
    )

    return ok(
        zone_rows
    )


# ============================================================
# ALERTS
# ============================================================

@api_bp.get("/alerts")
def alerts():

    stored_alerts = get_alerts()

    if stored_alerts:

        return ok(
            stored_alerts
        )

    return ok([

        {

            "timestamp":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "severity":
                "INFO",

            "message":
                "No stored alerts. Live monitoring is active.",

            "latitude":
                27.33,

            "longitude":
                88.61,

            "status":
                "LIVE"
        }

    ])


# ============================================================
# DASHBOARD DATA
# ============================================================

@api_bp.get("/dashboard")
def dashboard_data():

    try:

        (
            reading,
            score,
            category,
            history,
            escalation
        ) = current_package()

        # ----------------------------------------------------
        # FUTURE RISK
        # ----------------------------------------------------

        future = project_future(
            history
        )

        # ----------------------------------------------------
        # LIVE GIS ZONES
        # ----------------------------------------------------

        zone_rows = make_zones(

            reading["latitude"],

            reading["longitude"],

            score
        )

        # ----------------------------------------------------
        # ASSESSMENT ZONE
        # ----------------------------------------------------

        geom, area = build_assessment_zone(
            zone_rows
        )

        # ----------------------------------------------------
        # RETURN COMPLETE DASHBOARD
        # ----------------------------------------------------

        return ok({

            "mode":
                "LIVE MONITORING",

            # ------------------------------------------------
            # ENVIRONMENT
            # ------------------------------------------------

            "environment":
                reading,

            # ------------------------------------------------
            # RISK
            # ------------------------------------------------

            "risk": {

                "score":
                    round(
                        score,
                        1
                    ),

                "category":
                    category,

                "probability":
                    round(
                        score / 100,
                        4
                    ),

                "indicators":
                    risk_indicators(
                        reading
                    )
            },

            # ------------------------------------------------
            # HISTORY
            # ------------------------------------------------

            "history":
                history,

            # ------------------------------------------------
            # ESCALATION
            # ------------------------------------------------

            "escalation":
                escalation,

            # ------------------------------------------------
            # FUTURE
            # ------------------------------------------------

            "future":
                future,

            # ------------------------------------------------
            # GIS ZONES
            # ------------------------------------------------

            "zones":
                zone_rows,

            # ------------------------------------------------
            # AREA
            # ------------------------------------------------

            "assessment_area_km2":
                area,

            # ------------------------------------------------
            # GEOJSON
            # ------------------------------------------------

            "assessment_zone":

                (
                    geom.__geo_interface__

                    if geom

                    else None
                ),

            # ------------------------------------------------
            # EVACUATION
            # ------------------------------------------------

            "evacuation_assessment":
                evacuation_assessment(
                    score,
                    escalation
                ),

            # ------------------------------------------------
            # SOURCE
            # ------------------------------------------------

            "data_source":
                "Open-Meteo + Random Forest + Hybrid Risk Engine",

            # ------------------------------------------------
            # LIVE FLAG
            # ------------------------------------------------

            "live":
                True,

            # ------------------------------------------------
            # TIMESTAMP
            # ------------------------------------------------

            "timestamp":
                reading["timestamp"],

            # ------------------------------------------------
            # DISCLAIMER
            # ------------------------------------------------

            "assessment_disclaimer":

                "Decision-support assessment for authorized authorities; not an autonomous evacuation order."

        })

    except Exception as e:

        return fail(

            f"Dashboard data calculation failed: {str(e)}",

            502
        )


# ============================================================
# SIMULATE
# ============================================================

@api_bp.post("/simulate")
def simulate():

    payload = request.get_json(
        silent=True
    )

    # --------------------------------------------------------
    # VALIDATE JSON
    # --------------------------------------------------------

    if payload is None:

        return fail(
            "Send a JSON object."
        )

    # --------------------------------------------------------
    # BASE DEMO ENVIRONMENT
    # --------------------------------------------------------

    base = demo_environment()

    # --------------------------------------------------------
    # VALIDATE INPUTS
    # --------------------------------------------------------

    for key, (
        low,
        high
    ) in NUMERIC_INPUTS.items():

        if key not in payload:

            continue

        try:

            value = float(
                payload[key]
            )

        except (
            TypeError,
            ValueError
        ):

            return fail(

                f"{key} must be numeric."
            )

        if not (

            low
            <=
            value
            <=
            high
        ):

            return fail(

                f"{key} must be between "
                f"{low} and {high}."
            )

        base[key] = value

    # --------------------------------------------------------
    # RAINFALL CONSISTENCY
    # --------------------------------------------------------

    base["rainfall_3h"] = max(

        base["rainfall_1h"],

        base["rainfall_3h"]
    )

    base["rainfall_24h"] = max(

        base["rainfall_3h"],

        base["rainfall_24h"]
    )

    # --------------------------------------------------------
    # ASPECT
    # --------------------------------------------------------

    base["aspect"] = (

        base["aspect"]

        %

        360
    )

    # --------------------------------------------------------
    # TIMESTAMP
    # --------------------------------------------------------

    base["timestamp"] = (

        datetime.now(
            timezone.utc
        ).isoformat()
    )

    # --------------------------------------------------------
    # SAVE ENVIRONMENT
    # --------------------------------------------------------

    insert_environment(
        base
    )

    # --------------------------------------------------------
    # CALCULATE RISK
    # --------------------------------------------------------

    score = predict_score(
        base
    )

    category = classify_risk(
        score
    )

    # --------------------------------------------------------
    # SAVE RISK
    # --------------------------------------------------------

    insert_risk(

        base["timestamp"],

        base["latitude"],

        base["longitude"],

        score,

        category
    )

    # --------------------------------------------------------
    # HISTORY
    # --------------------------------------------------------

    history = get_risk_history()

    # --------------------------------------------------------
    # ESCALATION
    # --------------------------------------------------------

    escalation = analyze_escalation(
        history
    )

    # --------------------------------------------------------
    # ALERT
    # --------------------------------------------------------

    if (

        category == "CRITICAL"

        or

        escalation["status"]
        ==
        "RAPIDLY INCREASING"
    ):

        insert_alert(

            base["timestamp"],

            "CRITICAL",

            "High landslide risk or rapid escalation detected; authority review recommended.",

            base["latitude"],

            base["longitude"]
        )

    # --------------------------------------------------------
    # RETURN
    # --------------------------------------------------------

    return ok({

        "risk_score":
            round(
                score,
                1
            ),

        "category":
            category,

        "escalation":
            escalation,

        "evacuation_assessment":
            evacuation_assessment(
                score,
                escalation
            )
    })