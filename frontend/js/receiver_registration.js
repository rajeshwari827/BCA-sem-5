document.addEventListener("DOMContentLoaded", function () {

    const receiverForm = document.getElementById("receiverForm");

    receiverForm.addEventListener("submit", async function (e) {

        e.preventDefault();

        const data = {

            organization_name:
                document.getElementById("placeName").value,

            organization_type:
                document.getElementById("placeType").value,

            representative_name:
                document.getElementById("RepresentativeName").value,

            email:
                document.getElementById("Email").value,

            phone:
                document.getElementById("phone").value,

            address:
                document.getElementById("address").value,

            city:
                document.getElementById("city").value,

            password:
                document.getElementById("password").value,

            confirm_password:
                document.getElementById("confirm_password").value,

            location:
                document.getElementById("location").value
        };


        // -----------------------------
        // Check password
        // -----------------------------

        if (data.password !== data.confirm_password) {

            alert("Passwords do not match!");

            return;
        }


        try {

            // -----------------------------
            // Send data to Python backend
            // -----------------------------

            const response = await fetch(
                "/api/receiver/register",
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify(data)
                }
            );


            const result = await response.json();


            // -----------------------------
            // Show message
            // -----------------------------

            if (result.success) {

                alert(
                    "Registration Successful!\n\n" +
                    "Your Receiver ID is: " +
                    result.receiver_id
                );


                // -----------------------------
                // Go to login page
                // -----------------------------

                window.location.href = "login.html";

            } else {

                alert(
                    "Registration Failed:\n" +
                    result.message
                );
            }

        }

        catch (error) {

            console.error(error);

            alert(
                "Cannot connect to the server.\n\n" +
                "Please make sure the Python backend is running."
            );
        }

    });

});