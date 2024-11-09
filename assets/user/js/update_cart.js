document.addEventListener('DOMContentLoaded', function() {
    const plusButtons = document.querySelectorAll('.arrow.plus');
    const minusButtons = document.querySelectorAll('.arrow.minus');

    function updateCartQuantity(itemId, newQuantity) {
        fetch(`/update_cart_quantity/${itemId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json',
            },
            cache: "no-cache",
            body: JSON.stringify({ quantity: newQuantity })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                // Show error message for 2 seconds
                const errorMessage = document.getElementById(`error-message-${itemId}`);
                errorMessage.textContent = data.error;
                errorMessage.style.display = 'block';
                setTimeout(() => {
                    errorMessage.style.display = 'none';
                }, 2000);
            } else {
                // Update item total and grand total in the UI
                document.querySelector(`.cart-sub-total-price[data-id="${itemId}"]`).textContent = `₹${data.item_total}`;
                document.querySelector('.cart-grand-total .inner-left-md').textContent = `₹${data.grand_total}`;

                // Update quantity display if you have an element for showing it
                const quantityInput = document.querySelector(`.quantity-input[data-id="${itemId}"]`);
                quantityInput.value = newQuantity;

                // Check if quantity reached the max stock
                if (data.error === 'Not enough stock available.') {
                    document.querySelector(`.arrow.plus[data-id="${itemId}"]`).disabled = true;
                }
            }
        })
        .catch(error => console.error('Error:', error));
    }

    // Increment button click event
    plusButtons.forEach(button => {
        button.addEventListener('click', function() {
            const itemId = this.getAttribute('data-id');
            const quantityInput = document.querySelector(`.quantity-input[data-id="${itemId}"]`);
            const currentQuantity = parseInt(quantityInput.value) + 1;
            quantityInput.value = currentQuantity;
            updateCartQuantity(itemId, currentQuantity);
        });
    });

    // Decrement button click event
    minusButtons.forEach(button => {
        button.addEventListener('click', function() {
            const itemId = this.getAttribute('data-id');
            const quantityInput = document.querySelector(`.quantity-input[data-id="${itemId}"]`);
            const currentQuantity = parseInt(quantityInput.value) - 1;

            if (currentQuantity > 0) {
                quantityInput.value = currentQuantity;
                updateCartQuantity(itemId, currentQuantity);
            } else {
                // Show error if trying to set quantity below 1
                const errorMessage = document.getElementById(`error-message-${itemId}`);
                errorMessage.textContent = "Quantity cannot be zero or less.";
                errorMessage.style.display = 'block';
                setTimeout(() => {
                    errorMessage.style.display = 'none';
                }, 2000);
            }
        });
    });
});
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
