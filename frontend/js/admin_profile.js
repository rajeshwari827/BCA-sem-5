// Admin Profile JavaScript


// Admin Profile Data
let adminProfile = {

    id: "ADM001",

    username: "admin",

    email: "admin@hungerfree.com",

    role: "System Administrator",

    joiningDate: "15/06/2026",

    lastLogin: "05/10/2026"

};


// Display Admin Profile
function displayProfile() {

    document.getElementById("adminId").textContent =
        adminProfile.id;


    document.getElementById("adminUsername").textContent =
        adminProfile.username;


    document.getElementById("adminEmail").textContent =
        adminProfile.email;


    document.getElementById("adminRole").textContent =
        adminProfile.role;


    document.getElementById("joiningDate").textContent =
        adminProfile.joiningDate;


    document.getElementById("lastLogin").textContent =
        adminProfile.lastLogin;

}


// Edit Profile
document.getElementById("editProfileBtn")
    .addEventListener("click", function () {

        const newUsername = prompt(
            "Enter new username:",
            adminProfile.username
        );


        if (newUsername === null) {
            return;
        }


        if (newUsername.trim() === "") {

            alert("Username cannot be empty.");

            return;
        }


        const newEmail = prompt(
            "Enter new email:",
            adminProfile.email
        );


        if (newEmail === null) {
            return;
        }


        if (newEmail.trim() === "") {

            alert("Email cannot be empty.");

            return;
        }


        adminProfile.username =
            newUsername.trim();


        adminProfile.email =
            newEmail.trim();


        displayProfile();


        alert("Profile updated successfully.");

    });


// Change Password
document.getElementById("changePasswordBtn")
    .addEventListener("click", function () {

        const currentPassword = prompt(
            "Enter current password:"
        );


        if (currentPassword === null) {
            return;
        }


        if (currentPassword === "") {

            alert("Please enter your current password.");

            return;
        }


        const newPassword = prompt(
            "Enter new password:"
        );


        if (newPassword === null) {
            return;
        }


        if (newPassword.length < 6) {

            alert(
                "New password must contain at least 6 characters."
            );

            return;
        }


        const confirmPassword = prompt(
            "Confirm new password:"
        );


        if (confirmPassword === null) {
            return;
        }


        if (newPassword !== confirmPassword) {

            alert(
                "New password and confirm password do not match."
            );

            return;
        }


        alert("Password changed successfully.");

    });


// Logout
document.getElementById("logoutBtn")
    .addEventListener("click", async function () {

        const confirmLogout = confirm(
            "Are you sure you want to logout?"
        );


        if (!confirmLogout) {
            return;
        }


        try {
            await fetch("/api/logout", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: "{}"
            });
        } catch (error) {
            console.error("Admin logout error:", error);
        }

        ["user_id", "user_role", "token", "session_token"].forEach(function (key) {
            localStorage.removeItem(key);
            sessionStorage.removeItem(key);
        });
        alert("Logged out successfully.");
        window.location.href = "/login.html";

    });


// Load the summary from the same database-backed endpoint as the dashboard.
async function loadSummary() {
    const token = sessionStorage.getItem("token") ||
        localStorage.getItem("token") ||
        localStorage.getItem("session_token");
    const headers = token ? { "Authorization": "Bearer " + token } : {};

    try {
        const response = await fetch("/api/admin/dashboard", {
            headers: headers,
            cache: "no-store"
        });
        const result = await response.json();
        if (!response.ok || !result.success) {
            throw new Error(result.message || "Unable to load profile totals.");
        }

        const donors = Number(result.total_donors) || 0;
        const ngos = Number(result.total_receivers ?? result.total_ngos) || 0;
        document.getElementById("totalUsers").textContent = donors + ngos;
        document.getElementById("totalDonors").textContent = donors;
        document.getElementById("totalNGOs").textContent = ngos;
        document.getElementById("totalDonations").textContent =
            Number(result.total_donations) || 0;
    } catch (error) {
        console.error("Admin profile summary error:", error);
        const status = document.getElementById("profileSummaryStatus");
        if (status) status.textContent = "Could not load live totals. Refresh the page after signing in again.";
    }
}


// Load Page
displayProfile();

loadSummary();
