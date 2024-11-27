document.addEventListener('DOMContentLoaded', function () {
    const submitButtons = document.querySelectorAll('button[type="submit"][data-url]');

    submitButtons.forEach(button => {
        button.addEventListener('click', (event) => {
            event.preventDefault(); // Prevent default form submission

            const form = button.closest('form'); // Find the parent form
            const actionUrl = button.dataset.url;

            // Use FormData to collect all form fields
            const formData = new FormData(form);

            // Perform AJAX request
            fetch(actionUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Accept': 'application/json',
                },
                body: formData // Send form data
            })
                .then(response => response.json())
                .then(data => {
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
                    console.error("Error:", error);
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