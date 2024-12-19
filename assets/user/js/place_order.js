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

    // Function to check if all requirements are met
    function checkOrderEligibility() {
        const paymentMethodSelected = document.querySelector('input[name="payment"]:checked');
        const addressSelected = currentDeliveryAddress?.getAttribute('data-address-id');

        // Enable or disable the place order button
        placeOrderButton.disabled = !paymentMethodSelected || !addressSelected;

        if (!placeOrderButton.disabled) {
            placeOrderButton.classList.remove('bg-gray-400');
            placeOrderButton.classList.add('bg-yellow-500', 'hover:bg-yellow-600');
        } else {
            placeOrderButton.classList.add('bg-gray-400');
            placeOrderButton.classList.remove('bg-yellow-500', 'hover:bg-yellow-600');
        }
    }

    // Function to handle Razorpay payment verification
    async function verifyRazorpayPayment(response, redirectUrl) {
        try {
            const verificationData = new FormData();
            verificationData.append('razorpay_payment_id', response.razorpay_payment_id);
            verificationData.append('razorpay_order_id', response.razorpay_order_id);
            verificationData.append('razorpay_signature', response.razorpay_signature);
            verificationData.append('csrfmiddlewaretoken', csrfToken);

            const verificationResponse = await fetch('/verify-payment/', {
                method: 'POST',
                body: verificationData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                },
                credentials: 'same-origin'
            });

            const verificationResult = await verificationResponse.json();

            if (verificationResult.status === 'success') {
                await Swal.fire({
                    icon: 'success',
                    title: 'Payment Successful!',
                    text: 'Your order has been placed successfully.',
                    showConfirmButton: false,
                    timer: 2000,
                    timerProgressBar: true
                });
                window.location.href = redirectUrl || verificationResult.redirect_url;
            } else {
                throw new Error(verificationResult.message || 'Payment verification failed');
            }
        } catch (error) {
            showAlert('error', error.message || 'Payment verification failed');
            resetOrderButton();
        }
    }

    // Function to initialize Razorpay
    function initializeRazorpay(data) {
        const options = {
            key: data.razorpay_key,
            amount: data.amount,
            currency: data.currency,
            name: data.store_name || "Your Store Name",
            description: "Order Payment",
            order_id: data.razorpay_order_id,
            handler: async function (response) {
                await verifyRazorpayPayment(response, data.redirect_url);
            },
            prefill: {
                name: data.customer_name,
                email: data.email,
                contact: data.phone
            },
            theme: {
                color: "#3399cc"
            },
            method:{
                upi:true,
                card:true,
                netbanking:true,
                wallet:true,
                emi:false
            }
        };

        const rzp = new Razorpay(options);
        rzp.open();
    }

    // Function to handle order submission
    async function handleOrderSubmission(e) {
        e.preventDefault();

        // Get the payment method and address
        const selectedPayment = document.querySelector('input[name="payment"]:checked');
        const addressId = currentDeliveryAddress?.getAttribute('data-address-id');

        // Validate selections
        if (!addressId) {
            showAlert('error', 'Please select a delivery address');
            return;
        }

        if (!selectedPayment) {
            showAlert('error', 'Please select a payment method');
            return;
        }

        // Show loading state
        placeOrderButton.disabled = true;
        placeOrderButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Processing...';

        try {
            const formData = new FormData();
            formData.append('savedAddress', addressId);
            formData.append('payment', selectedPayment.value);
            formData.append('csrfmiddlewaretoken', csrfToken);

            const url = orderForm.getAttribute('data-url') || orderForm.action;
            const response = await fetch(url, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                },
                credentials: 'same-origin'
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const contentType = response.headers.get("content-type");
            if (!contentType || !contentType.includes("application/json")) {
                throw new TypeError("Response was not JSON");
            }

            const data = await response.json();

            if (data.status === 'success') {
                if (data.payment_method === 'ONLINE') {
                    // Handle Razorpay payment
                    initializeRazorpay(data);
                } else {
                    // Handle COD or other payment methods
                    await Swal.fire({
                        icon: 'success',
                        title: 'Order Placed Successfully!',
                        text: 'You will be redirected to the order confirmation page.',
                        showConfirmButton: false,
                        timer: 2000,
                        timerProgressBar: true,
                    });
                    window.location.href = data.redirect_url;
                }
            } else {
                showAlert('error', data.message || 'An error occurred while placing your order');
                resetOrderButton();
            }
        } catch (error) {
            console.error('Error:', error);
            showAlert('error', 'An unexpected error occurred. Please try again.');
            resetOrderButton();
        }
    }

    // Function to reset order button state
    function resetOrderButton() {
        placeOrderButton.disabled = false;
        placeOrderButton.innerHTML = 'Place Order <i class="fas fa-arrow-right ml-2"></i>';
    }

    // Add event listeners
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

    if (changeAddressLink) {
        changeAddressLink.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelector('#savedAddressesSection').scrollIntoView({ behavior: 'smooth' });
        });
    }

    if (orderForm) {
        orderForm.addEventListener('submit', handleOrderSubmission);
    }

    // Initial check
    checkOrderEligibility();
});