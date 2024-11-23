document.addEventListener('DOMContentLoaded', function () {
    console.log("Dynamic script loaded"); // Check if script is loaded
    
    const actionButtons = document.querySelectorAll('[data-url]');
    console.log("Found buttons:", actionButtons); // Check if buttons are detected

    actionButtons.forEach(button => {
        button.addEventListener('click', (event) => {
            event.preventDefault();
            console.log("Button clicked:", button); // Check if click is detected

            const actionUrl = button.dataset.url;
            console.log("Action URL:", actionUrl); // Check if URL is correct

            // Perform AJAX request
            fetch(actionUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Accept': 'application/json',
                },
            })
                .then(response => response.json())
                .then(data => {
                    console.log("Response Data:", data); // Log server response

                    if (data.status === 'success') {
                        Swal.fire({
                            title: 'Success!',
                            text: data.message,
                            icon: 'success',
                            timer: 2000,
                            showConfirmButton: false
                        }).then(() => {
                            if (data.redirect_url) {
                                window.location.href = data.redirect_url;
                            }
                        });
                    } else if (data.status === 'info') {
                        Swal.fire({
                            title: 'Info!',
                            text: data.message,
                            icon: 'info',
                            confirmButtonColor: '#3085d6',
                        });
                    } else {
                        Swal.fire({
                            title: 'Error!',
                            text: data.message || 'An error occurred.',
                            icon: 'error',
                            confirmButtonColor: '#3085d6',
                        });
                    }
                })
                .catch(error => {
                    console.error("Error:", error); // Log any fetch errors
                    Swal.fire({
                        title: 'Error!',
                        text: 'An error occurred while processing your request.',
                        icon: 'error',
                        confirmButtonColor: '#3085d6',
                    });
                });
        });
    });

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
