document.addEventListener("DOMContentLoaded", function () {

    loadDonations();


    // Search button

    document.getElementById("searchBtn").addEventListener("click", function () {

        loadDonations();

    });


    // Search when typing

    document.getElementById("searchDonation").addEventListener("input", function () {

        loadDonations();

    });


    // Filter by status

    document.getElementById("statusFilter").addEventListener("change", function () {

        loadDonations();

    });

});


async function loadDonations() {

    try {

        const response = await fetch("/api/admin/donations");

        const result = await response.json();


        if (!result.success) {

            alert(result.message || "Unable to load donations.");

            return;

        }


        const donations = result.donations || [];


        // Summary cards

        document.getElementById("totalDonations").textContent =
            donations.length;

        document.getElementById("acceptedDonations").textContent =
            donations.filter(function (donation) {
                return ["accepted", "approved"].includes(String(donation.status).toLowerCase());
            }).length;

        document.getElementById("pendingDonations").textContent =
            donations.filter(function (donation) {
                return String(donation.status).toLowerCase() === "pending";
            }).length;

        document.getElementById("rejectedDonations").textContent =
            donations.filter(function (donation) {
                return String(donation.status).toLowerCase() === "rejected";
            }).length;

        document.getElementById("pickedUpDonations").textContent =
            donations.filter(function (donation) {
                return ["picked up", "collected", "completed"].includes(String(donation.status).toLowerCase());
            }).length;


        // Get search and filter values

        const searchText =
            document.getElementById("searchDonation").value
                .trim()
                .toLowerCase();

        const status =
            document.getElementById("statusFilter").value;


        // Filter donations

        const filteredDonations = donations.filter(function (donation) {

            const searchMatch =
                !searchText ||
                String(donation.donation_id).toLowerCase().includes(searchText) ||
                String(donation.donor).toLowerCase().includes(searchText) ||
                String(donation.food_name).toLowerCase().includes(searchText) ||
                String(donation.category).toLowerCase().includes(searchText);

            const statusMatch =
                !status || String(donation.status).toLowerCase() === status.toLowerCase();


            return searchMatch && statusMatch;

        });


        // Display donations

        const tableBody =
            document.getElementById("donationTableBody");

        tableBody.innerHTML = "";


        if (filteredDonations.length === 0) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="9">
                        No donations available.
                    </td>
                </tr>
            `;

            return;

        }


        // Add donations to table

        filteredDonations.forEach(function (donation) {

            const row = document.createElement("tr");


            const donationId = document.createElement("td");
            donationId.textContent = donation.donation_id;
            row.appendChild(donationId);


            const donor = document.createElement("td");
            donor.textContent = donation.donor;
            row.appendChild(donor);


            const foodName = document.createElement("td");
            foodName.textContent = donation.food_name;
            row.appendChild(foodName);


            const category = document.createElement("td");
            category.textContent = donation.category;
            row.appendChild(category);


            const quantity = document.createElement("td");
            quantity.textContent = donation.quantity;
            row.appendChild(quantity);


            const city = document.createElement("td");
            city.textContent = donation.city;
            row.appendChild(city);


            const date = document.createElement("td");
            date.textContent = donation.date;
            row.appendChild(date);


            const statusCell = document.createElement("td");
            statusCell.textContent = donation.status;
            row.appendChild(statusCell);


            const action = document.createElement("td");


            const viewButton = document.createElement("button");

            viewButton.textContent = "View";

            viewButton.onclick = function () {

                viewDonation(donation.donation_id);

            };


            const deleteButton = document.createElement("button");

            deleteButton.textContent = "Delete";

            deleteButton.onclick = function () {

                deleteDonation(donation.donation_id);

            };


            action.appendChild(viewButton);
            action.appendChild(deleteButton);

            row.appendChild(action);


            tableBody.appendChild(row);

        });

    }
    catch (error) {

        console.error("Manage Donations Error:", error);

        alert(
            "Cannot connect to the server.\n\n" +
            "Please make sure the Python backend is running."
        );

    }

}


// View donation

function viewDonation(donationId) {

    alert("Donation ID: " + donationId);

}


// Delete donation

async function deleteDonation(donationId) {

    const confirmDelete =
        confirm("Delete this donation and its pickup history?");


    if (!confirmDelete) {

        return;

    }


    try {

        const response = await fetch("/api/admin/donations/delete", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                donation_id: donationId
            })

        });


        const result = await response.json();


        if (result.success) {

            alert("Donation deleted successfully.");

            loadDonations();

        }
        else {

            alert(result.message || "Unable to delete donation.");

        }

    }
    catch (error) {

        console.error("Delete Donation Error:", error);

        alert("Cannot connect to the server.");

    }

}
