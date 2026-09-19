document.addEventListener("DOMContentLoaded", function () {

    const donationForm = document.getElementById("donationForm");

    if (!donationForm) {
        console.error("Donation form not found.");
        return;
    }

    donationForm.addEventListener("submit", async function (e) {

        e.preventDefault();

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

        // Get form values
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

        const additionalNotes =
            document.getElementById("additionalNotes").value.trim();

        const imageInput =
            document.getElementById("foodImage");


        // Validate category
        if (!foodCategory) {
            alert("Please select a food category.");
            document.getElementById("foodCategory").focus();
            return;
        }


        // Convert image to Base64
        let foodImage = "";

        if (imageInput.files.length > 0) {

            const file = imageInput.files[0];

            foodImage = await new Promise(function (resolve, reject) {

                const reader = new FileReader();

                reader.onload = function () {
                    resolve(reader.result);
                };

                reader.onerror = function () {
                    reject(new Error("Unable to read image."));
                };

                reader.readAsDataURL(file);
            });
        }


        // Data sent to Python backend
        const donationData = {

            donor_id: donorId,

            food_name: foodName,

            food_category: foodCategory,

            quantity: quantity,

            cooking_date: cookingDate,

            expiry_time: expiryTime,

            // Your current form does not have a contact number field.
            // Send donor phone through backend if required.
            contact_number: "",

            description: additionalNotes,

            food_image: foodImage
        };


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


            const result = await response.json();


            if (result.success) {

                alert("Food donation submitted successfully.");

                donationForm.reset();

                // Go directly to donation history
                window.location.href =
                    "donation_history.html";

            } else {

                alert(
                    result.message ||
                    "Unable to submit food donation."
                );
            }


        } catch (error) {

            console.error(
                "Donation Error:",
                error
            );

            alert(
                "Cannot connect to the server. " +
                "Please make sure the Python backend is running."
            );
        }

    });

});