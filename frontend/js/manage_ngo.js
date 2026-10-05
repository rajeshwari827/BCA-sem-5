document.addEventListener("DOMContentLoaded", function () {

    loadNGOs();


    // Search button

    document.getElementById("searchBtn").addEventListener("click", function () {

        loadNGOs();

    });


    // Search when typing

    document.getElementById("searchNGO").addEventListener("input", function () {

        loadNGOs();

    });


    // Filter by city

    document.getElementById("cityFilter").addEventListener("change", function () {

        loadNGOs();

    });


    // Filter by status

    document.getElementById("statusFilter").addEventListener("change", function () {

        loadNGOs();

    });

});


async function loadNGOs() {

    try {

        const response = await fetch("/api/admin/ngos");

        const result = await response.json();


        if (!result.success) {

            alert(result.message || "Unable to load NGOs.");

            return;

        }


        const ngos = result.ngos || [];


        // Summary cards

        document.getElementById("totalNGOs").textContent =
            ngos.length;

        document.getElementById("approvedNGOs").textContent =
            ngos.filter(function (ngo) {
                return ngo.status === "Approved";
            }).length;

        document.getElementById("pendingNGOs").textContent =
            ngos.filter(function (ngo) {
                return ngo.status === "Pending";
            }).length;

        document.getElementById("rejectedNGOs").textContent =
            ngos.filter(function (ngo) {
                return ngo.status === "Rejected";
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


        ngos.forEach(function (ngo) {

            if (ngo.city && !cities.includes(ngo.city)) {

                cities.push(ngo.city);

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
            document.getElementById("searchNGO").value
                .trim()
                .toLowerCase();

        const city =
            document.getElementById("cityFilter").value;

        const status =
            document.getElementById("statusFilter").value;


        // Filter NGOs

        const filteredNGOs = ngos.filter(function (ngo) {

            const searchMatch =
                !searchText ||
                String(ngo.ngo_id).toLowerCase().includes(searchText) ||
                String(ngo.ngo_name).toLowerCase().includes(searchText) ||
                String(ngo.representative).toLowerCase().includes(searchText) ||
                String(ngo.email).toLowerCase().includes(searchText);

            const cityMatch =
                !city || ngo.city === city;

            const statusMatch =
                !status || ngo.status === status;


            return searchMatch && cityMatch && statusMatch;

        });


        // Display NGOs

        const tableBody =
            document.getElementById("ngoTableBody");

        tableBody.innerHTML = "";


        if (filteredNGOs.length === 0) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="8">
                        No NGOs available.
                    </td>
                </tr>
            `;

            return;

        }


        // Add NGOs to table

        filteredNGOs.forEach(function (ngo) {

            const row = document.createElement("tr");


            const ngoId = document.createElement("td");
            ngoId.textContent = ngo.ngo_id;
            row.appendChild(ngoId);


            const ngoName = document.createElement("td");
            ngoName.textContent = ngo.ngo_name;
            row.appendChild(ngoName);


            const representative = document.createElement("td");
            representative.textContent = ngo.representative;
            row.appendChild(representative);


            const email = document.createElement("td");
            email.textContent = ngo.email;
            row.appendChild(email);


            const phone = document.createElement("td");
            phone.textContent = ngo.phone;
            row.appendChild(phone);


            const city = document.createElement("td");
            city.textContent = ngo.city;
            row.appendChild(city);


            const statusCell = document.createElement("td");
            statusCell.textContent = ngo.status;
            row.appendChild(statusCell);


            const action = document.createElement("td");


            const viewButton = document.createElement("button");

            viewButton.textContent = "View";

            viewButton.onclick = function () {

                viewNGO(ngo.ngo_id);

            };


            const deleteButton = document.createElement("button");

            deleteButton.textContent = "Delete";

            deleteButton.onclick = function () {

                deleteNGO(ngo.ngo_id);

            };


            action.appendChild(viewButton);
            action.appendChild(deleteButton);

            row.appendChild(action);


            tableBody.appendChild(row);

        });

    }
    catch (error) {

        console.error("Manage NGOs Error:", error);

        alert(
            "Cannot connect to the server.\n\n" +
            "Please make sure the Python backend is running."
        );

    }

}


// View NGO

function viewNGO(ngoId) {

    alert("NGO ID: " + ngoId);

}


// Delete NGO

async function deleteNGO(ngoId) {

    const confirmDelete =
        confirm("Are you sure you want to delete this NGO?");


    if (!confirmDelete) {

        return;

    }


    try {

        const response = await fetch("/api/admin/ngos/delete", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                ngo_id: ngoId
            })

        });


        const result = await response.json();


        if (result.success) {

            alert("NGO deleted successfully.");

            loadNGOs();

        }
        else {

            alert(result.message || "Unable to delete NGO.");

        }

    }
    catch (error) {

        console.error("Delete NGO Error:", error);

        alert("Cannot connect to the server.");

    }

}