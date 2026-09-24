async function loadMap(){
  try {
    const r = await fetch("/api/dashboard");
    const j = await r.json();
    if (!r.ok || !j.success) throw new Error(j.error || "Unable to load map data");
    const d = j.data;

    // India-only map bounds. The system is not intended as a global risk map.
    const INDIA_BOUNDS = [[6.0, 68.0], [37.5, 97.5]];
    const lat = Math.max(6.1, Math.min(37.4, Number(d.environment.latitude)));
    const lon = Math.max(68.1, Math.min(97.4, Number(d.environment.longitude)));

    const map = L.map("map", {
      minZoom: 5,
      maxZoom: 14,
      maxBounds: INDIA_BOUNDS,
      maxBoundsViscosity: 1.0,
      worldCopyJump: false
    }).setView([lat, lon], 9);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution:"© OpenStreetMap contributors",
      noWrap:true
    }).addTo(map);

    const overallRisk = Number(d.risk?.score || 0);
    const visibleZones = overallRisk <= 0 ? [] : (d.zones || []).filter(z =>
      ["MODERATE", "HIGH", "CRITICAL"].includes(z.risk_category)
    );

    // No green cells: LOW/no-risk areas are intentionally not displayed.
    if (visibleZones.length === 0) {
      const status = L.control({position:"topright"});
      status.onAdd = function(){
        const div = L.DomUtil.create("div","map-status");
        div.innerHTML = `<strong>No significant landslide risk</strong><br><span>Current assessment: LOW</span>`;
        return div;
      };
      status.addTo(map);
      map.fitBounds(INDIA_BOUNDS,{padding:[20,20]});
      return;
    }

    const colors={MODERATE:"#e4c441",HIGH:"#e67e22",CRITICAL:"#c0392b"};
    visibleZones.forEach(z=>{
      const c=colors[z.risk_category];
      L.rectangle([[z.latitude-.035,z.longitude-.035],[z.latitude+.035,z.longitude+.035]],
        {color:c,weight:1,fillColor:c,fillOpacity:.48})
        .addTo(map)
        .bindPopup(`<b>${z.risk_category} RISK</b><br>Risk: ${Number(z.risk_score).toFixed(1)}%<br>Lat: ${z.latitude}<br>Lon: ${z.longitude}`);
    });

    if(overallRisk > 0 && d.assessment_zone) {
      L.geoJSON(d.assessment_zone,{style:{color:"#111",weight:3,fillOpacity:.08}})
        .addTo(map).bindPopup("High-risk assessment zone");
    }
  } catch(error) {
    console.error("Map loading failed:",error);
    const el=document.getElementById("map");
    if(el) el.innerHTML=`<div class="map-error">Unable to load the India risk map.<br>${error.message}</div>`;
  }
}
document.addEventListener("DOMContentLoaded",loadMap);
