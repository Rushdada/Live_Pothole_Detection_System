// Mobile Application Controller for PotholeCam AI

let videoStream = null;
let isScanning = false;
let scanTimer = null;
let currentFacingMode = "environment"; // default to rear camera for road
let currentLat = 12.971598;
let currentLng = 77.594562;
let currentSpeed = 36.0;
let currentAccuracy = 5.0;
let sensitivity = 0.5;
let detectedCount = 0;
let emailsCount = 0;
let isProcessingFrame = false;
let recipientEmail = "rushipapu456@gmail.com";

document.addEventListener("DOMContentLoaded", () => {
    initGPS();
    loadRecentCaptures();
    fetchConfig();
});

// ----------------- CONFIG & GPS -----------------

async function fetchConfig() {
    try {
        const res = await fetch("/api/server_info");
        const json = await res.json();
        if (json.success && json.recipient_email) {
            recipientEmail = json.recipient_email;
            const el = document.getElementById("displayRecipient");
            if (el) el.innerText = recipientEmail;
        }
    } catch (e) {
        console.warn("Could not fetch server info:", e);
    }
}

function initGPS() {
    const gpsPill = document.getElementById("gpsPill");
    const coordsDisplay = document.getElementById("mobileLatLong");
    const accDisplay = document.getElementById("gpsAccuracy");
    const hudCoords = document.getElementById("hudCoords");

    if ("geolocation" in navigator) {
        navigator.geolocation.watchPosition(
            (pos) => {
                currentLat = pos.coords.latitude;
                currentLng = pos.coords.longitude;
                currentAccuracy = pos.coords.accuracy || 4.0;
                currentSpeed = pos.coords.speed ? (pos.coords.speed * 3.6) : 38.0;

                gpsPill.className = "badge bg-success";
                gpsPill.innerHTML = '<i class="fa-solid fa-location-dot"></i> GPS: Locked';

                coordsDisplay.innerText = `${currentLat.toFixed(5)}° N, ${currentLng.toFixed(5)}° E`;
                accDisplay.innerText = `Accuracy: ±${currentAccuracy.toFixed(1)}m | Speed: ${currentSpeed.toFixed(0)}km/h`;
                if (hudCoords) {
                    hudCoords.innerText = `${currentLat.toFixed(4)}, ${currentLng.toFixed(4)}`;
                }
            },
            (err) => {
                console.warn("Real GPS unavailable, using simulated coordinates:", err.message);
                gpsPill.className = "badge bg-warning text-dark";
                gpsPill.innerHTML = '<i class="fa-solid fa-satellite-dish"></i> GPS: Simulated';
                coordsDisplay.innerText = `${currentLat.toFixed(5)}° N, ${currentLng.toFixed(5)}° E (Sim)`;
                accDisplay.innerText = "Simulated Road Route Coordinates";
            },
            { enableHighAccuracy: true, maximumAge: 2000, timeout: 5000 }
        );
    }
}

// ----------------- CAMERA CONTROLS -----------------

async function startCamera() {
    const video = document.getElementById("cameraVideo");
    const placeholder = document.getElementById("cameraPlaceholder");
    const hud = document.getElementById("cameraHUD");
    const mainBtnText = document.getElementById("mainActionText");
    const mainBtn = document.getElementById("btnMainAction");

    try {
        if (videoStream) {
            videoStream.getTracks().forEach(track => track.stop());
        }

        const constraints = {
            audio: false,
            video: {
                facingMode: { ideal: currentFacingMode },
                width: { ideal: 1280 },
                height: { ideal: 720 }
            }
        };

        videoStream = await navigator.mediaDevices.getUserMedia(constraints);
        video.srcObject = videoStream;
        await video.play();

        placeholder.classList.add("d-none");
        hud.classList.remove("d-none");

        isScanning = true;
        mainBtnText.innerText = "Pause Scanner";
        mainBtn.classList.remove("btn-primary");
        mainBtn.classList.add("btn-warning");

        // Start scanning frames
        startScanLoop();

    } catch (err) {
        console.error("Camera access error:", err);
        alert(`Camera Access Error: ${err.message}. Please allow camera permissions.`);
    }
}

function stopCamera() {
    stopScanLoop();
    if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
        videoStream = null;
    }
    const placeholder = document.getElementById("cameraPlaceholder");
    const hud = document.getElementById("cameraHUD");
    const mainBtnText = document.getElementById("mainActionText");
    const mainBtn = document.getElementById("btnMainAction");

    placeholder.classList.remove("d-none");
    hud.classList.add("d-none");

    isScanning = false;
    mainBtnText.innerText = "Start Scanner";
    mainBtn.classList.remove("btn-warning");
    mainBtn.classList.add("btn-primary");
}

