document.addEventListener('DOMContentLoaded', function () {
    const plusButtons = document.querySelectorAll('.plus');
    const minusButtons = document.querySelectorAll('.minus');

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

    function updateCartQuantity(itemId, newQuantity) {
        fetch(`/update_cart_quantity/${itemId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ quantity: newQuantity }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                const errorMessage = document.getElementById(`error-message-${itemId}`);
                errorMessage.textContent = data.error;
                errorMessage.classList.remove('hidden');
                setTimeout(() => {
                    errorMessage.classList.add('hidden');
                }, 2000);
            } else {
                // Update item total price
                const itemTotalElement = document.getElementById(`item-total-${itemId}`);
                if (itemTotalElement) {
                    itemTotalElement.textContent = `₹${data.item_total.toFixed(2)}`;
                }

                // Update grand total
                const grandTotal = document.querySelector('.text-xl.font-bold.text-gray-900');
                if (grandTotal && data.grand_total) {
                    grandTotal.textContent = `₹${data.grand_total.toFixed(2)}`;
                }

                // Update quantity input
                const quantityInput = document.querySelector(`input[data-id="${itemId}"]`);
                if (quantityInput) {
                    quantityInput.value = data.current_quantity;
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            const errorMessage = document.getElementById(`error-message-${itemId}`);
            errorMessage.textContent = 'An error occurred. Please try again.';
            errorMessage.classList.remove('hidden');
            setTimeout(() => {
                errorMessage.classList.add('hidden');
            }, 2000);
        });
    }

    // Plus button click handler
    plusButtons.forEach(button => {
        button.addEventListener('click', function() {
            console.log('Plus button clicked'); // Debug log
            const itemId = this.getAttribute('data-id');
            const quantityInput = document.querySelector(`input[data-id="${itemId}"]`);
            const currentQuantity = parseInt(quantityInput.value);
            const maxQuantity = parseInt(quantityInput.getAttribute('max'));

            console.log('ItemId:', itemId); // Debug log
            console.log('Current Quantity:', currentQuantity); // Debug log
            console.log('Max Quantity:', maxQuantity); // Debug log

            if (currentQuantity < maxQuantity) {
                updateCartQuantity(itemId, currentQuantity + 1);
            } else {
                const errorMessage = document.getElementById(`error-message-${itemId}`);
                errorMessage.textContent = 'Maximum stock limit reached.';
                errorMessage.classList.remove('hidden');
                setTimeout(() => {
                    errorMessage.classList.add('hidden');
                }, 2000);
            }
        });
    });

    // Minus button click handler
    minusButtons.forEach(button => {
        button.addEventListener('click', function() {
            const itemId = this.getAttribute('data-id');
            const quantityInput = document.querySelector(`input[data-id="${itemId}"]`);
            const currentQuantity = parseInt(quantityInput.value);

            if (currentQuantity > 1) {
                updateCartQuantity(itemId, currentQuantity - 1);
            } else {
                const errorMessage = document.getElementById(`error-message-${itemId}`);
                errorMessage.textContent = 'Quantity cannot be zero or less.';
                errorMessage.classList.remove('hidden');
                setTimeout(() => {
                    errorMessage.classList.add('hidden');
                }, 2000);
            }
        });
    });
});