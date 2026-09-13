document.addEventListener("DOMContentLoaded", async function () {

    const donorId = localStorage.getItem("user_id");

    // Check login
    if (!donorId) {
        alert("Please login first.");
        window.location.href = "../login.html";
        return;
    }

    // Check donor
    if (!donorId.toUpperCase().startsWith("DN")) {
        alert("Invalid donor login.");
        window.location.href = "../login.html";
        return;
    }

    try {

        const response = await fetch(
            "/api/donor/dashboard?donor_id=" +
            encodeURIComponent(donorId)
        );

        const result = await response.json();

        if (!result.success) {

            alert(
                "Unable to load dashboard:\n" +
                result.message
            );

            return;
        }


        // ==========================================
        // DONOR INFORMATION
        // ==========================================

        document.getElementById("welcomeMessage").textContent =
            "Welcome, " + result.donor.resturaent_name;


        // ==========================================
        // DASHBOARD COUNTS
        // ==========================================

        document.getElementById("totalDonations").textContent =
            result.stats.total;

        document.getElementById("todayDonations").textContent =
            result.stats.today;

        document.getElementById("acceptedDonations").textContent =
            result.stats.accepted;

        document.getElementById("pendingDonations").textContent =
            result.stats.pending;


        // ==========================================
        // LATEST DONATIONS
        // ==========================================

        const tableBody =
            document.getElementById("donationTableBody");

        tableBody.innerHTML = "";


        if (!result.donations || result.donations.length === 0) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="4">
                        No donations yet.
                    </td>
                </tr>
            `;

            return;
        }


        result.donations.forEach(function (donation) {

            const row = document.createElement("tr");

            let statusClass = "";

            const status =
                donation.status || "Pending";

            if (status.toLowerCase() === "accepted") {
                statusClass = "accepted";
            }
            else if (status.toLowerCase() === "pending") {
                statusClass = "pending";
            }
            else if (status.toLowerCase() === "picked") {
                statusClass = "picked";
            }
            else if (status.toLowerCase() === "rejected") {
                statusClass = "rejected";
            }


            let donationDate = "-";

            if (donation.created_at) {

                const date =
                    new Date(donation.created_at);

                donationDate =
                    date.toLocaleDateString(
                        "en-IN",
                        {
                            day: "2-digit",
                            month: "short",
                            year: "numeric"
                        }
                    );
            }


            row.innerHTML = `
                <td>${donation.food_name || "-"}</td>

                <td>${donation.quantity || "-"}</td>

                <td>${donationDate}</td>

                <td class="${statusClass}">
                    ${status}
                </td>
            `;

            tableBody.appendChild(row);

        });


    }
    catch (error) {

        console.error("Dashboard Error:", error);

        alert(
            "Cannot connect to the server.\n\n" +
            "Please make sure the Python backend is running."
        );
    }


    // ==========================================
    // LOGOUT
    // ==========================================

    document
        .getElementById("logoutBtn")
        .addEventListener("click", function () {

            localStorage.removeItem("user_id");

        });

});