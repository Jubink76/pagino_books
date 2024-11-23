document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('address-form');
    const inputs = form.querySelectorAll('input:not([type="hidden"])');
    const typeOptions = document.querySelectorAll('.type-option');
    const addressTypeInput = form.querySelector('input[name="address_type"]');
    
    // Toggle visibility of address form and saved addresses section
    document.getElementById('addNewAddressBtn').addEventListener('click', function() {
        document.getElementById('savedAddressesSection').classList.add('hidden');
        document.getElementById('newAddressFormSection').classList.remove('hidden');
    });

    // Cancel the address form and go back to saved addresses section
    document.getElementById('cancelBtn').addEventListener('click', function() {
        document.getElementById('savedAddressesSection').classList.remove('hidden');
        document.getElementById('newAddressFormSection').classList.add('hidden');
    });

    // Handle address type selection
    document.addEventListener('DOMContentLoaded', function() {
        const form = document.getElementById('address-form');
        const typeOptions = document.querySelectorAll('.type-option');
        const addressTypeInput = form.querySelector('input[name="address_type"]');
    
        // Handle address type selection
        typeOptions.forEach(option => {
            option.addEventListener('click', function() {
                // Log to check if the click event is being fired
                console.log('Clicked:', this);
    
                // Remove 'active' class from all type options
                typeOptions.forEach(opt => opt.classList.remove('active', 'border-yellow-500'));
    
                // Add 'active' class to the clicked element
                this.classList.add('active', 'border-yellow-500');
                
                // Set the address type value in the hidden input
                addressTypeInput.value = this.getAttribute('data-type');
                
                // Log to verify the address type is set correctly
                console.log('Address Type Set:', addressTypeInput.value);
            });
        });
    });
    // Validation patterns
    const patterns = {
        address_name: {
            pattern: /^[a-zA-Z\s]*$/,
            message: 'Name should only contain letters and spaces'
        },
        pincode: {
            pattern: /^\d{6}$/,
            message: 'Pincode must be 6 digits'
        },
        address_phone: {
            pattern: /^\d{10}$/,
            message: 'Phone number must be 10 digits'
        },
        city: {
            pattern: /^[a-zA-Z\s]*$/,
            message: 'City should only contain letters and spaces'
        },
        state: {
            pattern: /^[a-zA-Z\s]*$/,
            message: 'State should only contain letters and spaces'
        }
    };

    // Real-time validation
    inputs.forEach(input => {
        input.addEventListener('input', validateField);
        input.addEventListener('blur', validateField);
    });

    function validateField(e) {
        const input = e.target;
        const errorDiv = input.nextElementSibling;
        const value = input.value.trim();
        
        // Reset error state
        hideError(input, errorDiv);

        // Required field validation
        if (input.required && !value) {
            showError(input, errorDiv, 'This field is required');
            return false;
        }

        // Pattern validation
        if (patterns[input.name] && value) {
            if (!patterns[input.name].pattern.test(value)) {
                showError(input, errorDiv, patterns[input.name].message);
                return false;
            }
        }

        return true;
    }

    function showError(input, errorDiv, message) {
        errorDiv.textContent = message;
        errorDiv.classList.remove('hidden');
        input.classList.add('border-red-500');
    }

    function hideError(input, errorDiv) {
        errorDiv.classList.add('hidden');
        input.classList.remove('border-red-500');
    }

    // Form submission
    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        // Validate all fields
        let isValid = true;
        inputs.forEach(input => {
            if (!validateField({ target: input })) {
                isValid = false;
            }
        });

        if (!isValid) return;

        const formData = new FormData(form);

        try {
            const response = await fetch('{% url "checkout_add_address" %}', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                }
            });

            const data = await response.json();

            if (data.status === 'success') {
                Swal.fire({
                    icon: 'success',
                    title: 'Success!',
                    text: data.message,
                    showConfirmButton: false,
                    timer: 1500
                }).then(() => {
                    // Redirect or reset form based on your needs
                    form.reset();
                    window.location.reload(); // or redirect to another page
                });
            } else {
                // Show server-side validation errors
                if (data.errors) {
                    Object.entries(data.errors).forEach(([field, message]) => {
                        const input = form.querySelector(`[name=${field}]`);
                        const errorDiv = input.nextElementSibling;
                        showError(input, errorDiv, message);
                    });
                } else {
                    Swal.fire({
                        icon: 'error',
                        title: 'Error',
                        text: data.message || 'An error occurred. Please try again.',
                    });
                }
            }
        } catch (error) {
            console.error('Error:', error);
            Swal.fire({
                icon: 'error',
                title: 'Oops...',
                text: 'Something went wrong! Please try again.',
            });
        }
    });

    // Cancel button handler
    document.getElementById('cancel-btn').addEventListener('click', function() {
        form.reset();
        // Remove all error messages
        form.querySelectorAll('.error-message').forEach(div => div.classList.add('hidden'));
        form.querySelectorAll('input').forEach(input => input.classList.remove('border-red-500'));
    });
});
