document.addEventListener("DOMContentLoaded", async function () {
    const token = localStorage.getItem("token") ||
        localStorage.getItem("session_token") ||
        sessionStorage.getItem("token") ||
        sessionStorage.getItem("session_token");

    if (!token) {
        alert("Please log in as a receiver to view your profile.");
        window.location.replace("../login.html");
        return;
    }

    try {
        const response = await fetch("/api/receiver/profile", {
            headers: {
                "Authorization": "Bearer " + token,
                "Accept": "application/json"
            },
            cache: "no-store"
        });
        const result = await response.json();

        if (response.status === 401 || response.status === 403) {
            alert("Your receiver session has expired. Please log in again.");
            window.location.replace("../login.html");
            return;
        }
        if (!response.ok || !result.success || !result.receiver) {
            throw new Error(result.message || "Unable to load receiver profile.");
        }

        const receiver = result.receiver;
        localStorage.setItem("user_id", receiver.ngo_id);
        localStorage.setItem("user_role", "receiver");

        const values = {
            organizationName: receiver.organization_name,
            receiverId: receiver.ngo_id,
            representativeName: receiver.representative_name,
            email: receiver.email,
            phone: receiver.phone,
            address: receiver.address,
            city: receiver.city,
            organizationType: receiver.organization_type,
            location: receiver.location,
            createdAt: receiver.created_at
                ? new Date(receiver.created_at).toLocaleDateString("en-IN")
                : "-"
        };
        Object.entries(values).forEach(function ([id, value]) {
            const element = document.getElementById(id);
            if (element) element.textContent = value || "-";
        });
        document.getElementById("profileMessage").textContent =
            "Your details from your logged-in receiver account.";
    } catch (error) {
        console.error("Receiver profile error:", error);
        document.getElementById("profileMessage").textContent = error.message;
    }

    const logoutBtn = document.getElementById("logoutBtn");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", async function (event) {
            event.preventDefault();
            try {
                await fetch("/api/logout", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + token
                    },
                    body: "{}",
                    keepalive: true
                });
            } catch (error) {
                console.error("Receiver logout error:", error);
            }
            ["user_id", "user_role", "token", "session_token"].forEach(function (key) {
                localStorage.removeItem(key);
                sessionStorage.removeItem(key);
            });
            window.location.replace("../login.html");
        });
    }
});