function toggleCameraScanning() {
    if (isScanning) {
        stopCamera();
    } else {
        startCamera();
    }
}

async function switchCamera() {
    currentFacingMode = currentFacingMode === "environment" ? "user" : "environment";
    if (isScanning) {
        await startCamera();
    }
}

// ----------------- LIVE SCANNING & AI DETECTION -----------------

function startScanLoop() {
    if (scanTimer) clearInterval(scanTimer);
    // Scan every 1800ms
    scanTimer = setInterval(() => {
        if (isScanning && !isProcessingFrame) {
            captureAndDetect(false);
        }
    }, 1800);
}

function stopScanLoop() {
    if (scanTimer) {
        clearInterval(scanTimer);
        scanTimer = null;
    }
}

async function captureAndDetect(force = false) {
    const video = document.getElementById("cameraVideo");
    if (!videoStream || video.readyState < 2) {
        if (force) {
            // If camera not yet opened, start camera first
            await startCamera();
            setTimeout(() => captureAndDetect(true), 600);
        }
        return;
    }

    isProcessingFrame = true;
    const hudStatus = document.getElementById("hudStatus");
    if (hudStatus) hudStatus.innerText = "Analyzing road surface with AI...";

    try {
        const canvas = document.getElementById("captureCanvas");
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;

        const ctx = canvas.getContext("2d");
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        const b64Image = canvas.toDataURL("image/jpeg", 0.85);

        // Send to backend OpenCV detection endpoint
        const res = await fetch("/api/detect_camera_frame", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                image: b64Image,
                latitude: currentLat,
                longitude: currentLng,
                speed_kmh: currentSpeed,
                sensitivity: sensitivity,
                force_detect: force,
                recipient: recipientEmail
            })
        });

        const data = await res.json();

        if (data.success && data.detected) {
            handleDetectionSuccess(data);
        } else {
            if (hudStatus) hudStatus.innerText = "Road clear. Monitoring...";
            clearOverlayCanvas();
        }

    } catch (err) {
        console.error("Frame detection error:", err);
        if (hudStatus) hudStatus.innerText = "Scan error. Retrying...";
    } finally {
        isProcessingFrame = false;
    }
}

function handleDetectionSuccess(data) {
    const p = data.pothole;
    detectedCount++;
    emailsCount++;

    document.getElementById("mobileDetectedCount").innerText = detectedCount;
    document.getElementById("mobileEmailsCount").innerText = `${emailsCount} Emails Dispatched`;

    // Audio & Haptic Feedback
    playWarningBeep();
    if ("vibrate" in navigator) {
        navigator.vibrate([200, 100, 200]);
    }

    // Draw Bounding Box on overlay canvas
    if (data.bbox) {
        drawBoundingBox(data.bbox, p.severity);
    }

    // Show Notification Toast
    showPotholeToast(
        `🚨 ${p.severity} POTHOLE DETECTED!`,
        `Depth: ${p.depth_cm}cm. Email alert sent to <strong>${recipientEmail}</strong>`
    );

    // Refresh Recent Captures feed
    loadRecentCaptures();
}

function drawBoundingBox(bbox, severity) {
    const video = document.getElementById("cameraVideo");
    const overlay = document.getElementById("overlayCanvas");

    overlay.width = video.clientWidth;
    overlay.height = video.clientHeight;

    const ctx = overlay.getContext("2d");
    ctx.clearRect(0, 0, overlay.width, overlay.height);

    // Scale factors between video stream and displayed element
    const scaleX = overlay.width / (video.videoWidth || overlay.width);
    const scaleY = overlay.height / (video.videoHeight || overlay.height);

    const x = bbox.x * scaleX;
    const y = bbox.y * scaleY;
    const w = bbox.width * scaleX;
    const h = bbox.height * scaleY;

    // Draw box
    ctx.strokeStyle = severity === "HIGH" ? "#dc2626" : (severity === "MEDIUM" ? "#ea580c" : "#16a34a");
    ctx.lineWidth = 3;
    ctx.strokeRect(x, y, w, h);

    // Draw Label
    ctx.fillStyle = ctx.strokeStyle;
    ctx.fillRect(x, Math.max(0, y - 24), Math.min(180, w + 20), 24);
    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 12px sans-serif";
    ctx.fillText(`⚠️ POTHOLE: ${severity}`, x + 6, Math.max(16, y - 8));

    // Clear box after 2.5s
    setTimeout(clearOverlayCanvas, 2500);
}

