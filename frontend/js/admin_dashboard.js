document.addEventListener("DOMContentLoaded", function () {

    loadDashboardData();

});


async function loadDashboardData() {

    try {

        const response = await fetch("/api/admin/dashboard");

        const result = await response.json();


        if (!result.success) {

            alert(result.message || "Unable to load dashboard data.");

            return;

        }


        // Welcome message

        if (result.admin_name) {

            document.getElementById("welcomeMessage").textContent =
                "Welcome, " + result.admin_name;

        }


        // Dashboard cards

        document.getElementById("totalUsers").textContent =
            result.total_users;

        document.getElementById("totalDonors").textContent =
            result.total_donors;

        document.getElementById("totalNGOs").textContent =
            result.total_ngos;

        document.getElementById("totalDonations").textContent =
            result.total_donations;

        document.getElementById("pendingDonations").textContent =
            result.pending_donations;

        document.getElementById("completedDonations").textContent =
            result.completed_donations;


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

        alert(
            "Cannot connect to the server.\n\n" +
            "Please make sure the Python backend is running."
        );

    }

}