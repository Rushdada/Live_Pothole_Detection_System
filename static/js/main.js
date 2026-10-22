// Main Frontend Application Logic for Pothole Detection & Geolocation System

let map;
let vehicleMarker;
let potholeLayerGroup;
let isSimulationRunning = false;
let severityChartInstance = null;
let statusChartInstance = null;
let lastKnownPotholeId = 0;

// Default initial coordinates (Bangalore City Center / customizable)
const DEFAULT_LAT = 12.971598;
const DEFAULT_LNG = 77.594562;

document.addEventListener("DOMContentLoaded", () => {
    initMap();
    initCharts();
    refreshData();
    pollTelemetry();

    // Attach simulation toggle handler
    document.getElementById("btnToggleSim").addEventListener("click", toggleSimulation);

    // Periodic telemetry loop (every 1000ms)
    setInterval(pollTelemetry, 1000);

    // Periodic full data refresh (every 5000ms)
    setInterval(refreshData, 5000);
});

// ----------------- MAP INITIALIZATION -----------------

function initMap() {
    map = L.map("map").setView([DEFAULT_LAT, DEFAULT_LNG], 15);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
    }).addTo(map);

    potholeLayerGroup = L.layerGroup().addTo(map);

    // Vehicle custom marker icon
    const carIcon = L.divIcon({
        className: "vehicle-marker-wrapper",
        html: '<div class="vehicle-marker"></div>',
        iconSize: [22, 22],
        iconAnchor: [11, 11]
    });

    vehicleMarker = L.marker([DEFAULT_LAT, DEFAULT_LNG], { icon: carIcon }).addTo(map);
    vehicleMarker.bindTooltip("<b>Vehicle Sensor Unit</b><br>Real-time Road Scanner", { direction: "top" });
}

function centerMapOnVehicle() {
    if (vehicleMarker) {
        map.setView(vehicleMarker.getLatLng(), 16);
    }
}

// ----------------- TELEMETRY & SIMULATION -----------------

async function pollTelemetry() {
    try {
        const res = await fetch("/api/simulation/status");
        const json = await res.json();
        if (!json.success) return;

        const t = json.telemetry;
        isSimulationRunning = json.is_running;
        updateSimulationUI(isSimulationRunning);

        // Update Vehicle Marker position
        if (t.latitude && t.longitude && (t.latitude !== 0 || t.longitude !== 0)) {
            const newPos = [t.latitude, t.longitude];
            vehicleMarker.setLatLng(newPos);

            document.getElementById("telemetryCoords").innerText = `${t.latitude.toFixed(6)}° N, ${t.longitude.toFixed(6)}° E`;
            document.getElementById("telemetrySpeed").innerText = `Speed: ${t.speed_kmh.toFixed(1)} km/h`;
        }

        // Update sensor values & gauges
        const effDepth = t.effective_depth_cm || 0.0;
        const vibration = t.vibration_g || 1.0;

        document.getElementById("telemetryDepth").innerHTML = `${effDepth.toFixed(1)} <span class="fs-6 fw-normal text-muted">cm</span>`;
        document.getElementById("telemetryVibration").innerHTML = `${vibration.toFixed(2)} <span class="fs-6 fw-normal text-muted">g</span>`;

        // Progress bar indicators
        const depthPercent = Math.min(100, Math.max(5, (effDepth / 15.0) * 100));
        document.getElementById("depthProgressBar").style.width = `${depthPercent}%`;

        const vibPercent = Math.min(100, Math.max(5, ((vibration - 1.0) / 2.5) * 100));
        document.getElementById("vibProgressBar").style.width = `${vibPercent}%`;

        // Check if a new pothole was just detected
        if (t.last_pothole && t.last_pothole.id && t.last_pothole.id !== lastKnownPotholeId) {
            lastKnownPotholeId = t.last_pothole.id;
            displayLastPothole(t.last_pothole);
            showAlertBanner(
                `🚨 <strong>New Pothole Detected!</strong> ID #${t.last_pothole.id} (${t.last_pothole.severity} Severity) at ${t.last_pothole.latitude.toFixed(5)}, ${t.last_pothole.longitude.toFixed(5)}. Automated email alert dispatched!`,
                t.last_pothole.severity === "HIGH" ? "danger" : "warning"
            );
            refreshData();
        }
    } catch (err) {
        console.error("Telemetry poll failed:", err);
    }
}

