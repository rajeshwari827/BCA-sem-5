// Notifications JavaScript

let notifications = [];


// Notification Form
const notificationForm = document.getElementById("notificationForm");

notificationForm.addEventListener("submit", function (event) {

    event.preventDefault();

    // Get values from form
    const title = document.getElementById("notificationTitle").value.trim();
    const sendTo = document.getElementById("sendTo").value;
    const message = document.getElementById("notificationMessage").value.trim();

    // Check values
    if (title === "" || sendTo === "" || message === "") {
        alert("Please fill all the fields.");
        return;
    }

    // Create notification
    const notification = {
        id: notifications.length + 1,
        title: title,
        sendTo: sendTo,
        message: message,
        date: new Date().toLocaleDateString("en-IN"),
        status: "Sent"
    };

    // Add notification
    notifications.push(notification);

    // Update table
    displayNotifications();

    // Update cards
    updateSummary();

    // Clear form
    notificationForm.reset();

    alert("Notification sent successfully!");

});


// Display Notifications
function displayNotifications() {

    const tableBody = document.getElementById("notificationTableBody");

    tableBody.innerHTML = "";

    if (notifications.length === 0) {

        tableBody.innerHTML = `
            <tr>
                <td colspan="6">
                    No notifications available.
                </td>
            </tr>
        `;

        return;
    }


    notifications.forEach(function (notification) {

        const row = document.createElement("tr");

        row.innerHTML = `
            <td>${notification.id}</td>

            <td>${notification.title}</td>

            <td>${notification.sendTo}</td>

            <td>${notification.date}</td>

            <td>${notification.status}</td>

            <td>
                <button
                    type="button"
                    onclick="deleteNotification(${notification.id})">
                    Delete
                </button>
            </td>
        `;

        tableBody.appendChild(row);

    });

}


// Delete Notification
function deleteNotification(id) {

    const confirmDelete = confirm(
        "Are you sure you want to delete this notification?"
    );

    if (!confirmDelete) {
        return;
    }

    notifications = notifications.filter(function (notification) {
        return notification.id !== id;
    });

    // Reassign IDs
    notifications.forEach(function (notification, index) {
        notification.id = index + 1;
    });

    displayNotifications();

    updateSummary();

}


// Update Summary Cards
function updateSummary() {

    // Total notifications
    document.getElementById("totalNotifications").textContent =
        notifications.length;


    // Donor notifications
    const donorCount = notifications.filter(function (notification) {
        return notification.sendTo === "Food Donors";
    }).length;

    document.getElementById("donorNotifications").textContent =
        donorCount;


    // NGO notifications
    const ngoCount = notifications.filter(function (notification) {
        return notification.sendTo === "NGOs";
    }).length;

    document.getElementById("ngoNotifications").textContent =
        ngoCount;


    // All user notifications
    const allUserCount = notifications.filter(function (notification) {
        return notification.sendTo === "All Users";
    }).length;

    document.getElementById("allUserNotifications").textContent =
        allUserCount;

}


// Initial display
displayNotifications();
updateSummary();
