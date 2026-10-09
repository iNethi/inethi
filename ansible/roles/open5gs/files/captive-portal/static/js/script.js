document.getElementById("loginBtn").addEventListener("click", function() {
    // Redirect to actual login endpoint
    window.location.href = "/login";
});

// Optional: auto-redirect after delay (typical captive portal behavior)
setTimeout(() => {
    console.log("Still waiting for user interaction...");
}, 5000);
