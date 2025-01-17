document.addEventListener('DOMContentLoaded', function () {
    const forms = document.querySelectorAll('form');

    forms.forEach(form => {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const button = form.querySelector('button[data-url]');
            const formData = new FormData(form);
            
            // Disable the submit button to prevent double submission
            if (button) button.disabled = true;

            try {
                const response = await fetch(button.dataset.url, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'Accept': 'application/json',
                    },
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.status === 'login_required') {
                    Swal.fire({
                        title: 'Login Required',
                        text: 'Please login to add items to your cart',
                        icon: 'warning',
                        confirmButtonText: 'Login Now',
                        showCancelButton: true,
                        cancelButtonText: 'Cancel'
                    }).then((result) => {
                        if (result.isConfirmed) {
                            // Store current page URL in session storage before redirecting
                            sessionStorage.setItem('redirectAfterLogin', window.location.href);
                            window.location.href = data.redirect_url;
                        }
                    });
                } else if (data.status === 'success') {
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
                } else {
                    // Handle error cases
                    Swal.fire({
                        title: 'Notice',
                        text: data.message,
                        icon: 'error',
                        confirmButtonText: 'OK'
                    });
                }
            } catch (error) {
                Swal.fire({
                    title: 'Error',
                    text: 'An error occurred while processing your request.',
                    icon: 'error',
                    confirmButtonText: 'OK'
                });
            } finally {
                // Re-enable the submit button
                if (button) button.disabled = false;
            }
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