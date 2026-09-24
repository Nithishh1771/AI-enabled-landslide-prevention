let chart;

const riskColors = {
  LOW: "#2e8b57",
  MODERATE: "#e4c441",
  HIGH: "#e67e22",
  CRITICAL: "#c0392b"
};


async function getJSON(url, options = {}) {

  const response = await fetch(url, options);

  const body = await response.json();

  if (!response.ok || !body.success) {
    throw new Error(
      body.error || `HTTP ${response.status}`
    );
  }

  return body.data;
}


function setRiskBadge(el, category) {

  el.textContent = category;

  el.style.background =
    riskColors[category] || "#596b74";
}


function esc(value) {

  return String(value).replace(
    /[&<>"']/g,
    ch => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;"
    }[ch])
  );
}


/* =========================================================
   LOAD LIVE RISK
   ========================================================= */

async function loadLiveRisk() {

  const live = await getJSON("/api/live-risk");

  const weather = live.weather;
  const terrain = live.terrain;
const liveStatus = document.querySelector("#liveStatus");
if (liveStatus) {
  liveStatus.textContent = live.live ? "LIVE" : "OFFLINE";
}


const liveLatitude =
  document.querySelector("#liveLatitude");

if (liveLatitude) {
  liveLatitude.textContent =
    Number(live.location.latitude).toFixed(4);
}


const liveLongitude =
  document.querySelector("#liveLongitude");

if (liveLongitude) {
  liveLongitude.textContent =
    Number(live.location.longitude).toFixed(4);
}


const liveTimestamp =
  document.querySelector("#liveTimestamp");

if (liveTimestamp) {
  liveTimestamp.textContent =
    new Date(live.timestamp).toLocaleString();
}
  /* -------------------------------------------------------
     CURRENT RISK
     ------------------------------------------------------- */

  document.querySelector("#riskScore").textContent =
    `${Number(live.risk_score).toFixed(1)}%`;

  setRiskBadge(
    document.querySelector("#riskCategory"),
    live.risk_category
  );


  /* -------------------------------------------------------
     LIVE WEATHER
     ------------------------------------------------------- */

  document.querySelector("#rainfall").textContent =
    `${Number(weather.rainfall_1h).toFixed(1)} mm`;

  document.querySelector("#soil").textContent =
    `${Number(weather.soil_moisture).toFixed(1)}%`;

  document.querySelector("#slope").textContent =
    `${Number(terrain.slope).toFixed(1)}°`;

  document.querySelector("#elevation").textContent =
    `${Number(weather.elevation).toFixed(0)} m`;


  /* -------------------------------------------------------
     LIVE INDICATORS
     ------------------------------------------------------- */

  document.querySelector("#indicators").innerHTML =
    live.risk_indicators
      .map(
        indicator =>
          `<li>${esc(indicator)}</li>`
      )
      .join("");


  /* -------------------------------------------------------
     LIVE STATUS
     ------------------------------------------------------- */

  const status = document.querySelector("#simStatus");

  if (status) {

    status.textContent =
      `LIVE • ${live.risk_category} risk • ` +
      `ML probability ${Number(
        live.ml_probability_percent
      ).toFixed(2)}% • ` +
      `Updated ${new Date(
        live.timestamp
      ).toLocaleTimeString()}`;
  }


  return live;
}


/* =========================================================
   LOAD DASHBOARD SUPPORT DATA
   ========================================================= */

