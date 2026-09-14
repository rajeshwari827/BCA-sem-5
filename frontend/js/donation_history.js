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

    try {

        const response = await fetch(
            "/api/donor/donations?donor_id=" +
            encodeURIComponent(donorId)
        );


        const result = await response.json();


        if (!result.success) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="6">
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
                <td colspan="6">
                    Cannot connect to the server.
                    Please make sure the Python backend is running.
                </td>
            </tr>
        `;
    }


    // Search
    document.getElementById("searchFood").addEventListener(
        "input",
        filterDonations
    );


    // Status filter
    document.getElementById("statusFilter").addEventListener(
        "change",
        filterDonations
    );


    // Logout
    document.getElementById("logoutBtn").addEventListener(
        "click",
        function () {

            localStorage.removeItem("user_id");

        }
    );


    let allDonations = [];


    function displayDonations(donations) {

        allDonations = donations || [];

        renderTable(allDonations);
    }


    function renderTable(donations) {

        tableBody.innerHTML = "";


        if (!donations || donations.length === 0) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="6">
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


            // Date
            let donationDate = "-";

            if (donation.created_at) {

                const date = new Date(donation.created_at);

                donationDate = date.toLocaleDateString("en-IN", {

                    day: "2-digit",

                    month: "short",

                    year: "numeric"

                });
            }


            row.innerHTML = `

                <td>${donation.donation_id || "-"}</td>

                <td>${donation.food_name || "-"}</td>

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


    function filterDonations() {

        const searchText =
            document.getElementById("searchFood")
                .value
                .toLowerCase()
                .trim();


        const selectedStatus =
            document.getElementById("statusFilter").value;


        const filtered = allDonations.filter(function (donation) {

            const foodName =
                (donation.food_name || "")
                    .toLowerCase();


            const status =
                donation.status || "Pending";


            const matchesSearch =
                foodName.includes(searchText);


            const matchesStatus =
                selectedStatus === "All" ||
                status.toLowerCase() === selectedStatus.toLowerCase();


            return matchesSearch && matchesStatus;

        });


        renderTable(filtered);

    }

});