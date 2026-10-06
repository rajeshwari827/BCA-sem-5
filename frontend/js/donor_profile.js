let currentDonorProfile = null;

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

        currentDonorProfile = result.donor || {};
        renderDonorProfile(currentDonorProfile, donorId);

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

    const editForm = document.getElementById("editProfileForm");
    const passwordForm = document.getElementById("changePasswordForm");
    const status = document.getElementById("profileActionStatus");

    document.getElementById("editProfileBtn").addEventListener("click", function () {
        const profile = currentDonorProfile || {};
        document.getElementById("editRestaurantName").value = profile.resturaent_name || "";
        document.getElementById("editOwnerName").value = profile.owner_name || "";
        document.getElementById("editEmail").value = profile.email || "";
        document.getElementById("editPhone").value = profile.phone || "";
        document.getElementById("editAddress").value = profile.address || "";
        document.getElementById("editCity").value = profile.city || "";
        document.getElementById("editLocation").value = profile.location || "";
        passwordForm.hidden = true;
        editForm.hidden = false;
        status.textContent = "";
    });

    document.getElementById("cancelEditProfile").addEventListener("click", function () {
        editForm.hidden = true;
    });

    document.getElementById("changePasswordBtn").addEventListener("click", function () {
        editForm.hidden = true;
        passwordForm.reset();
        passwordForm.hidden = false;
        status.textContent = "";
    });

    document.getElementById("cancelChangePassword").addEventListener("click", function () {
        passwordForm.hidden = true;
    });

    editForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        const button = editForm.querySelector("button[type='submit']");
        button.disabled = true;
        status.classList.remove("error");
        status.textContent = "Saving profile…";
        try {
            const payload = {
                restaurant_name: document.getElementById("editRestaurantName").value.trim(),
                owner_name: document.getElementById("editOwnerName").value.trim(),
                email: document.getElementById("editEmail").value.trim(),
                phone: document.getElementById("editPhone").value.trim(),
                address: document.getElementById("editAddress").value.trim(),
                city: document.getElementById("editCity").value.trim(),
                location: document.getElementById("editLocation").value.trim()
            };
            const response = await fetch("/api/donor/profile/update", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": "Bearer " + token },
                body: JSON.stringify(payload)
            });
            const result = await response.json();
            if (!response.ok || !result.success) throw new Error(result.message || "Unable to save profile.");
            currentDonorProfile = {
                ...currentDonorProfile,
                resturaent_name: payload.restaurant_name,
                owner_name: payload.owner_name,
                email: payload.email,
                phone: payload.phone,
                address: payload.address,
                city: payload.city,
                location: payload.location
            };
            renderDonorProfile(currentDonorProfile, donorId);
            editForm.hidden = true;
            status.textContent = result.message;
        } catch (error) {
            status.textContent = error.message;
            status.classList.add("error");
        } finally {
            button.disabled = false;
        }
    });

    passwordForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        const currentPassword = document.getElementById("currentPassword").value;
        const newPassword = document.getElementById("newPassword").value;
        const confirmPassword = document.getElementById("confirmNewPassword").value;
        if (newPassword !== confirmPassword) {
            status.textContent = "New password and confirmation do not match.";
            status.classList.add("error");
            return;
        }
        const button = passwordForm.querySelector("button[type='submit']");
        button.disabled = true;
        status.classList.remove("error");
        status.textContent = "Updating password…";
        try {
            const response = await fetch("/api/donor/password", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": "Bearer " + token },
                body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
            });
            const result = await response.json();
            if (!response.ok || !result.success) throw new Error(result.message || "Unable to change password.");
            passwordForm.reset();
            passwordForm.hidden = true;
            status.textContent = result.message;
        } catch (error) {
            status.textContent = error.message;
            status.classList.add("error");
        } finally {
            button.disabled = false;
        }
    });
});

function renderDonorProfile(donor, donorId) {
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
}
