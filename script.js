// ================= OTP SYSTEM =================
let generatedOTP;

// SEND OTP
function sendOTP() {

    let role = document.getElementById("role").value;
    let userId = document.getElementById("userId").value;
    let password = document.getElementById("password").value;
    let phone = document.getElementById("phone").value;

    if (!role || !userId || !password || !phone) {
        alert("Fill all fields first");
        return;
    }

    generatedOTP = Math.floor(1000 + Math.random() * 9000);

    alert("Your OTP is: " + generatedOTP);
}


// VERIFY OTP
function verifyOTP() {

    let role = document.getElementById("role").value;
    let userId = document.getElementById("userId").value;
    let password = document.getElementById("password").value;
    let enteredOTP = document.getElementById("otp").value;

    if (
        !(
            (role === "police" && userId === "police1" && password === "1234") ||
            (role === "admin" && userId === "admin1" && password === "admin123")
        )
    ) {
        alert("Invalid ID or Password");
        return;
    }

    if (enteredOTP == generatedOTP) {
        alert("Login Successful");
        window.location.href = "dashboard.html";
    } else {
        alert("Invalid OTP");
    }
}


// ================= DASHBOARD DEMO STATS =================
let vehicles = 0;
let violations = 0;

setInterval(() => {

    vehicles = Math.floor(Math.random() * 100);
    violations = Math.floor(Math.random() * 10);

    let veh = document.getElementById("veh");
    let level = document.getElementById("level");
    let vio = document.getElementById("vio");

    if (veh) veh.innerText = vehicles;

    if (level) {
        if (vehicles < 30)
            level.innerText = "LOW";
        else if (vehicles < 70)
            level.innerText = "MEDIUM";
        else
            level.innerText = "HIGH";
    }

    if (vio) vio.innerText = violations;

}, 2000);


// ================= CCTV VIDEO ANALYSIS =================
function analyzeVideo() {

    const file = document.getElementById("videoFile").files[0];

    if (!file) {
        alert("Select a video first");
        return;
    }

    const formData = new FormData();
    formData.append("video", file);

    document.getElementById("status").innerHTML =
        "🚀 Uploading Video...";

    fetch("http://localhost:5000/upload", {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(() => {

        document.getElementById("status").innerHTML =
            "✅ Analysis Running";

        // VIDEO STREAM
        let video = document.getElementById("videoPlayer");

        if (video) {

            video.src =
                "http://localhost:5000/video?" +
                new Date().getTime();

            video.style.display = "block";
        }

        // LIVE ANALYTICS
        setInterval(() => {

            fetch("http://localhost:5000/result")
            .then(res => res.json())
            .then(data => {

                // Violations
                let vio =
                    document.getElementById("vio");

                if (vio)
                    vio.innerText =
                        data.violations || 0;

                let violationCount =
                    document.getElementById("violationCount");

                if (violationCount)
                    violationCount.innerText =
                        data.violations || 0;

                // Vehicles
                let veh =
                    document.getElementById("veh");

                if (veh)
                    veh.innerText =
                        data.vehicle_count || 0;

                // Ambulance
                let ambulance =
                    document.getElementById("ambulance");

                if (ambulance)
                    ambulance.innerText =
                        data.ambulance_alert
                            ? "YES"
                            : "NO";

                // Traffic Density
                let traffic =
                    document.getElementById("trafficLevel");

                if (traffic)
                    traffic.innerText =
                        data.traffic_density || "LOW";

                // Vehicle Density
                let density =
                    document.getElementById("vehicleDensity");

                if (density)
                    density.innerText =
                        data.vehicle_density || "LOW";

            })
            .catch(err => {
                console.log(err);
            });

        }, 2000);

    })
    .catch(error => {

        console.log(error);

        document.getElementById("status").innerHTML =
            "❌ Backend Error - Check Flask Server";

    });
}


// ================= ROAD IMAGE ANALYSIS =================
function openRoad() {

    let input = document.createElement("input");

    input.type = "file";
    input.accept = "image/*";

    input.onchange = function () {

        let file = this.files[0];

        let formData = new FormData();

        formData.append("image", file);

        let box =
            document.getElementById("resultBox");

        if (box) {
            box.innerHTML =
                "<p class='loading'>🔄 Analyzing image...</p>";
        }

        fetch("http://127.0.0.1:5000/analyze-road", {
            method: "POST",
            body: formData
        })
        .then(res => res.json())
        .then(data => {

            let html = "";

            html += "<div class='result-card'>";

            html += "<h3>🛣 Road Analysis Result</h3>";

            html += "<p><b>Risk Level:</b> "
                 + data.level +
                 "</p>";

            html += "<p><b>Score:</b> "
                 + data.edge_score.toFixed(4) +
                 "</p>";

            html += "<h4>Suggestions</h4>";

            data.suggestions.forEach(s => {

                html +=
                    "<div class='suggestion'>• "
                    + s +
                    "</div>";

            });

            html += "</div>";

            if (box)
                box.innerHTML = html;

        })
        .catch(err => {

            console.log(err);

            if (box)
                box.innerHTML =
                    "❌ Error in image analysis";

        });

    };

    input.click();
}