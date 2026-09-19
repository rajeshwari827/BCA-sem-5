document.addEventListener("DOMContentLoaded", async function () {

    const donorId = localStorage.getItem("user_id");

    // Check login
    if (!donorId) {
        alert("Please login first.");
        window.location.href = "../login.html";
        return;
    }

    // Check donor ID
    if (!donorId.toUpperCase().startsWith("DN")) {
        alert("Invalid donor login.");
        window.location.href = "../login.html";
        return;
    }

    const tableBody = document.getElementById("donationHistoryBody");

    // Check table body
    if (!tableBody) {
        console.error("donationHistoryBody not found.");
        return;
    }

    let allDonations = [];

    // Load donation history
    try {

        const response = await fetch(
            "/api/donor/donations?donor_id=" +
            encodeURIComponent(donorId)
        );

        const result = await response.json();

        if (!result.success) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="7">
                        ${result.message || "Unable to load donation history."}
                    </td>
                </tr>
            `;

            return;
        }

        displayDonations(result.donations);

    } catch (error) {

        console.error("Donation History Error:", error);

        tableBody.innerHTML = `
            <tr>
                <td colspan="7">
                    Cannot connect to the server.
                    Please make sure the Python backend is running.
                </td>
            </tr>
        `;
    }

    // Search
    const searchFood = document.getElementById("searchFood");

    if (searchFood) {
        searchFood.addEventListener("input", filterDonations);
    }

    // Status filter
    const statusFilter = document.getElementById("statusFilter");

    if (statusFilter) {
        statusFilter.addEventListener("change", filterDonations);
    }

    // Logout
    const logoutBtn = document.getElementById("logoutBtn");

    if (logoutBtn) {
        logoutBtn.addEventListener("click", function () {
            localStorage.removeItem("user_id");
        });
    }


    // Store all donations
    function displayDonations(donations) {

        allDonations = donations || [];

        renderTable(allDonations);
    }


    // Display table
    function renderTable(donations) {

        tableBody.innerHTML = "";

        if (!donations || donations.length === 0) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="7">
                        No donation records found.
                    </td>
                </tr>
            `;

            return;
        }


        donations.forEach(function (donation) {

            const row = document.createElement("tr");


            // Status
            const status = donation.status || "Pending";

            let statusClass = "";

            if (status.toLowerCase() === "accepted") {
                statusClass = "accepted";

            } else if (status.toLowerCase() === "pending") {
                statusClass = "pending";

            } else if (
                status.toLowerCase() === "picked up" ||
                status.toLowerCase() === "picked"
            ) {
                statusClass = "picked";

            } else if (status.toLowerCase() === "rejected") {
                statusClass = "rejected";
            }


            // Donation date
            let donationDate = "-";

            if (donation.created_at) {

                const date = new Date(donation.created_at);

                if (!isNaN(date.getTime())) {

                    donationDate = date.toLocaleDateString("en-IN", {
                        day: "2-digit",
                        month: "short",
                        year: "numeric"
                    });
                }
            }


            // Food category
            const foodCategory =
                donation.food_category &&
                donation.food_category.toString().trim() !== ""
                    ? donation.food_category
                    : "-";


            // Create row
            row.innerHTML = `

                <td>${donation.donation_id || "-"}</td>

                <td>${donation.food_name || "-"}</td>

                <td>${foodCategory}</td>

                <td>${donation.quantity || "-"}</td>

                <td>${donation.pickup_time || "-"}</td>

                <td>${donationDate}</td>

                <td>
                    <span class="${statusClass}">
                        ${status}
                    </span>
                </td>

            `;

            tableBody.appendChild(row);

        });
    }


    // Search and filter
    function filterDonations() {

        const searchElement = document.getElementById("searchFood");
        const statusElement = document.getElementById("statusFilter");

        const searchText = searchElement
            ? searchElement.value.toLowerCase().trim()
            : "";

        const selectedStatus = statusElement
            ? statusElement.value
            : "All";


        const filtered = allDonations.filter(function (donation) {

            const foodName =
                (donation.food_name || "")
                    .toString()
                    .toLowerCase();

            const foodCategory =
                (donation.food_category || "")
                    .toString()
                    .toLowerCase();

            const status =
                (donation.status || "Pending")
                    .toString();


            // Search food name OR category
            const matchesSearch =
                foodName.includes(searchText) ||
                foodCategory.includes(searchText);


            // Status filter
            const matchesStatus =
                selectedStatus === "All" ||
                status.toLowerCase() ===
                selectedStatus.toLowerCase();


            return matchesSearch && matchesStatus;

        });


        renderTable(filtered);
    }

});