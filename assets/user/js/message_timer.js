document.addEventListener('DOMContentLoaded', function() {
    const messageContainer = document.getElementById('message-container');
    if (messageContainer) {
        const alerts = messageContainer.getElementsByClassName('alert');

        // Loop through alerts and set the timer for each
        for (let alert of alerts) {
            let timeoutDuration = 3000; // Default timeout duration

            // Optional: Adjust timeout based on alert type
            if (alert.classList.contains('alert-success')) {
                // Green success alert
                alert.style.backgroundColor = '#d4edda'; // Bootstrap success background color
                alert.style.color = '#155724'; // Bootstrap success text color
            } else if (alert.classList.contains('alert-danger')) {
                // Red error alert
                alert.style.backgroundColor = '#f8d7da'; // Bootstrap danger background color
                alert.style.color = '#721c24'; // Bootstrap danger text color
            }

            // Set a timeout to hide the alert
            setTimeout(function() {
                alert.style.display = 'none';
            }, timeoutDuration);
        }
    }
});