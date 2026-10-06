document.addEventListener("DOMContentLoaded", function () {

    loadReports();


    // Download PDF

    document.getElementById("downloadPdfBtn").addEventListener("click", function () {

        window.open("/api/admin/reports/pdf", "_blank");

    });


    // Download Excel

    document.getElementById("downloadExcelBtn").addEventListener("click", function () {

        window.open("/api/admin/reports/excel", "_blank");

    });


    // Print Report

    document.getElementById("printReportBtn").addEventListener("click", function () {

        window.print();

    });

});


async function loadReports() {

    try {

        const response = await fetch("/api/admin/reports", { cache: "no-store" });

        const result = await response.json();


        if (!response.ok || !result.success) {

            alert(result.message || "Unable to load reports.");

            return;

        }


        // Report cards

        document.getElementById("totalUsers").textContent =
            result.total_users;

        document.getElementById("totalDonors").textContent =
            result.total_donors;

        document.getElementById("totalNGOs").textContent =
            result.total_ngos;

        document.getElementById("totalDonations").textContent =
            result.total_donations;

        document.getElementById("acceptedDonations").textContent =
            result.accepted_donations;

        document.getElementById("pendingDonations").textContent =
            result.pending_donations;

        document.getElementById("rejectedDonations").textContent =
            result.rejected_donations;

        document.getElementById("todayDonations").textContent =
            result.today_donations;


        // Monthly report

        const tableBody =
            document.getElementById("monthlyReportBody");

        tableBody.innerHTML = "";


        if (!result.monthly_report ||
            result.monthly_report.length === 0) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="5">
                        No monthly report data available.
                    </td>
                </tr>
            `;

            return;

        }


        // Add monthly report rows

        result.monthly_report.forEach(function (month) {

            const row = document.createElement("tr");


            const monthCell = document.createElement("td");
            monthCell.textContent = month.month;
            row.appendChild(monthCell);


            const totalCell = document.createElement("td");
            totalCell.textContent = month.total;
            row.appendChild(totalCell);


            const acceptedCell = document.createElement("td");
            acceptedCell.textContent = month.accepted;
            row.appendChild(acceptedCell);


            const pendingCell = document.createElement("td");
            pendingCell.textContent = month.pending;
            row.appendChild(pendingCell);


            const rejectedCell = document.createElement("td");
            rejectedCell.textContent = month.rejected;
            row.appendChild(rejectedCell);


            tableBody.appendChild(row);

        });

    }
    catch (error) {

        console.error("Reports Error:", error);

        alert(
            "Cannot connect to the server.\n\n" +
            "Please make sure the Python backend is running."
        );

    }

}
