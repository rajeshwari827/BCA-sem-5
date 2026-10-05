document.addEventListener("DOMContentLoaded", function () {

    const donationForm = document.getElementById("donationForm");

    if (!donationForm) {
        console.error("Donation form not found.");
        return;
    }

    donationForm.addEventListener("submit", async function (event) {

        event.preventDefault();

        console.log("DONATION FORM SUBMITTED");

        const donorId = localStorage.getItem("user_id");

        console.log("Donor ID:", donorId);

        if (!donorId) {
            alert("Donor login session not found. Please login again.");
            window.location.href = "../login.html";
            return;
        }

        const foodName =
            document.getElementById("foodName").value.trim();

        const foodCategory =
            document.getElementById("foodCategory").value;

        const quantity =
            document.getElementById("quantity").value.trim();

        const cookingDate =
            document.getElementById("cookingDate").value;

        const expiryTime =
            document.getElementById("expiryTime").value;


        // =========================
        // VALIDATION
        // =========================

        if (!foodName) {
            alert("Please enter food name.");
            return;
        }

        if (!foodCategory) {
            alert("Please select food category.");
            return;
        }

        if (!quantity) {
            alert("Please enter quantity.");
            return;
        }

        if (!cookingDate) {
            alert("Please select cooking date.");
            return;
        }

        if (!expiryTime) {
            alert("Please select expiry time.");
            return;
        }


        // =========================
        // DONATION DATA
        // =========================

        const donationData = {

            donor_id: donorId,

            food_name: foodName,

            food_category: foodCategory,

            quantity: quantity,

            cooking_date: cookingDate,

            expiry_time: expiryTime

        };


        console.log(
            "Sending donation:",
            donationData
        );


        // =========================
        // SEND TO PYTHON BACKEND
        // =========================

        try {

            const response = await fetch(
                "/api/donor/donate",
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify(donationData)
                }
            );


            console.log(
                "Server response status:",
                response.status
            );


            const result = await response.json();


            console.log(
                "Server response:",
                result
            );


            // =========================
            // SUCCESS
            // =========================

            if (result.success) {

                alert(
                    "Food donation submitted successfully."
                );

                donationForm.reset();

                window.location.href =
                    "donation_history.html";

            }


            // =========================
            // ERROR FROM BACKEND
            // =========================

            else {

                alert(
                    result.message ||
                    "Unable to submit food donation."
                );

            }

        }


        // =========================
        // CONNECTION ERROR
        // =========================

        catch (error) {

            console.error(
                "DONATION ERROR:",
                error
            );

            alert(
                "Cannot connect to server. Please make sure app.py is running."
            );

        }

    });

});