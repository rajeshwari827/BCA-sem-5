document.addEventListener("DOMContentLoaded", function () {

    loadUsers();


    // Search button

    document.getElementById("searchBtn").addEventListener("click", function () {

        loadUsers();

    });


    // Search when typing

    document.getElementById("searchUser").addEventListener("input", function () {

        loadUsers();

    });


    // Filter by role

    document.getElementById("roleFilter").addEventListener("change", function () {

        loadUsers();

    });


    // Filter by status

    document.getElementById("statusFilter").addEventListener("change", function () {

        loadUsers();

    });

});


async function loadUsers() {

    try {

        const response = await fetch("/api/admin/users");

        const result = await response.json();


        if (!result.success) {

            alert(result.message || "Unable to load users.");

            return;

        }


        const users = result.users || [];


        // Summary cards

        document.getElementById("totalUsers").textContent =
            users.length;

        document.getElementById("totalDonors").textContent =
            users.filter(function (user) {
                return user.role === "Donor";
            }).length;

        document.getElementById("totalNGOs").textContent =
            users.filter(function (user) {
                return user.role === "NGO";
            }).length;

        document.getElementById("inactiveUsers").textContent =
            users.filter(function (user) {
                return user.status === "Inactive";
            }).length;


        // Get filter values

        const searchText =
            document.getElementById("searchUser").value
                .trim()
                .toLowerCase();

        const role =
            document.getElementById("roleFilter").value;

        const status =
            document.getElementById("statusFilter").value;


        // Filter users

        const filteredUsers = users.filter(function (user) {

            const searchMatch =
                !searchText ||
                String(user.user_id).toLowerCase().includes(searchText) ||
                String(user.name).toLowerCase().includes(searchText) ||
                String(user.email).toLowerCase().includes(searchText);

            const roleMatch =
                !role || user.role === role;

            const statusMatch =
                !status || user.status === status;


            return searchMatch && roleMatch && statusMatch;

        });


        // Display users

        const tableBody =
            document.getElementById("userTableBody");

        tableBody.innerHTML = "";


        if (filteredUsers.length === 0) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="8">
                        No users available.
                    </td>
                </tr>
            `;

            return;

        }


        // Add users to table

        filteredUsers.forEach(function (user) {

            const row = document.createElement("tr");


            const userId = document.createElement("td");
            userId.textContent = user.user_id;
            row.appendChild(userId);


            const name = document.createElement("td");
            name.textContent = user.name;
            row.appendChild(name);


            const email = document.createElement("td");
            email.textContent = user.email;
            row.appendChild(email);


            const phone = document.createElement("td");
            phone.textContent = user.phone;
            row.appendChild(phone);


            const city = document.createElement("td");
            city.textContent = user.city;
            row.appendChild(city);


            const roleCell = document.createElement("td");
            roleCell.textContent = user.role;
            row.appendChild(roleCell);


            const statusCell = document.createElement("td");
            statusCell.textContent = user.status;
            row.appendChild(statusCell);


            const action = document.createElement("td");


            const viewButton = document.createElement("button");
            viewButton.textContent = "View";

            viewButton.onclick = function () {

                viewUser(user.user_id);

            };


            const deleteButton = document.createElement("button");
            deleteButton.textContent = "Delete";

            deleteButton.onclick = function () {

                deleteUser(user.user_id);

            };


            action.appendChild(viewButton);
            action.appendChild(deleteButton);

            row.appendChild(action);


            tableBody.appendChild(row);

        });

    }
    catch (error) {

        console.error("Manage Users Error:", error);

        alert(
            "Cannot connect to the server.\n\n" +
            "Please make sure the Python backend is running."
        );

    }

}


// View user

function viewUser(userId) {

    alert("User ID: " + userId);

}


// Delete user

async function deleteUser(userId) {

    const userIdPrefix = String(userId).toUpperCase();
    const deleteMessage = userIdPrefix.startsWith("DN")
        ? "Delete this donor and all donation records belonging to them?"
        : "Delete this NGO and its pickup history? Donations will remain available.";
    const confirmDelete = confirm(deleteMessage);


    if (!confirmDelete) {

        return;

    }


    try {

        const response = await fetch("/api/admin/users/delete", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                user_id: userId
            })

        });


        const result = await response.json();


        if (result.success) {

            alert("User deleted successfully.");

            loadUsers();

        }
        else {

            alert(result.message || "Unable to delete user.");

        }

    }
    catch (error) {

        console.error("Delete User Error:", error);

        alert("Cannot connect to the server.");

    }

}
