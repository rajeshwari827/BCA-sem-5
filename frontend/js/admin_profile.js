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
    .addEventListener("click", function () {

        const confirmLogout = confirm(
            "Are you sure you want to logout?"
        );


        if (!confirmLogout) {
            return;
        }


        alert("Logged out successfully.");


        window.location.href = "login.html";

    });


// Dashboard Summary
function loadSummary() {

    // Sample values
    const totalUsers = 25;

    const totalDonors = 15;

    const totalNGOs = 10;

    const totalDonations = 35;


    document.getElementById("totalUsers").textContent =
        totalUsers;


    document.getElementById("totalDonors").textContent =
        totalDonors;


    document.getElementById("totalNGOs").textContent =
        totalNGOs;


    document.getElementById("totalDonations").textContent =
        totalDonations;

}


// Load Page
displayProfile();

loadSummary();