function updateSimulationUI(running) {
    const btn = document.getElementById("btnToggleSim");
    const text = document.getElementById("simBtnText");
    const badge = document.getElementById("hardwareStatusBadge");

    if (running) {
        btn.classList.remove("btn-outline-light");
        btn.classList.add("btn-warning");
        text.innerText = "Pause Simulation";
        badge.className = "badge bg-warning-soft text-warning";
        badge.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Driving Active';
    } else {
        btn.classList.remove("btn-warning");
        btn.classList.add("btn-outline-light");
        text.innerText = "Start Vehicle Drive";
        badge.className = "badge bg-success-soft text-success";
        badge.innerHTML = '<i class="fa-solid fa-circle fa-2xs"></i> Ready';
    }
}

async function toggleSimulation() {
    const endpoint = isSimulationRunning ? "/api/simulation/stop" : "/api/simulation/start";
    try {
        await fetch(endpoint, { method: "POST" });
        isSimulationRunning = !isSimulationRunning;
        updateSimulationUI(isSimulationRunning);
    } catch (err) {
        console.error("Simulation toggle error:", err);
    }
}

async function triggerPothole(severity) {
    try {
        showAlertBanner(`Triggering simulated ${severity} pothole event...`, "info");
        const res = await fetch("/api/simulation/trigger", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ severity })
        });
        const data = await res.json();
        if (data.success && data.pothole) {
            lastKnownPotholeId = data.pothole.id;
            displayLastPothole(data.pothole);
            showAlertBanner(
                `✅ <strong>${severity} Pothole Injected!</strong> Email alert sent to authority. Recorded at ${data.pothole.latitude}, ${data.pothole.longitude}.`,
                severity === "HIGH" ? "danger" : "warning"
            );
            refreshData();
        }
    } catch (err) {
        console.error("Trigger pothole error:", err);
    }
}

function displayLastPothole(p) {
    document.getElementById("lastDetectionTime").innerText = p.timestamp ? p.timestamp.split(" ")[1] : "Just now";
    const badgeClass = p.severity === "HIGH" ? "bg-danger" : (p.severity === "MEDIUM" ? "bg-warning text-dark" : "bg-success");

    document.getElementById("lastDetectionDetails").innerHTML = `
        <div class="d-flex justify-content-between align-items-center mb-1">
            <span class="fw-bold">Incident #${p.id}</span>
            <span class="badge ${badgeClass}">${p.severity}</span>
        </div>
        <div class="text-dark small mb-1">${p.address || "Road Sector"}</div>
        <div class="d-flex justify-content-between text-muted small">
            <span>Depth: <strong>${p.depth_cm} cm</strong></span>
            <span>Vibration: <strong>${p.vibration_g} g</strong></span>
        </div>
        <div class="mt-2 text-center">
            <a href="https://www.google.com/maps?q=${p.latitude},${p.longitude}" target="_blank" class="btn btn-outline-primary btn-sm py-0 w-100" style="font-size: 11px;">
                <i class="fa-solid fa-map-pin"></i> View in Google Maps
            </a>
        </div>
    `;
}

// ----------------- DATA FETCHING & RENDERING -----------------

async function refreshData() {
    await Promise.all([fetchStats(), fetchPotholes()]);
}

async function fetchStats() {
    try {
        const res = await fetch("/api/stats");
        const json = await res.json();
        if (!json.success) return;

        const s = json.stats;
        document.getElementById("statTotal").innerText = s.total;
        document.getElementById("statHigh").innerText = s.high_severity;
        document.getElementById("statMedium").innerText = s.medium_severity;
        document.getElementById("statLow").innerText = s.low_severity;
        document.getElementById("statEmails").innerText = s.emails_sent;
        document.getElementById("statRepaired").innerText = `${s.repaired} / ${s.total}`;

        updateCharts(s);
    } catch (err) {
        console.error("Fetch stats error:", err);
    }
}

