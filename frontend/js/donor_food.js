document.addEventListener("DOMContentLoaded", function () {

    const form = document.getElementById("donationForm");

    form.addEventListener("submit", async function (event) {

        event.preventDefault();

        const donorId = localStorage.getItem("user_id");

        if (!donorId) {
            alert("Please login first.");
            window.location.href = "../login.html";
            return;
        }

        if (!donorId.toUpperCase().startsWith("DN")) {
            alert("Invalid donor login.");
            window.location.href = "../login.html";
            return;
        }

        const foodName = document.getElementById("foodName").value.trim();
        const quantity = document.getElementById("quantity").value.trim();
        const cookingDate = document.getElementById("cookingDate").value;
        const expiryTime = document.getElementById("expiryTime").value;
        const additionalNotes = document.getElementById("additionalNotes").value.trim();

        const pickupTime = cookingDate + " " + expiryTime;

        const data = {
            donor_id: donorId,
            food_name: foodName,
            quantity: quantity,
            description: additionalNotes,
            pickup_time: pickupTime
        };

        try {

            const response = await fetch("/api/donor/donate", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (result.success) {

                alert("Food donation submitted successfully!");

                form.reset();

                window.location.href = "donation_history.html";

            } else {

                alert("Donation failed:\n" + result.message);

            }

        } catch (error) {

            console.error("Donation Error:", error);

            alert(
                "Cannot connect to the server.\n\n" +
                "Please make sure the Python backend is running."
            );

        }

    });

});