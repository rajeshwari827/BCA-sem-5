document.addEventListener("DOMContentLoaded", function () {

    const loginForm = document.getElementById("loginForm");

    if (!loginForm) {
        console.error("Login form not found.");
        return;
    }

    loginForm.addEventListener("submit", async function (e) {

        e.preventDefault();

        const useridInput = document.getElementById("userid");
        const passwordInput = document.getElementById("password");

        const userid = useridInput.value.trim().toUpperCase();
        const password = passwordInput.value.trim();


        // ==========================================
        // VALIDATION
        // ==========================================

        if (!userid || !password) {

            alert("Please enter User ID and Password.");

            return;
        }


        try {

            const response = await fetch("/api/login", {

                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({

                    userid: userid,
                    password: password

                })

            });


            const result = await response.json();


            // ==========================================
            // LOGIN FAILED
            // ==========================================

            if (!result.success) {

                alert(
                    result.message ||
                    "Invalid User ID or Password."
                );

                return;
            }


            // ==========================================
            // SAVE LOGIN ID
            // ==========================================

            localStorage.setItem(
                "user_id",
                userid
            );


            console.log(
                "Logged in user:",
                localStorage.getItem("user_id")
            );


            // ==========================================
            // REDIRECT
            // ==========================================

            if (userid.startsWith("DN")) {

                window.location.href =
                    "/donor/donor_dashboard.html";

            }

            else if (userid.startsWith("RN")) {

                window.location.href =
                    "/receiver/receiver_dashboard.html";

            }

            else {

                alert("Invalid User ID format.");

            }

        }

        catch (error) {

            console.error(
                "Login Error:",
                error
            );

            alert(
                "Cannot connect to the server.\n\n" +
                "Please make sure the Python backend is running."
            );

        }

    });

});