document.getElementById("loginForm").addEventListener("submit", async function (e) {

    e.preventDefault();

    const data = {

        userid: document.getElementById("userid").value,

        username: document.getElementById("username").value,

        password: document.getElementById("password").value,

        email: document.getElementById("Email:").value

    };

    const response = await fetch("/api/login", {

        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify(data)

    });

    const result = await response.json();

    alert(result.message);

});