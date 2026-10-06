document.addEventListener("DOMContentLoaded", function () {

    loadDashboardData();

});


async function loadDashboardData() {

    try {

        const token = sessionStorage.getItem("token") ||
            localStorage.getItem("token") ||
            localStorage.getItem("session_token");
        const headers = token ? { "Authorization": "Bearer " + token } : {};
        const response = await fetch("/api/admin/dashboard", {
            headers: headers,
            cache: "no-store"
        });

        const result = await response.json();


        if (!response.ok || !result.success) {
            setDashboardStatus(result.message || "Unable to load dashboard totals. Please sign in again.", true);
            return;

        }


        // Welcome message

        if (result.admin_name) {

            document.getElementById("welcomeMessage").textContent =
                "Welcome, " + result.admin_name;

        }


        // Dashboard cards

        const donors = Number(result.total_donors) || 0;
        const receivers = Number(result.total_receivers ?? result.total_ngos) || 0;
        document.getElementById("totalUsers").textContent = donors + receivers;

        document.getElementById("totalDonors").textContent =
            donors;

        document.getElementById("totalNGOs").textContent =
            receivers;

        document.getElementById("totalDonations").textContent =
            result.total_donations;

        document.getElementById("pendingDonations").textContent =
            result.pending_donations;

        document.getElementById("completedDonations").textContent =
            result.completed_donations;

        setDashboardStatus("Totals updated from the latest database records.");


        // Recent activities

        const activitiesBody =
            document.getElementById("recentActivitiesBody");

        activitiesBody.innerHTML = "";


        if (!result.activities || result.activities.length === 0) {

            activitiesBody.innerHTML = `
                <tr>
                    <td colspan="3">
                        No recent activities.
                    </td>
                </tr>
            `;

            return;

        }


        result.activities.forEach(function (activity) {

            const row = document.createElement("tr");


            row.innerHTML = `
                <td>${activity.date}</td>
                <td>${activity.activity}</td>
                <td>${activity.status}</td>
            `;


            activitiesBody.appendChild(row);

        });


    }
    catch (error) {

        console.error("Dashboard Error:", error);

        setDashboardStatus("Could not load totals. Check that the backend is running, then refresh this page.", true);

    }

}

function setDashboardStatus(message, isError = false) {
    const status = document.getElementById("dashboardStatus");
    status.textContent = message;
    status.classList.toggle("error", isError);
}