async function fetchPotholes() {
    try {
        const severity = document.getElementById("filterSeverity").value;
        const status = document.getElementById("filterStatus").value;

        let url = "/api/potholes?";
        if (severity) url += `severity=${severity}&`;
        if (status) url += `status=${status}&`;

        const res = await fetch(url);
        const json = await res.json();
        if (!json.success) return;

        renderTable(json.data);
        renderMapMarkers(json.data);
    } catch (err) {
        console.error("Fetch potholes error:", err);
    }
}

function renderTable(potholes) {
    const tbody = document.getElementById("potholeTableBody");
    if (!potholes || potholes.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="10" class="text-center py-4 text-muted">
                    <i class="fa-solid fa-circle-check text-success fa-2x mb-2 d-block"></i>
                    No potholes recorded matching the current filter.
                </td>
            </tr>
        `;
        return;
    }

    let html = "";
    potholes.forEach(p => {
        const severityBadge = p.severity === "HIGH"
            ? '<span class="badge bg-danger">HIGH</span>'
            : (p.severity === "MEDIUM" ? '<span class="badge bg-warning text-dark">MEDIUM</span>' : '<span class="badge bg-success">LOW</span>');

        const statusBadge = p.status === "Repaired"
            ? '<span class="badge bg-success-soft text-success border border-success"><i class="fa-solid fa-check me-1"></i>Repaired</span>'
            : (p.status === "In Progress"
                ? '<span class="badge bg-info-soft text-info border border-info"><i class="fa-solid fa-person-digging me-1"></i>In Progress</span>'
                : '<span class="badge bg-danger-soft text-danger border border-danger"><i class="fa-solid fa-clock me-1"></i>Pending</span>');

        const emailBadge = p.email_sent === 1
            ? '<span class="text-success small fw-semibold"><i class="fa-solid fa-envelope-circle-check"></i> Sent</span>'
            : '<span class="text-muted small"><i class="fa-solid fa-envelope"></i> Not sent</span>';

        html += `
            <tr>
                <td class="fw-bold">#${p.id}</td>
                <td class="small text-muted">${p.timestamp}</td>
                <td>${severityBadge}</td>
                <td>
                    <span class="font-monospace small">${p.latitude.toFixed(5)}, ${p.longitude.toFixed(5)}</span>
                </td>
                <td class="small" style="max-width: 180px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${p.address}">
                    ${p.address || "Road Sector"}
                </td>
                <td class="fw-semibold">${p.depth_cm} cm</td>
                <td class="fw-semibold">${p.vibration_g} g</td>
                <td>
                    <div class="dropdown">
                        <button class="btn btn-sm btn-link text-decoration-none p-0 dropdown-toggle" type="button" data-bs-toggle="dropdown">
                            ${statusBadge}
                        </button>
                        <ul class="dropdown-menu shadow-sm">
                            <li><a class="dropdown-item small" href="javascript:void(0)" onclick="updateStatus(${p.id}, 'Pending')">Mark Pending</a></li>
                            <li><a class="dropdown-item small" href="javascript:void(0)" onclick="updateStatus(${p.id}, 'In Progress')">Mark In Progress</a></li>
                            <li><a class="dropdown-item small" href="javascript:void(0)" onclick="updateStatus(${p.id}, 'Repaired')">Mark Repaired</a></li>
                        </ul>
                    </div>
                </td>
                <td>${emailBadge}</td>
                <td>
                    <div class="d-flex gap-1">
                        <a href="https://www.google.com/maps?q=${p.latitude},${p.longitude}" target="_blank" class="btn btn-outline-primary btn-sm py-0 px-1" title="Open Google Maps">
                            <i class="fa-solid fa-location-arrow"></i>
                        </a>
                        <button class="btn btn-outline-secondary btn-sm py-0 px-1" onclick="focusOnMap(${p.latitude}, ${p.longitude})" title="Focus on Map">
                            <i class="fa-solid fa-eye"></i>
                        </button>
                        <button class="btn btn-outline-info btn-sm py-0 px-1" onclick="resendEmail(${p.id})" title="Resend Email Alert">
                            <i class="fa-solid fa-paper-plane"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
}

function renderMapMarkers(potholes) {
    potholeLayerGroup.clearLayers();

    potholes.forEach(p => {
        let pinClass = "pothole-pin-medium";
        if (p.severity === "HIGH") pinClass = "pothole-pin-high";
        else if (p.severity === "LOW") pinClass = "pothole-pin-low";

        const icon = L.divIcon({
            className: "pothole-marker-div",
            html: `<div class="${pinClass}"></div>`,
            iconSize: [16, 16],
            iconAnchor: [8, 8]
        });

        const marker = L.marker([p.latitude, p.longitude], { icon: icon });

        const popupContent = `
            <div style="min-width: 200px;">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <strong>Pothole #${p.id}</strong>
                    <span class="badge ${p.severity === 'HIGH' ? 'bg-danger' : (p.severity === 'MEDIUM' ? 'bg-warning text-dark' : 'bg-success')}">${p.severity}</span>
                </div>
                <div style="font-size: 11px; color: #64748b; margin-bottom: 6px;">${p.timestamp}</div>
                <div style="font-size: 12px; margin-bottom: 6px;"><strong>Location:</strong> ${p.address || 'Road Sector'}</div>
                <div style="font-size: 12px; margin-bottom: 6px;">
                    <strong>Depth:</strong> ${p.depth_cm} cm | <strong>Impact:</strong> ${p.vibration_g} g
                </div>
                <div style="font-size: 12px; margin-bottom: 10px;">
                    <strong>Status:</strong> ${p.status}
                </div>
                <div class="d-flex gap-1">
                    <a href="https://www.google.com/maps?q=${p.latitude},${p.longitude}" target="_blank" class="btn btn-primary btn-sm w-100 py-1" style="font-size: 11px;">
                        <i class="fa-solid fa-location-arrow"></i> Google Maps
                    </a>
                    <button class="btn btn-outline-info btn-sm py-1" onclick="resendEmail(${p.id})" title="Send Alert">
                        <i class="fa-solid fa-envelope"></i>
                    </button>
                </div>
            </div>
        `;

        marker.bindPopup(popupContent);
        potholeLayerGroup.addLayer(marker);
    });
}

function focusOnMap(lat, lng) {
    map.setView([lat, lng], 17);
}

// ----------------- STATUS & EMAIL ACTIONS -----------------

async function updateStatus(potholeId, newStatus) {
    try {
        const res = await fetch(`/api/potholes/${potholeId}/status`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: newStatus })
        });
        const json = await res.json();
        if (json.success) {
            showAlertBanner(`Pothole #${potholeId} status marked as <strong>${newStatus}</strong>.`, "success");
            refreshData();
        }
    } catch (err) {
        console.error("Status update error:", err);
    }
}

