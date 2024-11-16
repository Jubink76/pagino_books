document.addEventListener('DOMContentLoaded', function () {
    // Handle Place Order button
    const placeOrderBtn = document.getElementById('placeOrderBtn');
    const selectedAddressInput = document.getElementById('selectedAddress');
    const selectedPaymentInput = document.getElementById('selectedPayment');
    
    placeOrderBtn.addEventListener('click', function (event) {
        const selectedAddress = document.querySelector('input[name="savedAddress"]:checked');
        const selectedPayment = document.querySelector('input[name="payment"]:checked');
        
        if (!selectedAddress || !selectedPayment) {
            alert("Please select a delivery address and payment method.");
            event.preventDefault(); // Prevent form submission
            return;
        }

        // Set selected values into hidden inputs
        selectedAddressInput.value = selectedAddress.value;
        selectedPaymentInput.value = selectedPayment.value;

        // Allow the form to submit
        document.getElementById('placeOrderForm').submit();
    });
});
