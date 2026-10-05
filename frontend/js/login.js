document.addEventListener("DOMContentLoaded", function () {

    const loginForm = document.getElementById("loginForm");

    if (!loginForm) {
        console.error("Login form not found.");
        return;
    }

    loginForm.addEventListener("submit", async function (e) {

        e.preventDefault();

        const useridInput = document.getElementById("userid");
        const usernameInput = document.getElementById("username");
        const passwordInput = document.getElementById("password");
        const emailInput = document.getElementById("email");

        const userid = useridInput.value.trim().toUpperCase();
        const username = usernameInput.value.trim();
        const password = passwordInput.value.trim();
        const email = emailInput.value.trim();


        // ==========================================
        // VALIDATION
        // ==========================================

        if (!userid || !username || !password || !email) {

            alert("Please enter User ID, User Name, Password, and Email.");

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
                    username: username,
                    password: password,
                    email: email

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

            if (!result.token || !result.role || !result.user_id) {
                throw new Error("Login response is missing session information.");
            }

            localStorage.setItem("user_id", result.user_id);
            localStorage.setItem("user_role", result.role);
            localStorage.setItem("token", result.token);
            localStorage.setItem("session_token", result.token);
            sessionStorage.setItem("user_id", result.user_id);
            sessionStorage.setItem("user_role", result.role);
            sessionStorage.setItem("token", result.token);


            console.log(
                "Logged in user:",
                localStorage.getItem("user_id")
            );


            // ==========================================
            // REDIRECT
            // ==========================================

            if (result.role === "donor") {

                window.location.href =
                    "donor/donor_dashboard.html";

            }

            else if (result.role === "receiver") {

                window.location.href =
                    "receiver/receiver_dashboard.html";

            }

            else if (result.role === "admin") {

                window.location.href =
                    "admin/admin_dashboard.html";

            }
            else {

                localStorage.removeItem("token");
                localStorage.removeItem("user_role");
                localStorage.removeItem("user_id");

                alert(
                    "Login successful, but the account role is not recognized."
                );

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
