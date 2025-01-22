document.addEventListener('DOMContentLoaded', function () {
    const savedAddressItems = document.querySelectorAll('.saved-address-item');
    const currentDeliveryAddress = document.getElementById('currentDeliveryAddress');
    const changeAddressLink = document.getElementById('changeAddressLink');
    const paymentMethodInputs = document.querySelectorAll('input[name="payment"]');
    const placeOrderButton = document.getElementById('place-order-button');
    const orderForm = document.getElementById('orderForm');
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    // Function to show alerts (using SweetAlert2)
    function showAlert(type, message) {
        Swal.fire({
            icon: type,
            title: type === 'success' ? 'Success!' : 'Oops...',
            text: message,
            confirmButtonColor: type === 'success' ? '#10B981' : '#EF4444',
        });
    }
    function showLoadingAlert(message = 'Processing your order...') {
        return Swal.fire({
            title: message,
            allowOutsideClick: false,
            showConfirmButton: false,
            willOpen: () => {
                Swal.showLoading();
            }
        });
    }

    function resetOrderButton() {
        if (placeOrderButton) {
            placeOrderButton.disabled = false;
            placeOrderButton.innerHTML = 'Place Order <i class="fas fa-arrow-right ml-2"></i>';
        }
    }


    // Function to check if all requirements are met
    function checkOrderEligibility() {
        const paymentMethodSelected = document.querySelector('input[name="payment"]:checked');
        const addressSelected = currentDeliveryAddress?.getAttribute('data-address-id');
        
        if (placeOrderButton) {
            placeOrderButton.disabled = !paymentMethodSelected || !addressSelected;

            if (!placeOrderButton.disabled) {
                placeOrderButton.classList.remove('bg-gray-400');
                placeOrderButton.classList.add('bg-yellow-500', 'hover:bg-yellow-600');
            } else {
                placeOrderButton.classList.add('bg-gray-400');
                placeOrderButton.classList.remove('bg-yellow-500', 'hover:bg-yellow-600');
            }
        }
    }

    // Payment Processing Functions
    async function processRazorpayPayment(orderData, addressId) {
        console.log('Initializing Razorpay payment:', orderData);
        
        const options = {
            key: orderData.razorpay_key,
            amount: orderData.amount,
            currency: orderData.currency,
            name: orderData.store_name || "BookStore",
            description: "Order Payment",
            order_id: orderData.razorpay_order_id,
            prefill: {
                name: orderData.customer_name,
                email: orderData.email,
                contact: orderData.phone
            },
            theme: {
                color: "#3399cc"
            },
            handler: async function(response) {
                try {
                    await showLoadingAlert('Verifying payment...');
                    const formData = new FormData();
                    formData.append('savedAddress', addressId);
                    formData.append('payment', 'ONLINE');
                    formData.append('razorpay_payment_id', response.razorpay_payment_id);
                    formData.append('razorpay_order_id', response.razorpay_order_id);
                    formData.append('razorpay_signature', response.razorpay_signature);
            
                    const verificationResponse = await fetch(orderForm.getAttribute('data-url'), {
                        method: 'POST',
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest',
                            'X-CSRFToken': csrfToken
                        },
                        body: formData
                    });
            
                    const result = await verificationResponse.json();
                    console.log('Verification response:', result); // Add logging
            
                    if (result.status === 'success') {
                        await showAlert('success', 'Payment successful! Redirecting...');
                        window.location.href = result.redirect_url;
                    } else {
                        throw new Error(result.message || 'Payment verification failed');
                    }
                } catch (error) {
                    console.error('Verification error:', error);
                    await showAlert('error', error.message || 'Payment verification failed');
                    resetOrderButton();
                }
            },
            modal: {
                ondismiss: function() {
                    console.log('Razorpay modal dismissed');
                    resetOrderButton();
                }
            }
        };

        try {
            const rzp = new Razorpay(options);
            rzp.on('payment.failed', function(response) {
                console.error('Razorpay payment failed:', response.error);
                showAlert('error', response.error.description || 'Payment failed');
                resetOrderButton();
            });
            rzp.open();
        } catch (error) {
            console.error('Razorpay initialization error:', error);
            showAlert('error', 'Failed to initialize payment');
            resetOrderButton();
        }
    }

    async function processCODOrWalletPayment(addressId, paymentMethod) {
        console.log(`Processing ${paymentMethod} payment`);
        await showLoadingAlert();

        const formData = new FormData();
        formData.append('savedAddress', addressId);
        formData.append('payment', paymentMethod);

        try {
            const response = await fetch(orderForm.getAttribute('data-url'), {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                },
                body: formData
            });

            const result = await response.json();
            console.log(`${paymentMethod} payment result:`, result);

            if (result.status === 'success') {
                await showAlert('success', result.message || 'Order placed successfully!');
                window.location.href = result.redirect_url;
            } else {
                throw new Error(result.message || `${paymentMethod} payment failed`);
            }
        } catch (error) {
            console.error(`${paymentMethod} payment error:`, error);
            showAlert('error', error.message || 'Failed to process payment');
            resetOrderButton();
        }
    }

    // Event Handlers
    async function handleOrderSubmission(e) {
        e.preventDefault();
        console.log('Order submission started');

        const selectedPayment = document.querySelector('input[name="payment"]:checked');
        const addressId = currentDeliveryAddress?.getAttribute('data-address-id');

        if (!addressId) {
            showAlert('error', 'Please select a delivery address');
            return;
        }

        if (!selectedPayment) {
            showAlert('error', 'Please select a payment method');
            return;
        }

        placeOrderButton.disabled = true;
        placeOrderButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Processing...';

        try {
            if (selectedPayment.value === 'ONLINE') {
                await showLoadingAlert('Initializing payment...');
                
                const formData = new FormData();
                formData.append('savedAddress', addressId);
                formData.append('payment', selectedPayment.value);

                const response = await fetch(orderForm.getAttribute('data-url'), {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': csrfToken
                    },
                    body: formData
                });

                const data = await response.json();
                console.log('Initial payment setup response:', data);

                if (data.status === 'success') {
                    await processRazorpayPayment(data, addressId);
                } else {
                    throw new Error(data.message || 'Failed to initialize payment');
                }
            } else {
                await processCODOrWalletPayment(addressId, selectedPayment.value);
            }
        } catch (error) {
            console.error('Order submission error:', error);
            showAlert('error', error.message || 'An unexpected error occurred');
            resetOrderButton();
        }
    }

    // Event Listeners
    paymentMethodInputs.forEach(input => {
        input.addEventListener('change', checkOrderEligibility);
    });

    document.querySelectorAll('.payment-option').forEach(container => {
        container.addEventListener('click', function() {
            const radio = this.querySelector('input[type="radio"]');
            if (radio) {
                radio.checked = true;
                checkOrderEligibility();
            }
        });
    });

    if (changeAddressLink) {
        changeAddressLink.addEventListener('click', function(e) {
            e.preventDefault();
            document.querySelector('#savedAddressesSection').scrollIntoView({ behavior: 'smooth' });
        });
    }

    if (orderForm) {
        orderForm.addEventListener('submit', handleOrderSubmission);
    }

    // Initialize
    checkOrderEligibility();
});