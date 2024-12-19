document.addEventListener('DOMContentLoaded', () => {
    const csrftoken = getCookie('csrftoken');

    document.querySelectorAll('.plus, .minus').forEach(button => {
        button.addEventListener('click', function () {
            const itemId = this.dataset.id;
            const isPlus = this.classList.contains('plus');
            const inputField = document.querySelector(`input[data-id="${itemId}"]`);
            const errorMessage = document.querySelector(`#error-message-${itemId}`);
            const itemTotalField = document.querySelector(`#item-total-${itemId}`);
            const grandTotalField = document.querySelector('#grand-total'); // Assuming you have this

            if (inputField) {
                let currentQuantity = parseInt(inputField.value);
                const newQuantity = isPlus ? currentQuantity + 1 : currentQuantity - 1;

                if (newQuantity < 1) {
                    errorMessage.classList.remove('hidden');
                    return;
                } else {
                    errorMessage.classList.add('hidden');
                }

                // Send AJAX request to update quantity
                fetch(`/cart/update/${itemId}/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrftoken
                    },
                    body: JSON.stringify({ quantity: newQuantity })
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.error) {
                            errorMessage.textContent = data.error;
                            errorMessage.classList.remove('hidden');
                        } else {
                            // Update UI
                            inputField.value = data.current_quantity;
                            itemTotalField.textContent = `₹${data.item_total.toFixed(2)}`;
                            if (grandTotalField) {
                                grandTotalField.textContent = `₹${data.grand_total.toFixed(2)}`;
                            }
                        }
                    })
                    .catch(error => {
                        console.error('Error updating cart:', error);
                    });
            }
        });
    });
});