async function resendEmail(potholeId) {
    try {
        showAlertBanner(`Dispatching email alert for Pothole #${potholeId}...`, "info");
        const res = await fetch(`/api/potholes/${potholeId}/email`, { method: "POST" });
        const json = await res.json();
        if (json.success) {
            showAlertBanner(`✅ ${json.message}`, "success");
            refreshData();
        } else {
            showAlertBanner(`Email error: ${json.message || "Failed to send"}`, "danger");
        }
    } catch (err) {
        console.error("Email send error:", err);
    }
}

async function clearAllData() {
    if (!confirm("Are you sure you want to clear all detected pothole records for this demonstration?")) {
        return;
    }
    try {
        await fetch("/api/potholes/clear", { method: "POST" });
        showAlertBanner("All pothole incident records have been cleared.", "secondary");
        refreshData();
    } catch (err) {
        console.error("Clear data error:", err);
    }
}

// ----------------- CHARTS INITIALIZATION -----------------

function initCharts() {
    const ctxSev = document.getElementById("severityChart").getContext("2d");
    severityChartInstance = new Chart(ctxSev, {
        type: "doughnut",
        data: {
            labels: ["High", "Medium", "Low"],
            datasets: [{
                data: [0, 0, 0],
                backgroundColor: ["#dc2626", "#ea580c", "#16a34a"],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            cutout: "65%"
        }
    });

    const ctxStat = document.getElementById("statusChart").getContext("2d");
    statusChartInstance = new Chart(ctxStat, {
        type: "bar",
        data: {
            labels: ["Pending", "In Prog.", "Repaired"],
            datasets: [{
                data: [0, 0, 0],
                backgroundColor: ["#ef4444", "#3b82f6", "#22c55e"],
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { font: { size: 9 } } },
                y: { display: false, beginAtZero: true }
            }
        }
    });
}

function updateCharts(stats) {
    if (severityChartInstance) {
        severityChartInstance.data.datasets[0].data = [
            stats.high_severity || 0,
            stats.medium_severity || 0,
            stats.low_severity || 0
        ];
        severityChartInstance.update();
    }

    if (statusChartInstance) {
        statusChartInstance.data.datasets[0].data = [
            stats.pending || 0,
            stats.in_progress || 0,
            stats.repaired || 0
        ];
        statusChartInstance.update();
    }
}

// ----------------- MODALS & SETTINGS -----------------

async function loadConfig() {
    try {
        const res = await fetch("/api/config");
        const json = await res.json();
        if (!json.success) return;

        const c = json.config;
        document.getElementById("cfgRecipientEmail").value = c.recipient_email;
        document.getElementById("cfgSenderEmail").value = c.sender_email;
        document.getElementById("cfgSerialPort").value = `${c.serial_port} (${c.serial_baud} baud)`;

        const badge = document.getElementById("cfgLiveEmailBadge");
        if (c.live_email_enabled) {
            badge.innerHTML = '<span class="badge bg-success">Live SMTP Enabled</span>';
        } else {
            badge.innerHTML = '<span class="badge bg-secondary">Simulated Outbox Mode (Testing)</span>';
        }
    } catch (err) {
        console.error("Config fetch error:", err);
    }
}

async function loadOutboxList() {
    try {
        const res = await fetch("/api/outbox");
        const json = await res.json();
        const listContainer = document.getElementById("outboxList");

        if (!json.success || !json.emails || json.emails.length === 0) {
            listContainer.innerHTML = `
                <div class="text-center py-4 text-muted">
                    <i class="fa-solid fa-inbox fa-2x mb-2 d-block"></i>
                    No archived emails in outbox yet.<br>
                    Trigger a pothole detection to generate an email alert!
                </div>
            `;
            return;
        }

        let html = "";
        json.emails.forEach(file => {
            html += `
                <a href="/outbox/${file}" target="_blank" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                    <div>
                        <div class="fw-bold text-dark"><i class="fa-solid fa-envelope text-primary me-2"></i>${file}</div>
                        <small class="text-muted">Click to view formatted HTML alert as received by authority</small>
                    </div>
                    <span class="btn btn-outline-primary btn-sm py-0"><i class="fa-solid fa-arrow-up-right-from-square"></i> Open</span>
                </a>
            `;
        });
        listContainer.innerHTML = html;
    } catch (err) {
        console.error("Outbox fetch error:", err);
    }
}

async function loadQRCode() {
    try {
        const res = await fetch("/api/server_info");
        const json = await res.json();
        if (json.success) {
            document.getElementById("qrCodeImg").src = `data:image/png;base64,${json.qr_code_b64}`;
            document.getElementById("mobileAppUrl").innerText = json.mobile_url;
        }
    } catch (e) {
        console.error("QR Code fetch error:", e);
    }
}

// ----------------- UI NOTIFICATIONS -----------------

function showAlertBanner(msg, type = "info") {
    const banner = document.getElementById("alertBanner");
    const text = document.getElementById("alertBannerText");

    banner.className = `alert alert-${type} alert-dismissible fade show`;
    text.innerHTML = msg;
    banner.classList.remove("d-none");

    setTimeout(() => {
        hideAlertBanner();
    }, 6000);
}

function hideAlertBanner() {
    const banner = document.getElementById("alertBanner");
    banner.classList.add("d-none");
}

