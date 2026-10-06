document.addEventListener("DOMContentLoaded", function () {

    loadDonors();


    // Search button

    document.getElementById("searchBtn").addEventListener("click", function () {

        loadDonors();

    });


    // Search when typing

    document.getElementById("searchDonor").addEventListener("input", function () {

        loadDonors();

    });


    // Filter by city

    document.getElementById("cityFilter").addEventListener("change", function () {

        loadDonors();

    });


    // Filter by status

    document.getElementById("statusFilter").addEventListener("change", function () {

        loadDonors();

    });

});


async function loadDonors() {

    try {

        const response = await fetch("/api/admin/donors");

        const result = await response.json();


        if (!result.success) {

            alert(result.message || "Unable to load donors.");

            return;

        }


        const donors = result.donors || [];


        // Summary cards

        document.getElementById("totalDonors").textContent =
            donors.length;

        document.getElementById("approvedDonors").textContent =
            donors.filter(function (donor) {
                return String(donor.status).toLowerCase() === "active";
            }).length;

        document.getElementById("inactiveDonors").textContent =
            donors.filter(function (donor) {
                return String(donor.status).toLowerCase() === "inactive";
            }).length;


        // Add cities to city filter

        const cityFilter =
            document.getElementById("cityFilter");

        const currentCity =
            cityFilter.value;

        cityFilter.innerHTML = `
            <option value="">
                All Cities
            </option>
        `;


        const cities = [];


        donors.forEach(function (donor) {

            if (donor.city && !cities.includes(donor.city)) {

                cities.push(donor.city);

            }

        });


        cities.sort();


        cities.forEach(function (city) {

            const option = document.createElement("option");

            option.value = city;
            option.textContent = city;

            cityFilter.appendChild(option);

        });


        cityFilter.value = currentCity;


        // Get search and filter values

        const searchText =
            document.getElementById("searchDonor").value
                .trim()
                .toLowerCase();

        const city =
            document.getElementById("cityFilter").value;

        const status =
            document.getElementById("statusFilter").value;


        // Filter donors

        const filteredDonors = donors.filter(function (donor) {

            const searchMatch =
                !searchText ||
                String(donor.donor_id).toLowerCase().includes(searchText) ||
                String(donor.restaurant_name).toLowerCase().includes(searchText) ||
                String(donor.owner_name).toLowerCase().includes(searchText) ||
                String(donor.email).toLowerCase().includes(searchText);

            const cityMatch =
                !city || donor.city === city;

            const statusMatch =
                !status || donor.status === status;


            return searchMatch && cityMatch && statusMatch;

        });


        // Display donors

        const tableBody =
            document.getElementById("donorTableBody");

        tableBody.innerHTML = "";


        if (filteredDonors.length === 0) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="8">
                        No donors available.
                    </td>
                </tr>
            `;

            return;

        }


        // Add donors to table

        filteredDonors.forEach(function (donor) {

            const row = document.createElement("tr");


            const donorId = document.createElement("td");
            donorId.textContent = donor.donor_id;
            row.appendChild(donorId);


            const restaurantName = document.createElement("td");
            restaurantName.textContent = donor.restaurant_name;
            row.appendChild(restaurantName);


            const ownerName = document.createElement("td");
            ownerName.textContent = donor.owner_name;
            row.appendChild(ownerName);


            const email = document.createElement("td");
            email.textContent = donor.email;
            row.appendChild(email);


            const phone = document.createElement("td");
            phone.textContent = donor.phone;
            row.appendChild(phone);


            const city = document.createElement("td");
            city.textContent = donor.city;
            row.appendChild(city);


            const statusCell = document.createElement("td");
            statusCell.textContent = donor.status;
            row.appendChild(statusCell);


            const action = document.createElement("td");


            const viewButton = document.createElement("button");

            viewButton.textContent = "View";

            viewButton.onclick = function () {

                viewDonor(donor.donor_id);

            };


            const deleteButton = document.createElement("button");

            deleteButton.textContent = "Delete";

            deleteButton.onclick = function () {

                deleteDonor(donor.donor_id);

            };


            action.appendChild(viewButton);
            action.appendChild(deleteButton);

            row.appendChild(action);


            tableBody.appendChild(row);

        });

    }
    catch (error) {

        console.error("Manage Donors Error:", error);

        alert(
            "Cannot connect to the server.\n\n" +
            "Please make sure the Python backend is running."
        );

    }

}


// View donor

function viewDonor(donorId) {

    alert("Donor ID: " + donorId);

}


// Delete donor

async function deleteDonor(donorId) {

    const confirmDelete =
        confirm("Delete this donor and all donation records belonging to them?");


    if (!confirmDelete) {

        return;

    }


    try {

        const response = await fetch("/api/admin/donors/delete", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                donor_id: donorId
            })

        });


        const result = await response.json();


        if (result.success) {

            alert("Donor deleted successfully.");

            loadDonors();

        }
        else {

            alert(result.message || "Unable to delete donor.");

        }

    }
    catch (error) {

        console.error("Delete Donor Error:", error);

        alert("Cannot connect to the server.");

    }

}
