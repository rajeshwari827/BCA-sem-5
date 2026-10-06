document.addEventListener("DOMContentLoaded", function () {
    const role = localStorage.getItem("user_role") || sessionStorage.getItem("user_role");
    const token = localStorage.getItem("token") || localStorage.getItem("session_token") ||
        sessionStorage.getItem("token") || sessionStorage.getItem("session_token");
    const userId = localStorage.getItem("user_id") || sessionStorage.getItem("user_id");
    const form = document.getElementById("feedbackForm");
    const status = document.getElementById("feedbackStatus");
    const backLink = document.getElementById("backLink");

    if (role === "donor") backLink.href = "donor/donor_dashboard.html";
    if (role === "receiver") backLink.href = "receiver/receiver_dashboard.html";
    if (!token || !userId || !["donor", "receiver"].includes(role)) {
        status.textContent = "Please sign in as a donor or NGO to submit feedback.";
        status.classList.add("error");
        form.querySelector("button").disabled = true;
        return;
    }

    form.addEventListener("submit", async function (event) {
        event.preventDefault();
        const button = form.querySelector("button");
        status.textContent = "Submitting…";
        status.classList.remove("error");
        button.disabled = true;
        try {
            const response = await fetch("/api/feedback", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + token
                },
                body: JSON.stringify({
                    rating: document.getElementById("rating").value,
                    message: document.getElementById("message").value
                })
            });
            const result = await response.json();
            if (!response.ok || !result.success) throw new Error(result.message || "Feedback could not be submitted.");
            form.reset();
            status.textContent = result.message || "Thanks! Your feedback was submitted.";
        } catch (error) {
            status.textContent = error.message;
            status.classList.add("error");
        } finally {
            button.disabled = false;
        }
    });
});
