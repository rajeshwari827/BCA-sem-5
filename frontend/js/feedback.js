document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("searchBtn").addEventListener("click", renderFeedback);
    document.getElementById("searchFeedback").addEventListener("input", renderFeedback);
    document.getElementById("roleFilter").addEventListener("change", renderFeedback);
    loadFeedback();
});

let feedbackList = [];

async function loadFeedback() {
    try {
        const response = await fetch("/api/admin/feedback", { cache: "no-store" });
        const result = await response.json();
        if (!response.ok || !result.success) {
            throw new Error(result.message || "Unable to load feedback.");
        }
        feedbackList = result.feedback || [];
        updateSummary();
        renderFeedback();
    } catch (error) {
        console.error("Feedback load error:", error);
        document.getElementById("feedbackTableBody").innerHTML =
            `<tr><td colspan="7">${error.message}</td></tr>`;
    }
}

function renderFeedback() {
    const query = document.getElementById("searchFeedback").value.trim().toLowerCase();
    const role = document.getElementById("roleFilter").value;
    const entries = feedbackList.filter(item =>
        (!role || item.role === role) &&
        (!query || [item.name, item.user_id, item.feedback].some(value =>
            String(value || "").toLowerCase().includes(query)))
    );
    const body = document.getElementById("feedbackTableBody");
    body.replaceChildren();
    if (!entries.length) {
        body.innerHTML = "<tr><td colspan='7'>No feedback submitted yet.</td></tr>";
        return;
    }
    entries.forEach(item => {
        const row = body.insertRow();
        [item.id, item.name, item.role, `${item.rating} ★`, item.feedback,
            item.date ? new Date(item.date).toLocaleString() : "-"]
            .forEach(value => { row.insertCell().textContent = value ?? "-"; });
        const action = row.insertCell();
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = "Delete";
        button.addEventListener("click", () => deleteFeedback(item.id));
        action.appendChild(button);
    });
}

function updateSummary() {
    document.getElementById("totalFeedback").textContent = feedbackList.length;
    document.getElementById("donorFeedback").textContent =
        feedbackList.filter(item => item.role === "Donor").length;
    document.getElementById("ngoFeedback").textContent =
        feedbackList.filter(item => item.role === "NGO").length;
    const average = feedbackList.length
        ? feedbackList.reduce((sum, item) => sum + Number(item.rating || 0), 0) / feedbackList.length
        : 0;
    document.getElementById("averageRating").textContent = `${average.toFixed(1)} ★`;
}

async function deleteFeedback(id) {
    if (!confirm("Delete this feedback record?")) return;
    try {
        const response = await fetch("/api/admin/feedback/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ feedback_id: id })
        });
        const result = await response.json();
        if (!response.ok || !result.success) throw new Error(result.message || "Unable to delete feedback.");
        await loadFeedback();
    } catch (error) {
        alert(error.message);
    }
}