async function loadDashboardSupport() {

  const d = await getJSON("/api/dashboard");

  /* -------------------------------------------------------
     Assessment area
     ------------------------------------------------------- */

  document.querySelector("#area").textContent =
    `${Number(
      d.assessment_area_km2
    ).toFixed(3)} km²`;


  /* -------------------------------------------------------
     Risk escalation
     ------------------------------------------------------- */

  document.querySelector("#trend").textContent =
    d.escalation.status;

  document.querySelector("#escalationText").textContent =
    `Change: ${Number(
      d.escalation.absolute_change
    ).toFixed(1)} points; ` +
    `recent momentum: ${Number(
      d.escalation.recent_momentum
    ).toFixed(1)
    } points/hour.`;


  /* -------------------------------------------------------
     Future projection
     ------------------------------------------------------- */

  document.querySelector("#futureCards").innerHTML =
    d.future.projections
      .map(
        x =>
          `<div>
            <b>+${x.hours_ahead}h</b><br>
            <strong>
              ${Number(x.risk_score).toFixed(1)}%
            </strong>
          </div>`
      )
      .join("");


  /* -------------------------------------------------------
     Evacuation assessment
     ------------------------------------------------------- */

  const assessment =
    d.evacuation_assessment;

  document.querySelector(
    "#assessmentLevel"
  ).textContent =
    assessment.level.replaceAll("_", " ");

  document.querySelector(
    "#assessmentAction"
  ).textContent =
    assessment.recommended_action;


  /* -------------------------------------------------------
     Risk history chart
     ------------------------------------------------------- */

  const labels =
    d.history.map(
      (x, i) =>
        x.timestamp?.startsWith("T")
          ? x.timestamp
          : `T-${d.history.length - i - 1}h`
    );

  const values =
    d.history.map(
      x => Number(x.risk_score)
    );


  if (chart) {
    chart.destroy();
  }


  chart = new Chart(
    document.getElementById("riskChart"),
    {
      type: "line",

      data: {
        labels,

        datasets: [
          {
            label: "Risk %",
            data: values,
            tension: 0.25,
            fill: false,
            borderWidth: 3
          }
        ]
      },

      options: {
        responsive: true,

        scales: {
          y: {
            min: 0,
            max: 100
          }
        },

        plugins: {
          legend: {
            display: false
          }
        }
      }
    }
  );


  /* -------------------------------------------------------
     Alerts
     ------------------------------------------------------- */

  const alerts =
    await getJSON("/api/alerts");

  document.querySelector("#alerts").innerHTML =
    alerts.length
      ? alerts
          .map(
            alert =>
              `<div class="alert">
                <b>${esc(alert.severity)}</b>
                — ${esc(alert.message)}
                <small>
                  ${esc(alert.timestamp)}
                </small>
              </div>`
          )
          .join("")
      : `<p class="muted">No alerts.</p>`;


  /* -------------------------------------------------------
     GIS MAP
     ------------------------------------------------------- */

  /*
     NOTE:
     The map currently receives zones from /api/dashboard.
     We will connect the zone generation to the live risk
     engine in the next backend step.
  */

  const center =
    d.environment
      ? [
          d.environment.latitude,
          d.environment.longitude
        ]
      : [27.33, 88.61];

  drawMap(
    d.zones,
    d.assessment_zone,
    center
  );

  return d;
}


/* =========================================================
   LOAD COMPLETE DASHBOARD
   ========================================================= */

async function loadDashboard() {

  try {

    /*
     IMPORTANT:

     /api/live-risk
       → current live environmental data
       → Random Forest
       → Hybrid Risk Engine

     /api/dashboard
       → chart
       → escalation
       → future projection
       → evacuation assessment
       → alerts
       → GIS support data
    */

    await Promise.all([
      loadLiveRisk(),
      loadDashboardSupport()
    ]);

  } catch (err) {

    console.error(err);

    const status =
      document.querySelector("#simStatus");

    if (status) {
      status.textContent =
        `Error: ${err.message}`;
    }
  }
}


/* =========================================================
   SIMULATION
   ========================================================= */

async function runSimulation() {

  const payload = {

    rainfall_1h:
      Number(
        document.querySelector("#simRain1").value
      ),

    rainfall_3h:
      Number(
        document.querySelector("#simRain3").value
      ),

    rainfall_24h:
      Number(
        document.querySelector("#simRain24").value
      ),

    soil_moisture:
      Number(
        document.querySelector("#simSoil").value
      ),

    slope:
      Number(
        document.querySelector("#simSlope").value
      ),

    elevation:
      Number(
        document.querySelector("#simElev").value
      ),

    historical_landslide_density:
      Number(
        document.querySelector("#simHist").value
      )
  };


  const status =
    document.querySelector("#simStatus");

  status.textContent =
    "Running simulation…";


  try {

    const result =
      await getJSON(
        "/api/simulate",
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json"
          },

          body:
            JSON.stringify(payload)
        }
      );


    status.textContent =
      `Simulation result: ${
        result.category
      } risk (${
        Number(
          result.risk_score
        ).toFixed(1)
      }%).`;


    /*
       Reload the dashboard.

       The simulation result is stored in
       SQLite and therefore becomes part of
       the risk history.
    */

    await loadDashboard();


  } catch (err) {

    status.textContent =
      `Simulation failed: ${
        err.message
      }`;
  }
}


