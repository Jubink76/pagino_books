document.addEventListener('DOMContentLoaded', function () {
    const forms = document.querySelectorAll('form');

    forms.forEach(form => {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const button = form.querySelector('button[data-url]');
            const formData = new FormData(form);

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
                
                Swal.fire({
                    title: data.status === 'success' ? 'Success!' : 'Error!',
                    text: data.message,
                    icon: data.status,
                    timer: data.status === 'success' ? 2000 : null,
                    showConfirmButton: data.status !== 'success'
                }).then(() => {
                    if (data.redirect_url && data.status === 'success') {
                        window.location.href = data.redirect_url;
                    }
                });
            } catch (error) {
                Swal.fire({
                    title: 'Error!',
                    text: 'An error occurred.',
                    icon: 'error'
                });
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