function clearOverlayCanvas() {
    const overlay = document.getElementById("overlayCanvas");
    if (overlay) {
        const ctx = overlay.getContext("2d");
        ctx.clearRect(0, 0, overlay.width, overlay.height);
    }
}

// ----------------- RECENT CAPTURES FEED -----------------

async function loadRecentCaptures() {
    const list = document.getElementById("capturesList");
    try {
        const res = await fetch("/api/potholes?limit=5");
        const json = await res.json();

        if (!json.success || !json.data || json.data.length === 0) {
            return;
        }

        let html = "";
        json.data.forEach(p => {
            const badgeClass = p.severity === "HIGH" ? "bg-danger" : (p.severity === "MEDIUM" ? "bg-warning text-dark" : "bg-success");
            const imgHtml = p.image_path
                ? `<img src="/snapshots/${p.image_path.split('\\').pop().split('/').pop()}" class="capture-img" alt="Pothole Photo">`
                : `<div class="p-3 text-center bg-light text-muted small"><i class="fa-solid fa-camera me-1"></i> Sensor Record</div>`;

            html += `
                <div class="capture-card shadow-sm">
                    ${imgHtml}
                    <div class="p-2">
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <span class="fw-bold">Incident #${p.id}</span>
                            <span class="badge ${badgeClass}">${p.severity}</span>
                        </div>
                        <div class="small text-muted mb-2">${p.timestamp}</div>
                        <div class="d-flex justify-content-between text-dark small mb-2">
                            <span>Depth: <strong>${p.depth_cm} cm</strong></span>
                            <span>Speed: <strong>${p.speed_kmh} km/h</strong></span>
                        </div>
                        <div class="d-flex gap-1">
                            <a href="${p.map_url}" target="_blank" class="btn btn-outline-primary btn-sm flex-grow-1 rounded-pill py-1" style="font-size: 11px;">
                                <i class="fa-solid fa-map-location-dot"></i> Google Maps
                            </a>
                            <button class="btn btn-outline-info btn-sm rounded-pill py-1 px-3" onclick="resendEmail(${p.id})" title="Send Alert">
                                <i class="fa-solid fa-paper-plane"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });

        list.innerHTML = html;

    } catch (err) {
        console.error("Load recent captures error:", err);
    }
}

async function resendEmail(id) {
    try {
        showPotholeToast("Sending Email...", `Dispatching alert to ${recipientEmail}`);
        const res = await fetch(`/api/potholes/${id}/email`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ recipient: recipientEmail })
        });
        const data = await res.json();
        showPotholeToast(data.success ? "Email Dispatched!" : "Email Notice", data.message);
    } catch (e) {
        console.error(e);
    }
}

async function sendTestEmail() {
    showPotholeToast("Sending Test Alert...", `Target: ${recipientEmail}`);
    try {
        const res = await fetch("/api/simulation/trigger", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ severity: "HIGH", latitude: currentLat, longitude: currentLng })
        });
        const json = await res.json();
        if (json.success && json.pothole) {
            handleDetectionSuccess({ pothole: json.pothole });
        }
    } catch (err) {
        console.error("Test email error:", err);
    }
}

function updateSensitivity(val) {
    sensitivity = parseFloat(val);
    const label = val >= 0.7 ? "High" : (val <= 0.3 ? "Low" : "Medium");
    document.getElementById("sensitivityVal").innerText = `${label} (${val})`;
}

// ----------------- NOTIFICATIONS & AUDIO -----------------

function showPotholeToast(title, msg) {
    const toast = document.getElementById("potholeToast");
    document.getElementById("toastTitle").innerText = title;
    document.getElementById("toastMessage").innerHTML = msg;
    toast.classList.remove("d-none");

    setTimeout(hidePotholeToast, 5000);
}

function hidePotholeToast() {
    const toast = document.getElementById("potholeToast");
    if (toast) toast.classList.add("d-none");
}

function playWarningBeep() {
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();

        osc.type = "sine";
        osc.frequency.setValueAtTime(880, audioCtx.currentTime); // 880 Hz (A5)
        osc.frequency.exponentialRampToValueAtTime(440, audioCtx.currentTime + 0.25);

        gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
        gain.gain.linearRampToValueAtTime(0.01, audioCtx.currentTime + 0.25);

        osc.connect(gain);
        gain.connect(audioCtx.destination);

        osc.start();
        osc.stop(audioCtx.currentTime + 0.25);
    } catch (e) {
        // AudioContext may be blocked before first user gesture
    }
}

