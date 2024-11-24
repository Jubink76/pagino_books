document.addEventListener('DOMContentLoaded', function () {
    // Existing DOM elements
    const addressForm = document.getElementById('addressForm');
    const submitButton = document.getElementById('submit');
    const addNewAddressBtn = document.getElementById('addNewAddressBtn');
    const savedAddressesSection = document.getElementById('savedAddressesSection');
    const newAddressFormSection = document.getElementById('newAddressFormSection');
    const typeOptions = document.querySelectorAll('.type-option');
    const deliveryAddressDiv = document.querySelector('.delivery-address');
    const orderForm = document.querySelector('form:not(#addressForm)'); // Get the order form
    let selectedAddressType = 'home'; // Default address type

    // Existing address display function
    function updateDeliveryAddress(addressElement) {
        if (!addressElement) {
            console.log('No address element found');
            return;
        }
        
        // Extract all address details from the selected address
        const addressType = addressElement.querySelector('.font-medium')?.textContent?.trim() || 'Home';
        const name = addressElement.querySelector('.text-gray-900')?.textContent?.trim() || '';
        const addressLines = Array.from(addressElement.querySelectorAll('.text-gray-600 p')).map(p => p.textContent.trim());
        
        // Create the address HTML with all details
        const addressHTML = `
            <div class="border border-green-500 rounded-lg p-4 bg-green-50">
                <div class="flex-1">
                    <div class="flex items-center gap-2 mb-2">
                        <input type="radio" checked disabled>
                        <i class="fas fa-${addressType.toLowerCase() === 'home' ? 'home' : 'building'} text-gray-600"></i>
                        <span class="font-medium">${addressType}</span>
                    </div>
                    <div class="space-y-1 text-gray-600 ml-6">
                        <p class="font-semibold text-gray-900">${name}</p>
                        ${addressLines.map(line => `<p>${line}</p>`).join('')}
                    </div>
                </div>
            </div>
        `;
        
        // Update the delivery address display
        const deliveryAddressDiv = document.querySelector('.delivery-address');
        if (deliveryAddressDiv) {
            deliveryAddressDiv.innerHTML = addressHTML;
        }
    }

    // Order form validation check
    function checkOrderValidation() {
        const placeOrderButton = document.querySelector('button[type="submit"][disabled]');
        const selectedAddress = document.querySelector('input[name="savedAddress"]:checked');
        const selectedPayment = document.querySelector('input[name="payment"]:checked');

        if (!placeOrderButton) {
            console.log('Place order button not found');
            return;
        }

        if (selectedAddress && selectedPayment) {
            placeOrderButton.disabled = false;
            placeOrderButton.classList.remove('bg-gray-400');
            placeOrderButton.classList.add('bg-yellow-500', 'hover:bg-yellow-600');
            
            const orderForm = placeOrderButton.closest('form');
            if (orderForm) {
                // Handle address input
                let addressInput = orderForm.querySelector('input[name="savedAddress"][type="hidden"]');
                if (!addressInput) {
                    addressInput = document.createElement('input');
                    addressInput.type = 'hidden';
                    addressInput.name = 'savedAddress';
                    orderForm.appendChild(addressInput);
                }
                addressInput.value = selectedAddress.value;

                // Handle payment input
                let paymentInput = orderForm.querySelector('input[name="payment"][type="hidden"]');
                if (!paymentInput) {
                    paymentInput = document.createElement('input');
                    paymentInput.type = 'hidden';
                    paymentInput.name = 'payment';
                    orderForm.appendChild(paymentInput);
                }
                paymentInput.value = selectedPayment.value;
            }
        } else {
            placeOrderButton.disabled = true;
            placeOrderButton.classList.add('bg-gray-400');
            placeOrderButton.classList.remove('bg-yellow-500', 'hover:bg-yellow-600');
        }
    }

    // Add event listeners for address and payment selection
    document.querySelectorAll('input[name="savedAddress"]').forEach(radio => {
        radio.addEventListener('change', function() {
            document.querySelectorAll('.saved-address-item').forEach(item => {
                item.classList.remove('border-green-500', 'bg-green-50', 'border-yellow-500');
            });
            
            const selectedAddressItem = this.closest('.saved-address-item');
            if (selectedAddressItem) {
                selectedAddressItem.classList.add('border-green-500', 'bg-green-50');
                updateDeliveryAddress(selectedAddressItem);
                checkOrderValidation();
            }
        });
    });

    document.querySelectorAll('input[name="payment"]').forEach(radio => {
        radio.addEventListener('change', checkOrderValidation);
    });

    // Toggle functions
    function showNewAddressForm() {
        if (savedAddressesSection && newAddressFormSection && addNewAddressBtn) {
            savedAddressesSection.classList.add('hidden');
            newAddressFormSection.classList.remove('hidden');
            addNewAddressBtn.innerHTML = '<i class="fas fa-list"></i> View Saved Addresses';
            addNewAddressBtn.removeEventListener('click', showNewAddressForm);
            addNewAddressBtn.addEventListener('click', showSavedAddresses);
        }
    }

    function showSavedAddresses() {
        if (savedAddressesSection && newAddressFormSection && addNewAddressBtn) {
            savedAddressesSection.classList.remove('hidden');
            newAddressFormSection.classList.add('hidden');
            addNewAddressBtn.innerHTML = '<i class="fas fa-plus"></i> Add New Address';
            addNewAddressBtn.removeEventListener('click', showSavedAddresses);
            addNewAddressBtn.addEventListener('click', showNewAddressForm);
        }
    }

    if (addNewAddressBtn) {
        addNewAddressBtn.addEventListener('click', showNewAddressForm);
    }

    // Address type selection
    typeOptions.forEach(option => {
        option.addEventListener('click', () => {
            typeOptions.forEach(opt => {
                opt.classList.remove('active', 'border-red-500', 'bg-red-50');
                opt.classList.add('border-gray-300');
            });
            option.classList.add('active', 'border-red-500', 'bg-red-50');
            option.classList.remove('border-gray-300');
            selectedAddressType = option.dataset.type;
        });
    });

    // Validation functions
    function clearErrors() {
        document.querySelectorAll('.error-message').forEach(error => error.remove());
        document.querySelectorAll('input').forEach(input => {
            input.classList.remove('border-red-500', 'bg-red-50');
        });
    }

    const validationRules = {
        address_name: {
            pattern: /^[A-Za-z\s]+$/,
            message: "Name should only contain letters and spaces",
            required: true
        },
        street_name: {
            required: true,
            message: "Street address is required"
        },
        building_no: {
            required: true,
            message: "Building number is required"
        },
        landmark: {
            required: true,
            message: "Landmark is required"
        },
        city: {
            pattern: /^[A-Za-z\s]+$/,
            message: "City should only contain letters and spaces",
            required: true
        },
        pincode: {
            pattern: /^\d{6}$/,
            message: "Please enter a valid 6-digit postal code",
            required: true
        },
        address_phone: {
            pattern: /^[6-9]\d{9}$/,
            message: "Please enter a valid 10-digit Indian phone number",
            required: true
        },
        state: {
            pattern: /^[A-Za-z\s]+$/,
            message: "State should only contain letters and spaces",
            required: true
        }
    };

    function validateField(input) {
        const rules = validationRules[input.name];
        if (!rules) return true;

        let isValid = true;
        const value = input.value.trim();

        const existingError = input.parentElement.querySelector('.error-message');
        if (existingError) existingError.remove();

        if (rules.required && !value) {
            isValid = false;
            showFieldError(input, rules.message);
        }
        else if (rules.pattern && value && !rules.pattern.test(value)) {
            isValid = false;
            showFieldError(input, rules.message);
        }

        input.classList.toggle('border-red-500', !isValid);
        input.classList.toggle('bg-red-50', !isValid);

        return isValid;
    }

    function showFieldError(input, message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message text-red-500 text-sm mt-1';
        errorDiv.textContent = message;
        input.parentElement.appendChild(errorDiv);
    }

    function validateForm() {
        clearErrors();
        let isValid = true;
        const errors = {};

        const formData = new FormData(addressForm);

        for (const [fieldName, value] of formData.entries()) {
            const rules = validationRules[fieldName];
            if (rules) {
                const fieldValue = value.trim();
                
                if (rules.required && !fieldValue) {
                    errors[fieldName] = rules.message;
                    isValid = false;
                } else if (rules.pattern && !rules.pattern.test(fieldValue)) {
                    errors[fieldName] = rules.message;
                    isValid = false;
                }
            }
        }

        if (!isValid) {
            Object.entries(errors).forEach(([fieldName, message]) => {
                const input = addressForm.querySelector(`[name="${fieldName}"]`);
                if (input) {
                    input.classList.add('border-red-500', 'bg-red-50');
                    showFieldError(input, message);
                }
            });
        }

        return isValid;
    }

    // Add field validation listeners
    document.querySelectorAll('input').forEach(input => {
        if (validationRules[input.name]) {
            input.addEventListener('blur', () => validateField(input));
            input.addEventListener('input', () => {
                input.classList.remove('border-red-500', 'bg-red-50');
                const errorMessage = input.parentElement.querySelector('.error-message');
                if (errorMessage) errorMessage.remove();
            });
        }
    });

    // Address form submission handler
    if (addressForm) {
        addressForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            if (!validateForm()) {
                Swal.fire({
                    title: 'Validation Error',
                    text: 'Please correct the errors in the form.',
                    icon: 'error',
                    confirmButtonText: 'OK'
                });
                return false;
            }

            const selectedType = document.querySelector('.type-option.active')?.dataset.type || 'home';
            const formData = new FormData(addressForm);
            formData.append('address_type', selectedType);

            if (submitButton) {
                submitButton.disabled = true;
                submitButton.classList.add('opacity-50');
            }

            try {
                const response = await fetch(addressForm.dataset.url, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': formData.get('csrfmiddlewaretoken'),
                    },
                    body: formData
                });

                const data = await response.json();

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
                        } else {
                            window.location.reload();
                        }
                    });
                } else {
                    if (data.errors) {
                        Object.entries(data.errors).forEach(([field, message]) => {
                            const input = addressForm.querySelector(`[name="${field}"]`);
                            if (input) {
                                input.classList.add('border-red-500', 'bg-red-50');
                                showFieldError(input, message);
                            }
                        });
                    }
                    
                    Swal.fire({
                        title: 'Error!',
                        text: data.message || 'An error occurred.',
                        icon: 'error',
                        confirmButtonText: 'OK'
                    });
                }
            } catch (error) {
                console.error('Error:', error);
                Swal.fire({
                    title: 'Error!',
                    text: 'An error occurred while processing your request.',
                    icon: 'error',
                    confirmButtonText: 'OK'
                });
            } finally {
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.classList.remove('opacity-50');
                }
            }

            return false;
        });
    }

    // Order form submission handler
    if (orderForm) {
        orderForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const submitButton = this.querySelector('button[type="submit"]');
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.classList.add('opacity-50');
            }

            try {
                const formData = new FormData(this);
                const response = await fetch(this.action, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': formData.get('csrfmiddlewaretoken'),
                    },
                    body: formData
                });

                const data = await response.json();
                console.log('Response received:', data); // Debug log

                if (data.status === 'success') {
                    await Swal.fire({
                        title: 'Success!',
                        text: data.message,
                        icon: 'success',
                        timer: 2000,
                        showConfirmButton: false
                    });
                    
                    console.log('Redirecting to:', data.redirect_url); // Debug log
                    if (data.redirect_url) {
                        window.location.href = data.redirect_url;
                    }
                } else {
                    Swal.fire({
                        title: 'Error!',
                        text: data.message || 'An error occurred.',
                        icon: 'error',
                        confirmButtonText: 'OK'
                    });
                }
            } catch (error) {
                console.error('Error:', error);
                Swal.fire({
                    title: 'Error!',
                    text: 'An error occurred while processing your request.',
                    icon: 'error',
                    confirmButtonText: 'OK'
                });
            } finally {
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.classList.remove('opacity-50');
                }
            }
        });
    }

    // Initialize validation state
    checkOrderValidation();
});