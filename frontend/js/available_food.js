document.addEventListener("DOMContentLoaded", async function () {

    const receiverId =
        localStorage.getItem("user_id") ||
        sessionStorage.getItem("user_id");

    const token =
        localStorage.getItem("token") ||
        localStorage.getItem("session_token") ||
        sessionStorage.getItem("token") ||
        sessionStorage.getItem("session_token");


    // Check receiver login
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


    // Format date
    function formatDate(value) {

        if (!value) {
            return "-";
        }

        const date = new Date(value);

        return Number.isNaN(date.getTime())
            ? String(value)
            : date.toLocaleDateString("en-IN", {
                day: "2-digit",
                month: "short",
                year: "numeric"
            });
    }


    // Accept Food
    async function acceptFood(donationId) {

        if (!donationId) {

            alert("Invalid donation.");

            return;
        }


        const confirmAccept = confirm(
            "Do you want to accept this food donation?"
        );


        if (!confirmAccept) {
            return;
        }


        try {

            const response = await fetch("/api/receiver/accept", {

                method: "POST",

                headers: {

                    "Authorization": "Bearer " + token,

                    "Content-Type": "application/json",

                    "Accept": "application/json"

                },

                body: JSON.stringify({

                    donation_id: donationId,

                    receiver_id: receiverId

                })

            });


            const contentType =
                response.headers.get("content-type") || "";


            if (!contentType.includes("application/json")) {

                throw new Error(
                    "The backend returned an invalid response."
                );

            }


            const result = await response.json();


            // Session expired
            if (response.status === 401 || response.status === 403) {

                ["user_id", "user_role", "token", "session_token"]
                    .forEach(function (key) {

                        localStorage.removeItem(key);

                        sessionStorage.removeItem(key);

                    });


                alert(
                    "Your receiver session has expired. Please log in again."
                );


                window.location.replace("../login.html");

                return;
            }


            if (!response.ok || !result.success) {

                throw new Error(
                    result.message || "Unable to accept food."
                );

            }


            alert("Food accepted successfully!");


            // Remove accepted food from current list
            donations = donations.filter(function (item) {

                return String(item.donation_id) !== String(donationId);

            });


            renderDonations();


        } catch (error) {

            console.error("Accept food error:", error);

            alert(
                "Unable to accept food: " + error.message
            );

        }

    }


    // Make function available for button
    window.acceptFood = acceptFood;


    // Display donations
    function renderDonations() {

        const search =
            searchInput.value.trim().toLowerCase();

        const category =
            categoryFilter.value.toLowerCase();

        const city =
            cityFilter.value.toLowerCase();


        const filtered = donations.filter(function (item) {

            const searchable = [

                item.restaurant,

                item.food_name,

                item.food_category,

                item.city

            ]
                .join(" ")
                .toLowerCase();


            return (

                (!search || searchable.includes(search))

                &&

                (!category ||
                    String(item.food_category || "")
                        .toLowerCase() === category)

                &&

                (!city ||
                    String(item.city || "")
                        .toLowerCase() === city)

            );

        });


        tableBody.replaceChildren();


        // No food available
        if (!filtered.length) {

            const row = tableBody.insertRow();

            const cell = row.insertCell();

            cell.colSpan = 8;


            cell.textContent = donations.length

                ? "No available food matches these filters."

                : "No available food donations right now.";


            return;
        }


        // Create rows
        filtered.forEach(function (item) {

            const row = tableBody.insertRow();


            // Restaurant
            let cell = row.insertCell();

            cell.textContent =
                item.restaurant || "-";


            // Food
            cell = row.insertCell();

            cell.textContent =
                item.food_name || "-";


            // Category
            cell = row.insertCell();

            cell.textContent =
                item.food_category || "-";


            // Quantity
            cell = row.insertCell();

            cell.textContent =
                item.quantity || "-";


            // Cooking / Expiry
            cell = row.insertCell();

            cell.textContent =
                `${formatDate(item.cooking_date)} / ${item.expiry_time || "-"}`;


            // Pickup Address
            cell = row.insertCell();

            cell.textContent =
                item.pickup_address || "-";


            // Contact
            cell = row.insertCell();


            if (item.contact && item.contact !== "-") {

                const link = document.createElement("a");

                link.href =
                    "tel:" +
                    String(item.contact).replace(/[^\d+]/g, "");

                link.textContent =
                    item.contact;

                cell.appendChild(link);

            } else {

                cell.textContent = "-";

            }


            // Status / Accept button
            cell = row.insertCell();


            const button =
                document.createElement("button");


            button.type = "button";

            button.className = "accept-btn";

            button.textContent = "Accept Food";


            button.addEventListener("click", function () {

                acceptFood(item.donation_id);

            });


            cell.appendChild(button);

        });

    }


    try {

        // Get available food
        const response = await fetch(
            "/api/receiver/available",
            {

                headers: {

                    "Authorization":
                        "Bearer " + token,

                    "Accept":
                        "application/json"

                },

                cache: "no-store"

            }
        );


        const contentType =
            response.headers.get("content-type") || "";


        if (!contentType.includes("application/json")) {

            throw new Error(

                "The backend returned an HTML page instead of the Available Food API. " +

                "Stop the old server and restart backend/app.py to load the new endpoint."

            );

        }


        const result =
            await response.json();


        // Session expired
        if (
            response.status === 401 ||
            response.status === 403
        ) {

            [
                "user_id",
                "user_role",
                "token",
                "session_token"
            ]
                .forEach(function (key) {

                    localStorage.removeItem(key);

                    sessionStorage.removeItem(key);

                });


            alert(
                "Your receiver session has expired. Please log in again."
            );


            window.location.replace("../login.html");

            return;
        }


        if (!response.ok || !result.success) {

            throw new Error(
                result.message ||
                "Unable to load available food."
            );

        }


        // Store donations
        donations =
            result.donations || [];


        // Add cities to filter
        const cities =
            [
                ...new Set(
                    donations
                        .map(item => item.city)
                        .filter(Boolean)
                )
            ]
                .sort(
                    (a, b) =>
                        a.localeCompare(b)
                );


        cities.forEach(function (city) {

            const option =
                document.createElement("option");


            option.value = city;

            option.textContent = city;


            cityFilter.appendChild(option);

        });


        // Display food
        renderDonations();


        // Search
        searchInput.addEventListener(
            "input",
            renderDonations
        );


        // Category filter
        categoryFilter.addEventListener(
            "change",
            renderDonations
        );


        // City filter
        cityFilter.addEventListener(
            "change",
            renderDonations
        );


    } catch (error) {

        console.error(
            "Available food error:",
            error
        );


        tableBody.replaceChildren();


        const row =
            tableBody.insertRow();


        const cell =
            row.insertCell();


        cell.colSpan = 8;


        cell.textContent =
            "Unable to load available food: " +
            error.message;

    }

});