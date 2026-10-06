document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("notificationForm").addEventListener("submit", createNotification);
    loadNotifications();
});

let notifications = [];

async function loadNotifications() {
    try {
        const response = await fetch("/api/admin/notifications", { cache: "no-store" });
        const result = await response.json();
        if (!response.ok || !result.success) throw new Error(result.message || "Unable to load notifications.");
        notifications = result.notifications || [];
        renderNotifications();
        updateSummary();
    } catch (error) {
        console.error("Notification load error:", error);
        document.getElementById("notificationTableBody").innerHTML =
            `<tr><td colspan="6">${error.message}</td></tr>`;
    }
}

async function createNotification(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector("button[type='submit']");
    button.disabled = true;
    try {
        const response = await fetch("/api/admin/notifications", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                title: document.getElementById("notificationTitle").value.trim(),
                send_to: document.getElementById("sendTo").value,
                message: document.getElementById("notificationMessage").value.trim()
            })
        });
        const result = await response.json();
        if (!response.ok || !result.success) throw new Error(result.message || "Unable to save notification.");
        form.reset();
        await loadNotifications();
        alert("Notification saved.");
    } catch (error) {
        alert(error.message);
    } finally {
        button.disabled = false;
    }
}

function renderNotifications() {
    const body = document.getElementById("notificationTableBody");
    body.replaceChildren();
    if (!notifications.length) {
        body.innerHTML = "<tr><td colspan='6'>No notifications available.</td></tr>";
        return;
    }
    notifications.forEach(function (notification) {
        const row = body.insertRow();
        [notification.id, notification.title, notification.sendTo,
            notification.date ? new Date(notification.date).toLocaleDateString() : "-",
            notification.status].forEach(value => { row.insertCell().textContent = value ?? "-"; });
        const action = row.insertCell();
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = "Delete";
        button.addEventListener("click", () => deleteNotification(notification.id));
        action.appendChild(button);
    });
}

async function deleteNotification(id) {
    if (!confirm("Delete this notification?")) return;
    try {
        const response = await fetch("/api/admin/notifications/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ notification_id: id })
        });
        const result = await response.json();
        if (!response.ok || !result.success) throw new Error(result.message || "Unable to delete notification.");
        await loadNotifications();
    } catch (error) {
        alert(error.message);
    }
}

function updateSummary() {
    document.getElementById("totalNotifications").textContent = notifications.length;
    document.getElementById("donorNotifications").textContent =
        notifications.filter(item => item.sendTo === "Food Donors").length;
    document.getElementById("ngoNotifications").textContent =
        notifications.filter(item => item.sendTo === "NGOs").length;
    document.getElementById("allUserNotifications").textContent =
        notifications.filter(item => item.sendTo === "All Users").length;
}
