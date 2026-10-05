document.addEventListener("DOMContentLoaded", async function () {
    const receiverId = localStorage.getItem("user_id") || sessionStorage.getItem("user_id");
    const token = localStorage.getItem("token") ||
        localStorage.getItem("session_token") ||
        sessionStorage.getItem("token") ||
        sessionStorage.getItem("session_token");

    if (receiverId) localStorage.setItem("user_id", receiverId);
    if (token) localStorage.setItem("token", token);

    if (!receiverId || !receiverId.toUpperCase().startsWith("RN") || !token) {
        window.location.replace("../login.html");
        return;
    }

    try {
        const response = await fetch("/api/receiver/dashboard", {
            headers: {
                "Authorization": "Bearer " + token,
                "Accept": "application/json"
            },
            cache: "no-store"
        });
        const result = await response.json();

        if (response.status === 401 || response.status === 403) {
            localStorage.removeItem("user_id");
            localStorage.removeItem("user_role");
            localStorage.removeItem("token");
            localStorage.removeItem("session_token");
            sessionStorage.removeItem("user_id");
            sessionStorage.removeItem("user_role");
            sessionStorage.removeItem("token");
            sessionStorage.removeItem("session_token");
            alert("Your receiver session has expired. Please log in again.");
            window.location.replace("../login.html");
            return;
        }

        if (!response.ok || !result.success) {
            throw new Error(result.message || "Unable to load receiver dashboard.");
        }

        document.getElementById("welcomeMessage").textContent =
            "Welcome, " + (result.receiver?.organization_name || "Receiver");
        document.getElementById("availableDonations").textContent = result.stats?.available ?? 0;
        document.getElementById("acceptedDonations").textContent = result.stats?.accepted ?? 0;
        document.getElementById("todayPickups").textContent = result.stats?.today_pickups ?? 0;
        document.getElementById("completedDonations").textContent = result.stats?.completed ?? 0;

        const body = document.getElementById("donationTableBody");
        body.replaceChildren();
        if (!result.donations?.length) {
            const row = body.insertRow();
            const cell = row.insertCell();
            cell.colSpan = 5;
            cell.textContent = "No available donations right now.";
        } else {
            result.donations.forEach(function (donation) {
                const row = body.insertRow();
                [donation.restaurant, donation.food_name, donation.quantity, donation.city, donation.status]
                    .forEach(function (value) {
                        row.insertCell().textContent = value || "-";
                    });
            });
        }
    } catch (error) {
        console.error("Receiver dashboard error:", error);
        alert("Unable to load receiver dashboard: " + error.message);
    }

    const logoutBtn = document.getElementById("logoutBtn");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", async function (event) {
            event.preventDefault();
            try {
                await fetch("/api/logout", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + token
                    },
                    body: "{}",
                    keepalive: true
                });
            } catch (error) {
                console.error("Receiver logout error:", error);
            }
            localStorage.removeItem("user_id");
            localStorage.removeItem("user_role");
            localStorage.removeItem("token");
            localStorage.removeItem("session_token");
            sessionStorage.removeItem("user_id");
            sessionStorage.removeItem("user_role");
            sessionStorage.removeItem("token");
            sessionStorage.removeItem("session_token");
            window.location.replace("../login.html");
        });
    }
});
