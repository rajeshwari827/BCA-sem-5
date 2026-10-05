document.addEventListener("DOMContentLoaded", async function () {

    const donorId = localStorage.getItem("user_id");
    const token = localStorage.getItem("token");

    if (!donorId || !token) {
        alert("Please login first.");
        window.location.replace("../login.html");
        return;
    }

    if (!donorId.toUpperCase().startsWith("DN")) {
        alert("Invalid donor login.");
        window.location.replace("../login.html");
        return;
    }

    try {
        const response = await fetch("/api/donor/profile", {
            method: "GET",
            headers: {
                "Authorization": "Bearer " + token,
                "Accept": "application/json"
            },
            cache: "no-store"
        });

        const result = await response.json();

        if (response.status === 401) {
            localStorage.removeItem("user_id");
            localStorage.removeItem("user_role");
            localStorage.removeItem("token");
            alert("Your login session is no longer valid. Please log in again.");
            window.location.replace("../login.html");
            return;
        }

        if (!response.ok || !result.success) {
            alert("Unable to load profile:\n" + (result.message || "Unknown server error."));
            return;
        }

        const donor = result.donor || {};

        document.getElementById("donor_id").textContent = donor.donor_id || donorId;
        document.getElementById("restaurant_name").textContent = donor.resturaent_name || "-";
        document.getElementById("owner_name").textContent = donor.owner_name || "-";
        document.getElementById("email").textContent = donor.email || "-";
        document.getElementById("phone").textContent = donor.phone || "-";
        document.getElementById("address").textContent = donor.address || "-";
        document.getElementById("city").textContent = donor.city || "-";
        document.getElementById("location").textContent = donor.location || "-";

        document.getElementById("registration_date").textContent = donor.created_at
            ? new Date(donor.created_at).toLocaleDateString("en-IN", {
                day: "2-digit", month: "long", year: "numeric"
            })
            : "-";

    } catch (error) {
        console.error("Profile Error:", error);
        alert("Cannot connect to the server.\n\nPlease make sure app.py is running.");
    }

    async function logout() {
        const currentToken = localStorage.getItem("token");
        try {
            if (currentToken) {
                await fetch("/api/logout", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + currentToken
                    },
                    body: "{}",
                    keepalive: true
                });
            }
        } catch (error) {
            console.error("Logout Error:", error);
        }
        localStorage.removeItem("user_id");
        localStorage.removeItem("user_role");
        localStorage.removeItem("token");
        window.location.replace("../login.html");
    }

    const logoutBtn = document.getElementById("logoutBtn");
    if (logoutBtn) logoutBtn.addEventListener("click", function (e) {
        e.preventDefault();
        logout();
    });

    const sidebarLogout = document.getElementById("sidebarLogout");
    if (sidebarLogout) sidebarLogout.addEventListener("click", function (e) {
        e.preventDefault();
        logout();
    });

    const editProfileBtn = document.getElementById("editProfileBtn");
    if (editProfileBtn) editProfileBtn.addEventListener("click", function () {
        alert("Edit Profile feature will be added next.");
    });

    const changePasswordBtn = document.getElementById("changePasswordBtn");
    if (changePasswordBtn) changePasswordBtn.addEventListener("click", function () {
        alert("Change Password feature will be added next.");
    });
});
