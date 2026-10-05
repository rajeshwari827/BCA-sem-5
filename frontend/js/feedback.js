// Feedback JavaScript

let feedbackList = [
    {
        id: 1,
        name: "Rahul Restaurant",
        role: "Donor",
        rating: 5,
        feedback: "The food donation process is very easy and useful.",
        date: "05/10/2026"
    },

    {
        id: 2,
        name: "Helping Hands NGO",
        role: "NGO",
        rating: 4,
        feedback: "It is easy to find and accept available food donations.",
        date: "05/10/2026"
    },

    {
        id: 3,
        name: "Shree Food Center",
        role: "Donor",
        rating: 5,
        feedback: "HungerFree helps us donate extra food instead of wasting it.",
        date: "04/10/2026"
    }
];


// Display Feedback
function displayFeedback(list) {

    const tableBody = document.getElementById("feedbackTableBody");

    tableBody.innerHTML = "";

    if (list.length === 0) {

        tableBody.innerHTML =
            "<tr>" +
            "<td colspan='7'>No feedback available.</td>" +
            "</tr>";

        return;
    }


    list.forEach(function (feedback) {

        const row = document.createElement("tr");


        // Feedback ID
        const idCell = document.createElement("td");
        idCell.textContent = feedback.id;
        row.appendChild(idCell);


        // User Name
        const nameCell = document.createElement("td");
        nameCell.textContent = feedback.name;
        row.appendChild(nameCell);


        // Role
        const roleCell = document.createElement("td");
        roleCell.textContent = feedback.role;
        row.appendChild(roleCell);


        // Rating
        const ratingCell = document.createElement("td");
        ratingCell.textContent = feedback.rating + " ★";
        row.appendChild(ratingCell);


        // Feedback
        const feedbackCell = document.createElement("td");
        feedbackCell.textContent = feedback.feedback;
        row.appendChild(feedbackCell);


        // Date
        const dateCell = document.createElement("td");
        dateCell.textContent = feedback.date;
        row.appendChild(dateCell);


        // Action
        const actionCell = document.createElement("td");

        const deleteButton = document.createElement("button");

        deleteButton.textContent = "Delete";

        deleteButton.type = "button";

        deleteButton.onclick = function () {
            deleteFeedback(feedback.id);
        };

        actionCell.appendChild(deleteButton);

        row.appendChild(actionCell);


        tableBody.appendChild(row);

    });

}


// Search Feedback
function searchFeedback() {

    const searchText =
        document.getElementById("searchFeedback")
            .value
            .toLowerCase()
            .trim();


    const selectedRole =
        document.getElementById("roleFilter").value;


    const filteredFeedback = feedbackList.filter(function (feedback) {

        const nameMatch =
            feedback.name
                .toLowerCase()
                .includes(searchText);


        const roleMatch =
            selectedRole === "" ||
            feedback.role === selectedRole;


        return nameMatch && roleMatch;

    });


    displayFeedback(filteredFeedback);

}


// Search Button
document.getElementById("searchBtn").addEventListener(
    "click",
    searchFeedback
);


// Role Filter
document.getElementById("roleFilter").addEventListener(
    "change",
    searchFeedback
);


// Search while typing
document.getElementById("searchFeedback").addEventListener(
    "input",
    searchFeedback
);


// Delete Feedback
function deleteFeedback(id) {

    const confirmDelete = confirm(
        "Are you sure you want to delete this feedback?"
    );


    if (!confirmDelete) {
        return;
    }


    feedbackList = feedbackList.filter(function (feedback) {

        return feedback.id !== id;

    });


    displayFeedback(feedbackList);

    updateSummary();

}


// Update Summary
function updateSummary() {

    // Total Feedback
    document.getElementById("totalFeedback").textContent =
        feedbackList.length;


    // Donor Feedback
    let donorCount = 0;

    feedbackList.forEach(function (feedback) {

        if (feedback.role === "Donor") {
            donorCount++;
        }

    });


    document.getElementById("donorFeedback").textContent =
        donorCount;


    // NGO Feedback
    let ngoCount = 0;

    feedbackList.forEach(function (feedback) {

        if (feedback.role === "NGO") {
            ngoCount++;
        }

    });


    document.getElementById("ngoFeedback").textContent =
        ngoCount;


    // Average Rating
    if (feedbackList.length === 0) {

        document.getElementById("averageRating").textContent =
            "0 ★";

        return;

    }


    let totalRating = 0;

    feedbackList.forEach(function (feedback) {

        totalRating += feedback.rating;

    });


    const averageRating =
        totalRating / feedbackList.length;


    document.getElementById("averageRating").textContent =
        averageRating.toFixed(1) + " ★";

}


// Initial Display
displayFeedback(feedbackList);

updateSummary();
