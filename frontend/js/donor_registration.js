document.getElementById("donorForm").addEventListener("submit", async function (e) {

    e.preventDefault();

    const data = {
        restaurant_name: document.getElementById("restaurant_name").value,
        owner_name: document.getElementById("owner_name").value,
        email: document.getElementById("email").value,
        phone: document.getElementById("phone").value,
        address: document.getElementById("address").value,
        city: document.getElementById("city").value,
        password: document.getElementById("password").value,
        confirm_password: document.getElementById("confirm_password").value,
        location: document.getElementById("location").value
    };

    if (data.password !== data.confirm_password) {
        alert("Passwords do not match!");
        return;
    }

    const response = await fetch("/api/donor/register", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    });

    const result = await response.json();

    alert(result.message);

    if (result.success) {
        alert("Your Donor ID is: " + result.donor_id);
        window.location.href = "login.html";
    }

});