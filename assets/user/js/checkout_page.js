document.addEventListener('DOMContentLoaded', function() {
    // Validation rules
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

    // Get references to key elements
    const addressForm = document.getElementById('addressForm');
    const savedAddressesSection = document.getElementById('savedAddressesSection');
    const newAddressFormSection = document.getElementById('newAddressFormSection');
    
    // Get both address buttons
    const addNewAddressButtons = document.querySelectorAll('#addNewAddressBtn');
    const addNewAddressBtn = addNewAddressButtons[0];
    const showAddressesBtn = addNewAddressButtons[1];
    
    const cancelButton = document.querySelector('#addressForm button[type="button"]');

    // Function to submit the address form with AJAX
    function submitAddressForm(form) {
        const formData = new FormData(form);
        
        fetch(form.dataset.url, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Show success message
                Swal.fire({
                    title: 'Success!',
                    text: data.message,
                    icon: 'success',
                    confirmButtonText: 'OK'
                }).then((result) => {
                    if (result.isConfirmed && data.redirect_url) {
                        window.location.href = data.redirect_url;
                    }
                });
            } else {
                // Show error message
                if (data.errors) {
                    // Display field-specific errors
                    Object.entries(data.errors).forEach(([field, error]) => {
                        const inputField = form.querySelector(`[name="${field}"]`);
                        if (inputField) {
                            displayError(inputField, error);
                        }
                    });
                }
                Swal.fire({
                    title: 'Error!',
                    text: data.message,
                    icon: 'error',
                    confirmButtonText: 'OK'
                });
            }
        })
        .catch(error => {
            console.error('Error:', error);
            Swal.fire({
                title: 'Error!',
                text: 'An unexpected error occurred. Please try again.',
                icon: 'error',
                confirmButtonText: 'OK'
            });
        });
    }

    // Function to update delivery address
    function updateDeliveryAddress(addressElement) {
        const deliveryAddressContainer = document.querySelector('.delivery-address');
        
        const addressName = addressElement.querySelector('.font-semibold').textContent;
        const streetName = addressElement.querySelector('p:nth-child(2)').textContent;
        const landmarkElement = addressElement.querySelector('p:nth-child(3)');
        const cityStatePostal = addressElement.querySelector('p:nth-child(4)').textContent;
        const phoneNumber = addressElement.querySelector('p:nth-child(5)').textContent;

        deliveryAddressContainer.innerHTML = `
            <div class="p-4 border rounded-lg">
                <div class="flex items-center gap-2 mb-2">
                    <span class="bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded-full">Selected</span>
                </div>
                <p class="font-semibold">${addressName}</p>
                <p>${streetName}</p>
                ${landmarkElement ? `<p>${landmarkElement.textContent}</p>` : ''}
                <p>${cityStatePostal}</p>
                <p>${phoneNumber}</p>
            </div>
        `;

        const addressId = addressElement.dataset.addressId;
        fetch('/update-default-address/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify({ address_id: addressId })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                console.log('Default address updated successfully');
            }
        })
        .catch(error => {
            console.error('Error updating default address:', error);
        });
    }

    // Function to show new address form
    function showNewAddressForm() {
        savedAddressesSection.classList.add('hidden');
        newAddressFormSection.classList.remove('hidden');
        addNewAddressBtn.classList.add('hidden');
        showAddressesBtn.classList.remove('hidden');
    }

    // Function to show saved addresses
    function showSavedAddresses() {
        savedAddressesSection.classList.remove('hidden');
        newAddressFormSection.classList.add('hidden');
        addNewAddressBtn.classList.remove('hidden');
        showAddressesBtn.classList.add('hidden');

        if (addressForm) {
            addressForm.reset();

            const typeOptions = document.querySelectorAll('.type-option');
            typeOptions.forEach(opt => {
                opt.classList.remove('active', 'border-red-500', 'bg-red-50');
                opt.classList.add('border-gray-300');
            });
            
            const homeOption = document.querySelector('.type-option[data-type="home"]');
            if (homeOption) {
                homeOption.classList.add('active', 'border-red-500', 'bg-red-50');
                homeOption.classList.remove('border-gray-300');
                const addressTypeInput = homeOption.querySelector('input[name="address_type"]');
                if (addressTypeInput) {
                    addressTypeInput.value = 'home';
                }
            }
        }
    }

    function validateField(fieldName, value) {
        const rule = validationRules[fieldName];
        if (!rule) return null;

        if (rule.required && (!value || value.trim() === '')) {
            return rule.message || "This field is required";
        }

        if (!value && !rule.required) return null;

        if (rule.pattern && !rule.pattern.test(value.trim())) {
            return rule.message || "Invalid input";
        }

        return null;
    }

    function displayError(field, errorMessage) {
        const existingError = field.parentNode.querySelector('.text-red-500');
        if (existingError) {
            existingError.remove();
        }

        if (errorMessage) {
            field.classList.add('border-red-500', 'bg-red-50');
            
            const errorSpan = document.createElement('span');
            errorSpan.classList.add('text-red-500', 'text-sm', 'mt-1', 'block');
            errorSpan.textContent = errorMessage;
            
            field.parentNode.insertBefore(errorSpan, field.nextSibling);
        } else {
            field.classList.remove('border-red-500', 'bg-red-50');
        }
    }

    function validateForm() {
        let isValid = true;

        Object.keys(validationRules).forEach(fieldName => {
            const field = document.querySelector(`[name="${fieldName}"]`);
            if (!field) return;

            const errorMessage = validateField(fieldName, field.value);
            displayError(field, errorMessage);

            if (errorMessage) {
                isValid = false;
            }
        });

        const selectedAddressType = document.querySelector('.type-option.active');
        if (!selectedAddressType) {
            isValid = false;
            const addressTypeContainer = document.querySelector('.flex.gap-5.mb-8');
            
            const errorSpan = document.createElement('span');
            errorSpan.classList.add('text-red-500', 'text-sm', 'block', 'mt-2');
            errorSpan.textContent = 'Please select an address type (Home or Office)';
            
            const existingError = addressTypeContainer.querySelector('.text-red-500');
            if (existingError) {
                existingError.remove();
            }
            
            addressTypeContainer.appendChild(errorSpan);
        }

        return isValid;
    }

    // Setup address type selector toggle
    const typeOptions = document.querySelectorAll('.type-option');
    typeOptions.forEach(option => {
        option.addEventListener('click', function() {
            typeOptions.forEach(opt => {
                opt.classList.remove('active', 'border-red-500', 'bg-red-50');
                opt.classList.add('border-gray-300');
            });
            
            this.classList.add('active', 'border-red-500', 'bg-red-50');
            this.classList.remove('border-gray-300');

            const addressTypeInput = this.querySelector('input[name="address_type"]');
            if (addressTypeInput) {
                addressTypeInput.value = this.dataset.type;
            }
        });
    });

    // Setup form submission with validation
    if (addressForm) {
        addressForm.addEventListener('submit', function(event) {
            event.preventDefault();
            const isValid = validateForm();
            if (isValid) {
                submitAddressForm(this);
            }
        });
    }

    // Setup event listeners
    addNewAddressBtn.addEventListener('click', showNewAddressForm);
    showAddressesBtn.addEventListener('click', showSavedAddresses);

    if (cancelButton) {
        cancelButton.addEventListener('click', showSavedAddresses);
    }

    // Setup real-time validation
    function setupRealTimeValidation() {
        Object.keys(validationRules).forEach(fieldName => {
            const field = document.querySelector(`[name="${fieldName}"]`);
            if (!field) return;

            let isTouched = false;

            field.addEventListener('input', function() {
                if (isTouched) {
                    const errorMessage = validateField(fieldName, this.value);
                    displayError(this, errorMessage);
                }
            });

            field.addEventListener('blur', function() {
                isTouched = true;
                const errorMessage = validateField(fieldName, this.value);
                displayError(this, errorMessage);
            });

            field.addEventListener('focus', function() {
                if (!this.value.trim()) {
                    displayError(this, null);
                }
            });
        });
    }

    // Setup saved address selection
    const savedAddressItems = document.querySelectorAll('.saved-address-item');
    savedAddressItems.forEach(item => {
        item.addEventListener('click', function() {
            savedAddressItems.forEach(addressItem => {
                const radio = addressItem.querySelector('input[type="radio"]');
                addressItem.classList.remove('border-yellow-500');
                radio.checked = false;
            });

            const radio = this.querySelector('input[type="radio"]');
            radio.checked = true;
            this.classList.add('border-yellow-500');

            updateDeliveryAddress(this);
        });
    });

    // Initialize real-time validation
    setupRealTimeValidation();

    console.log("Dynamic address form script loaded successfully");
});