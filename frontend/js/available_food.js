document.addEventListener("DOMContentLoaded", async function () {
    const receiverId = localStorage.getItem("user_id") || sessionStorage.getItem("user_id");
    const token = localStorage.getItem("token") ||
        localStorage.getItem("session_token") ||
        sessionStorage.getItem("token") ||
        sessionStorage.getItem("session_token");

    if (!receiverId || !receiverId.toUpperCase().startsWith("RN") || !token) {
        alert("Please log in as a receiver to view available food.");
        window.location.replace("../login.html");
        return;
    }

    const tableBody = document.getElementById("availableFoodBody");
    const searchInput = document.getElementById("searchFood");
    const categoryFilter = document.getElementById("categoryFilter");
    const cityFilter = document.getElementById("cityFilter");
    let donations = [];

    function formatDate(value) {
        if (!value) return "-";
        const date = new Date(value);
        return Number.isNaN(date.getTime()) ? String(value) :
            date.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
    }

    function renderDonations() {
        const search = searchInput.value.trim().toLowerCase();
        const category = categoryFilter.value.toLowerCase();
        const city = cityFilter.value.toLowerCase();
        const filtered = donations.filter(function (item) {
            const searchable = [item.restaurant, item.food_name, item.food_category, item.city]
                .join(" ").toLowerCase();
            return (!search || searchable.includes(search)) &&
                (!category || String(item.food_category || "").toLowerCase() === category) &&
                (!city || String(item.city || "").toLowerCase() === city);
        });

        tableBody.replaceChildren();
        if (!filtered.length) {
            const row = tableBody.insertRow();
            const cell = row.insertCell();
            cell.colSpan = 8;
            cell.textContent = donations.length
                ? "No available food matches these filters."
                : "No available food donations right now.";
            return;
        }

        filtered.forEach(function (item) {
            const row = tableBody.insertRow();
            [item.restaurant, item.food_name, item.food_category, item.quantity,
                `${formatDate(item.cooking_date)} / ${item.expiry_time || "-"}`,
                item.pickup_address, item.contact, item.status || "Pending"]
                .forEach(function (value, index) {
                    const cell = row.insertCell();
                    if (index === 6 && value && value !== "-") {
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
        const response = await fetch("/api/receiver/available", {
            headers: {
                "Authorization": "Bearer " + token,
                "Accept": "application/json"
            },
            cache: "no-store"
        });
        const contentType = response.headers.get("content-type") || "";
        if (!contentType.includes("application/json")) {
            throw new Error(
                "The backend returned an HTML page instead of the Available Food API. " +
                "Stop the old server and restart backend/app.py to load the new endpoint."
            );
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
            throw new Error(result.message || "Unable to load available food.");
        }

        donations = result.donations || [];
        const cities = [...new Set(donations.map(item => item.city).filter(Boolean))]
            .sort((a, b) => a.localeCompare(b));
        cities.forEach(function (city) {
            const option = document.createElement("option");
            option.value = city;
            option.textContent = city;
            cityFilter.appendChild(option);
        });

        renderDonations();
        searchInput.addEventListener("input", renderDonations);
        categoryFilter.addEventListener("change", renderDonations);
        cityFilter.addEventListener("change", renderDonations);
    } catch (error) {
        console.error("Available food error:", error);
        tableBody.replaceChildren();
        const row = tableBody.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 8;
        cell.textContent = "Unable to load available food: " + error.message;
    }
});
