document.addEventListener("DOMContentLoaded", async function () {

    // Get logged-in user ID
    const donorId = localStorage.getItem("user_id");

    // If nobody is logged in
    if (!donorId) {

        alert("Please login first.");

        window.location.href = "../login.html";

        return;
    }


    // Make sure this is a donor
    if (!donorId.toUpperCase().startsWith("DN")) {

        alert("Invalid donor login.");

        window.location.href = "../login.html";

        return;
    }


    try {

        const response = await fetch(
            "/api/donor/profile?donor_id=" +
            encodeURIComponent(donorId)
        );


        const result = await response.json();


        if (result.success) {

            const donor = result.donor;


            document.getElementById("donor_id").textContent =
                donor.donor_id || "-";


            document.getElementById("restaurant_name").textContent =
                donor.resturaent_name || "-";


            document.getElementById("owner_name").textContent =
                donor.owner_name || "-";


            document.getElementById("email").textContent =
                donor.email || "-";


            document.getElementById("phone").textContent =
                donor.phone || "-";


            document.getElementById("address").textContent =
                donor.address || "-";


            document.getElementById("city").textContent =
                donor.city || "-";


            document.getElementById("location").textContent =
                donor.location || "-";


            if (donor.created_at) {

                const date = new Date(
                    donor.created_at
                );

                document.getElementById(
                    "registration_date"
                ).textContent =
                    date.toLocaleDateString(
                        "en-IN",
                        {
                            day: "2-digit",
                            month: "long",
                            year: "numeric"
                        }
                    );

            }
            else {

                document.getElementById(
                    "registration_date"
                ).textContent = "-";

            }

        }
        else {

            alert(
                "Unable to load profile:\n" +
                result.message
            );

        }

    }
    catch (error) {

        console.error(
            "Profile Error:",
            error
        );

        alert(
            "Cannot connect to the server.\n\n" +
            "Please make sure the Python backend is running."
        );

    }


    // =====================================================
    // LOGOUT
    // =====================================================

    document.getElementById(
        "logoutBtn"
    ).addEventListener(
        "click",
        function () {

            localStorage.removeItem("user_id");

            window.location.href =
                "../login.html";

        }
    );


    document.getElementById(
        "sidebarLogout"
    ).addEventListener(
        "click",
        function (e) {

            e.preventDefault();

            localStorage.removeItem("user_id");

            window.location.href =
                "../login.html";

        }
    );


    // =====================================================
    // BUTTONS - TEMPORARY
    // =====================================================

    document.getElementById(
        "editProfileBtn"
    ).addEventListener(
        "click",
        function () {

            alert(
                "Edit Profile feature will be added next."
            );

        }
    );


    document.getElementById(
        "changePasswordBtn"
    ).addEventListener(
        "click",
        function () {

            alert(
                "Change Password feature will be added next."
            );

        }
    );

});