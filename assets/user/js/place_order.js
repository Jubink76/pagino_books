document.addEventListener('DOMContentLoaded', function () {
    const savedAddressItems = document.querySelectorAll('.saved-address-item');
    const currentDeliveryAddress = document.getElementById('currentDeliveryAddress');
    const changeAddressLink = document.getElementById('changeAddressLink');
    const paymentMethodInputs = document.querySelectorAll('input[name="payment"]');
    const placeOrderButton = document.getElementById('place-order-button');
    const orderForm = document.getElementById('orderForm');
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    function loadRazorpayScript(callback) {
        const script = document.createElement("script");
        script.src = "https://checkout.razorpay.com/v1/checkout.js";
        script.onload = callback;
        document.body.appendChild(script);
    }

    function showAlert(type, message) {
        Swal.fire({
            icon: type,
            title: type === 'success' ? 'Success!' : 'Oops...',
            text: message,
            confirmButtonColor: type === 'success' ? '#10B981' : '#EF4444',
        });
    }

    function resetOrderButton() {
        if (placeOrderButton) {
            placeOrderButton.disabled = false;
            placeOrderButton.innerHTML = 'Place Order <i class="fas fa-arrow-right ml-2"></i>';
        }
    }

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

    // Add address selection logic
    if (savedAddressItems) {
        savedAddressItems.forEach(item => {
            item.addEventListener('click', function() {
                // Remove selected class from all address items
                savedAddressItems.forEach(el => el.classList.remove('border-yellow-500', 'bg-yellow-50'));
                
                // Add selected class to clicked item
                this.classList.add('border-yellow-500', 'bg-yellow-50');
                
                // Set the current delivery address
                if (currentDeliveryAddress) {
                    currentDeliveryAddress.textContent = this.querySelector('.address-details').textContent;
                    currentDeliveryAddress.setAttribute('data-address-id', this.getAttribute('data-address-id'));
                }
                
                // Recheck order eligibility
                checkOrderEligibility();
            });
        });
    }

    async function handleOrderSubmission(e) {
        e.preventDefault();

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
            const formData = new FormData();
            formData.append('savedAddress', addressId);
            formData.append('payment', selectedPayment.value);
            formData.append('csrfmiddlewaretoken', csrfToken);

            const response = await fetch(orderForm.getAttribute('data-url') || '/create-order/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                },
                credentials: 'same-origin'
            });

            const data = await response.json();

            if (data.status === 'success') {
                if (data.payment_method === 'ONLINE') {
                    loadRazorpayScript(() => {
                        const options = {
                            key: data.razorpay_key,
                            amount: data.amount,
                            currency: data.currency,
                            name: data.store_name || "Your Store Name",
                            description: "Order Payment",
                            order_id: data.razorpay_order_id,
                            handler: function (response) {
                                const verificationData = new FormData();
                                verificationData.append('savedAddress', addressId);
                                verificationData.append('payment', 'ONLINE');
                                verificationData.append('razorpay_payment_id', response.razorpay_payment_id);
                                verificationData.append('razorpay_order_id', response.razorpay_order_id);
                                verificationData.append('razorpay_signature', response.razorpay_signature);
                                verificationData.append('csrfmiddlewaretoken', csrfToken);

                                fetch(orderForm.getAttribute('data-url') || '/create-order/', {
                                    method: 'POST',
                                    body: verificationData,
                                    headers: {
                                        'X-CSRFToken': csrfToken
                                    }
                                })
                                .then(response => response.json())
                                .then(result => {
                                    if (result.status === 'success') {
                                        Swal.fire({
                                            icon: 'success',
                                            title: 'Payment Successful!',
                                            text: 'Your order has been placed.',
                                            timer: 2000,
                                            timerProgressBar: true
                                        }).then(() => {
                                            window.location.href = result.redirect_url;
                                        });
                                    } else {
                                        showAlert('error', result.message || 'Payment verification failed');
                                        resetOrderButton();
                                    }
                                })
                                .catch(error => {
                                    console.error('Verification error:', error);
                                    showAlert('error', 'An error occurred during payment verification');
                                    resetOrderButton();
                                });
                            },
                            prefill: {
                                name: data.customer_name,
                                email: data.email,
                                contact: data.phone
                            },
                            theme: { color: "#3399cc" },
                            modal: {
                                ondismiss: function() {
                                    resetOrderButton();
                                }
                            }
                        };
                        const rzp = new Razorpay(options);
                        rzp.on('payment.failed', function(response) {
                            console.error('Razorpay payment failed:', response.error);
                            showAlert('error', response.error.description || 'Payment failed');
                            resetOrderButton();
                        });
                        rzp.open();
                    });
                } else {
                    Swal.fire({
                        icon: 'success',
                        title: 'Order Placed!',
                        text: 'Your order has been successfully placed.',
                        timer: 2000,
                        timerProgressBar: true
                    }).then(() => {
                        window.location.href = data.redirect_url;
                    });
                }
            } else {
                showAlert('error', data.message || 'An error occurred while placing your order');
                resetOrderButton();
            }
        } catch (error) {
            console.error('Order submission error:', error);
            showAlert('error', 'An unexpected error occurred. Please try again.');
            resetOrderButton();
        }
    }

    // Existing event listeners
    paymentMethodInputs.forEach((input) => {
        input.addEventListener('change', checkOrderEligibility);
    });

    document.querySelectorAll('.payment-option').forEach((container) => {
        container.addEventListener('click', function () {
            const radio = this.querySelector('input[type="radio"]');
            if (radio) {
                radio.checked = true;
                checkOrderEligibility();
            }
        });
    });

    // Change address link scroll functionality
    if (changeAddressLink) {
        changeAddressLink.addEventListener('click', function(e) {
            e.preventDefault();
            document.querySelector('#savedAddressesSection').scrollIntoView({ behavior: 'smooth' });
        });
    }

    if (orderForm) {
        orderForm.addEventListener('submit', handleOrderSubmission);
    }

    checkOrderEligibility();
});