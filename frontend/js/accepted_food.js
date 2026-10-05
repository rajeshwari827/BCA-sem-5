document.addEventListener("DOMContentLoaded", async function () {
    const token = localStorage.getItem("token") ||
        localStorage.getItem("session_token") ||
        sessionStorage.getItem("token") ||
        sessionStorage.getItem("session_token");
    const tableBody = document.getElementById("acceptedFoodBody");
    const searchInput = document.getElementById("searchDonation");
    const statusFilter = document.getElementById("statusFilter");
    let donations = [];

    if (!token) {
        alert("Please log in as a receiver to view accepted food.");
        window.location.replace("../login.html");
        return;
    }

    function render() {
        const search = searchInput.value.trim().toLowerCase();
        const status = statusFilter.value.toLowerCase();
        const rows = donations.filter(function (item) {
            const text = [item.donation_id, item.restaurant, item.food_name]
                .join(" ").toLowerCase();
            return (!search || text.includes(search)) &&
                (!status || String(item.status || "").toLowerCase() === status);
        });

        tableBody.replaceChildren();
        if (!rows.length) {
            const row = tableBody.insertRow();
            const cell = row.insertCell();
            cell.colSpan = 7;
            cell.textContent = donations.length
                ? "No accepted food matches these filters."
                : "You have not accepted any donations yet.";
            return;
        }

        rows.forEach(function (item) {
            const row = tableBody.insertRow();
            [item.donation_id, item.restaurant, item.food_name, item.quantity,
                item.pickup_time || "Not scheduled", item.contact, item.status]
                .forEach(function (value, index) {
                    const cell = row.insertCell();
                    if (index === 5 && value) {
                        const link = document.createElement("a");
                        link.href = "tel:" + String(value).replace(/[^\d+]/g, "");
                        link.textContent = value;
                        cell.appendChild(link);
                    } else {
                        cell.textContent = value || "-";
                    }
                });
        });
    }

    try {
        const response = await fetch("/api/receiver/accepted", {
            headers: {
                "Authorization": "Bearer " + token,
                "Accept": "application/json"
            },
            cache: "no-store"
        });
        const contentType = response.headers.get("content-type") || "";
        if (!contentType.includes("application/json")) {
            throw new Error("Restart backend/app.py to load the accepted donations API.");
        }
        const result = await response.json();

        if (response.status === 401 || response.status === 403) {
            ["user_id", "user_role", "token", "session_token"].forEach(function (key) {
                localStorage.removeItem(key);
                sessionStorage.removeItem(key);
            });
            alert("Your receiver session has expired. Please log in again.");
            window.location.replace("../login.html");
            return;
        }
        if (!response.ok || !result.success) {
            throw new Error(result.message || "Unable to load accepted food.");
        }

        donations = result.donations || [];
        render();
        searchInput.addEventListener("input", render);
        statusFilter.addEventListener("change", render);
    } catch (error) {
        console.error("Accepted food error:", error);
        tableBody.replaceChildren();
        const row = tableBody.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 7;
        cell.textContent = "Unable to load accepted food: " + error.message;
    }
});