/* =========================================================
   INDIA MAP
   ========================================================= */

function drawMap(
  zones,
  zone,
  center
) {

  const el =
    document.getElementById("map");

  if (!el) {
    return;
  }


  if (el._mapInstance) {
    el._mapInstance.remove();
  }


  /* -------------------------------------------------------
     India geographic boundary
     ------------------------------------------------------- */

  const INDIA_BOUNDS = [
    [6.0, 68.0],
    [37.5, 97.5]
  ];


  const lat =
    Math.max(
      6.1,
      Math.min(
        37.4,
        Number(center[0])
      )
    );


  const lon =
    Math.max(
      68.1,
      Math.min(
        97.4,
        Number(center[1])
      )
    );


  /* -------------------------------------------------------
     Create map
     ------------------------------------------------------- */

  const map =
    L.map(
      el,
      {
        minZoom: 5,
        maxZoom: 14,

        maxBounds:
          INDIA_BOUNDS,

        maxBoundsViscosity: 1.0,

        worldCopyJump: false
      }
    ).setView(
      [lat, lon],
      9
    );


  el._mapInstance = map;


  /* -------------------------------------------------------
     OpenStreetMap
     ------------------------------------------------------- */

  L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
      attribution:
        "© OpenStreetMap contributors",

      noWrap: true
    }
  ).addTo(map);


  /* -------------------------------------------------------
     Current risk from live dashboard card
     ------------------------------------------------------- */

  const overallRisk =
    Number(
      document
        .querySelector("#riskScore")
        ?.textContent
        .replace("%", "")
        || 0
    );


  const visibleZones =
    overallRisk <= 0
      ? []
      : (zones || []).filter(
          z =>
            [
              "MODERATE",
              "HIGH",
              "CRITICAL"
            ].includes(
              z.risk_category
            )
        );


  /* -------------------------------------------------------
     No significant risk
     ------------------------------------------------------- */

  if (
    visibleZones.length === 0
  ) {

    const status =
      L.control({
        position: "topright"
      });


    status.onAdd =
      function() {

        const div =
          L.DomUtil.create(
            "div",
            "map-status"
          );


        div.innerHTML =
          "<strong>No significant landslide risk</strong>" +
          "<br>" +
          "<span>Low risk — no risk overlay displayed.</span>";


        return div;
      };


    status.addTo(map);


    map.fitBounds(
      INDIA_BOUNDS,
      {
        padding: [20, 20]
      }
    );


    return;
  }


  /* -------------------------------------------------------
     Risk colors
     ------------------------------------------------------- */

  const colors = {

    MODERATE:
      "#e4c441",

    HIGH:
      "#e67e22",

    CRITICAL:
      "#c0392b"
  };


  /* -------------------------------------------------------
     Draw risk cells
     ------------------------------------------------------- */

  visibleZones.forEach(
    z => {

      const color =
        colors[
          z.risk_category
        ];


      L.rectangle(

        [
          [
            z.latitude - 0.035,
            z.longitude - 0.035
          ],

          [
            z.latitude + 0.035,
            z.longitude + 0.035
          ]
        ],

        {
          color,

          weight: 1,

          fillColor:
            color,

          fillOpacity:
            0.48
        }

      ).addTo(map)

      .bindPopup(
        `<b>
          ${esc(
            z.risk_category
          )} RISK
        </b>
        <br>
        Risk:
        ${Number(
          z.risk_score
        ).toFixed(1)}%
        <br>
        Lat:
        ${z.latitude}
        <br>
        Lon:
        ${z.longitude}`
      );
    }
  );


  /* -------------------------------------------------------
     Assessment zone
     ------------------------------------------------------- */

  if (
    overallRisk > 0 &&
    zone
  ) {

    L.geoJSON(
      zone,
      {
        style: {
          color: "#111",
          weight: 3,
          fillOpacity: 0.08
        }
      }
    )

    .addTo(map)

    .bindPopup(
      "High-risk assessment zone"
    );
  }
}


/* =========================================================
   START DASHBOARD
   ========================================================= */

document.addEventListener(
  "DOMContentLoaded",
  loadDashboard
);