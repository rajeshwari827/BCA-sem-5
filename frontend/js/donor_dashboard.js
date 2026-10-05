document.addEventListener("DOMContentLoaded", async function () {

    // Keep the session available if a previous page saved it in
    // sessionStorage instead of localStorage.
    const donorId = localStorage.getItem("user_id") || sessionStorage.getItem("user_id");
    const token = localStorage.getItem("token") ||
        localStorage.getItem("session_token") ||
        sessionStorage.getItem("token") ||
        sessionStorage.getItem("session_token");

    if (donorId) localStorage.setItem("user_id", donorId);
    if (token) {
        localStorage.setItem("token", token);
        localStorage.setItem("session_token", token);
    }

    if (!donorId || !token) {
        alert("Please login first.");
        window.location.replace("../login.html");
        return;
    }

    if (!donorId.toUpperCase().startsWith("DN")) {
        alert("Invalid donor login.");
        window.location.replace("../login.html");
        return;
    }

    try {
        const response = await fetch("/api/donor/dashboard", {
            method: "GET",
            headers: {
                "Authorization": "Bearer " + token,
                "Accept": "application/json"
            },
            cache: "no-store"
        });

        const result = await response.json();

        const authError = /please log in again/i.test(result.message || "");
        if (response.status === 401 || authError) {
            localStorage.removeItem("user_id");
            localStorage.removeItem("user_role");
            localStorage.removeItem("token");
            localStorage.removeItem("session_token");
            sessionStorage.removeItem("user_id");
            sessionStorage.removeItem("user_role");
            sessionStorage.removeItem("token");
            sessionStorage.removeItem("session_token");
            alert("Your login session has expired or the server was restarted. Please log in again.");
            window.location.replace("../login.html");
            return;
        }

        if (!response.ok || !result.success) {
            alert("Unable to load dashboard:\n" + (result.message || "Unknown server error."));
            return;
        }

        document.getElementById("welcomeMessage").textContent =
            "Welcome, " + (result.donor?.resturaent_name || "Donor");

        document.getElementById("totalDonations").textContent = result.stats?.total ?? 0;
        document.getElementById("todayDonations").textContent = result.stats?.today ?? 0;
        document.getElementById("acceptedDonations").textContent = result.stats?.accepted ?? 0;
        document.getElementById("pendingDonations").textContent = result.stats?.pending ?? 0;

        const tableBody = document.getElementById("donationTableBody");
        tableBody.innerHTML = "";

        if (!result.donations || result.donations.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="4">No donations yet.</td></tr>';
        } else {
            result.donations.forEach(function (donation) {
                const row = document.createElement("tr");
                const status = donation.status || "Pending";
                let statusClass = status.toLowerCase();
                let donationDate = "-";

                if (donation.created_at) {
                    donationDate = new Date(donation.created_at).toLocaleDateString("en-IN", {
                        day: "2-digit", month: "short", year: "numeric"
                    });
                }

                row.innerHTML = `
                    <td>${donation.food_name || "-"}</td>
                    <td>${donation.quantity || "-"}</td>
                    <td>${donationDate}</td>
                    <td class="${statusClass}">${status}</td>
                `;
                tableBody.appendChild(row);
            });
        }
    } catch (error) {
        console.error("Dashboard Error:", error);
        alert("Cannot connect to the server.\n\nPlease make sure app.py is running.");
    }

    const logoutBtn = document.getElementById("logoutBtn");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", async function (e) {
            e.preventDefault();
            const currentToken = localStorage.getItem("token");
            try {
                if (currentToken) {
                    await fetch("/api/logout", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "Authorization": "Bearer " + currentToken
                        },
                        body: "{}",
                        keepalive: true
                    });
                }
            } catch (error) {
                console.error("Logout Error:", error);
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
