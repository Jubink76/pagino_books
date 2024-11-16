document.addEventListener('DOMContentLoaded', function() {
    // UI Elements
    const elements = {
        savedAddressesSection: document.getElementById('savedAddressesSection'),
        newAddressFormSection: document.getElementById('newAddressFormSection'),
        addNewAddressBtn: document.getElementById('addNewAddressBtn'),
        deliveryAddressPanel: document.querySelector('.delivery-address'),
        placeOrderButton: document.querySelector('.btn-place-order'),
        paymentRadios: document.querySelectorAll('input[name="payment"]'),
        savedAddressItems: document.querySelectorAll('.saved-address-item')
    };

    // State management
    let state = {
        selectedAddress: null,
        selectedPayment: null
    };

    // Initialize event listeners
    function initializeEventListeners() {
        // Address item click handler
        elements.savedAddressItems.forEach(item => {
            item.addEventListener('click', function(e) {
                // Prevent triggering if clicking on radio input
                if (e.target.type === 'radio') return;
                
                const radio = this.querySelector('.address-radio');
                if (radio) {
                    radio.checked = true;
                    state.selectedAddress = this;
                    updateDeliveryAddress();
                    validateOrderButton();
                }
            });

            // Make the entire address item focusable
            item.setAttribute('tabindex', '0');
            
            // Handle keyboard selection
            item.addEventListener('keypress', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    const radio = this.querySelector('.address-radio');
                    if (radio) {
                        radio.checked = true;
                        state.selectedAddress = this;
                        updateDeliveryAddress();
                        validateOrderButton();
                    }
                }
            });
        });

        // Radio button handlers
        elements.paymentRadios.forEach(radio => {
            radio.addEventListener('change', function() {
                state.selectedPayment = this.value;
                validateOrderButton();
            });
        });

        // Add New Address button handler
        if (elements.addNewAddressBtn) {
            elements.addNewAddressBtn.addEventListener('click', toggleAddressForm);
        }

        // Place order button handler
        if (elements.placeOrderButton) {
            elements.placeOrderButton.addEventListener('click', handlePlaceOrder);
        }
    }

    // Update delivery address panel
    function updateDeliveryAddress() {
        if (!state.selectedAddress || !elements.deliveryAddressPanel) return;

        const addressDetails = state.selectedAddress.querySelector('.address-details');
        const addressType = state.selectedAddress.querySelector('.address-type .type-label')?.textContent || 'Home';
        
        // Safely get text content from elements
        const nameText = addressDetails.querySelector('.name')?.textContent || '';
        const streetText = addressDetails.querySelector('.street')?.textContent || '';
        const areaText = addressDetails.querySelector('.area')?.textContent || '';
        const cityStateText = addressDetails.querySelector('.city-state')?.textContent || '';
        const phoneText = addressDetails.querySelector('.phone')?.textContent || '';

        elements.deliveryAddressPanel.innerHTML = `
            <h4 class="mt-4">Delivery Address</h4>
            <div class="selected-address bg-light p-3 rounded">
                <div class="address-type mb-2">
                    <span class="badge bg-secondary">${addressType}</span>
                </div>
                <p class="mb-1"><strong>${nameText}</strong></p>
                <p class="mb-1">${streetText}</p>
                ${areaText ? `<p class="mb-1">${areaText}</p>` : ''}
                <p class="mb-1">${cityStateText}</p>
                <p class="mb-1">${phoneText}</p>
                <button class="btn btn-link btn-sm p-0 mt-2" onclick="window.changeAddress()">Change</button>
            </div>
        `;

        elements.deliveryAddressPanel.classList.add('has-address');
    }

    // Toggle address form visibility
    function toggleAddressForm() {
        const savedSection = elements.savedAddressesSection;
        const formSection = elements.newAddressFormSection;
        
        if (savedSection && formSection) {
            if (formSection.style.display === 'none') {
                savedSection.style.display = 'none';
                formSection.style.display = 'block';
                elements.addNewAddressBtn.textContent = 'Back to Saved Addresses';
            } else {
                savedSection.style.display = 'block';
                formSection.style.display = 'none';
                elements.addNewAddressBtn.innerHTML = '<i class="fa fa-plus"></i> Add New Address';
            }
        }
    }

    // Validate order button state
    function validateOrderButton() {
        if (!elements.placeOrderButton) return;

        const isValid = state.selectedAddress && state.selectedPayment;
        
        elements.placeOrderButton.classList.toggle('disabled', !isValid);
        elements.placeOrderButton.disabled = !isValid;
        elements.placeOrderButton.style.backgroundColor = isValid ? '#fac825' : '#6c757d';
        elements.placeOrderButton.style.cursor = isValid ? 'pointer' : 'not-allowed';
    }

    // Handle place order
    function handlePlaceOrder(e) {
        e.preventDefault();
        
        if (!state.selectedAddress || !state.selectedPayment) {
            Swal.fire({
                icon: 'error',
                title: 'Oops...',
                text: 'Please select both delivery address and payment method!'
            });
            return;
        }
        const addressId = state.selectedAddress.querySelector('.address-radio').value;

        // Log data for debugging (replace with your form submission logic)
        console.log('Submitting order:', {
            addressId: addressId,
            paymentMethod: state.selectedPayment
        });
    
        // Submit the form with the required data
        const placeOrderForm = document.getElementById('placeOrderForm');
        if (placeOrderForm) {
            const addressInput = document.createElement('input');
            addressInput.type = 'hidden';
            addressInput.name = 'savedAddress';
            addressInput.value = addressId;
    
            const paymentInput = document.createElement('input');
            paymentInput.type = 'hidden';
            paymentInput.name = 'payment';
            paymentInput.value = state.selectedPayment;
    
            // Append hidden inputs to the form
            placeOrderForm.appendChild(addressInput);
            placeOrderForm.appendChild(paymentInput);
    
            // Submit the form
            placeOrderForm.submit();
        }

        Swal.fire({
            icon: 'success',
            title: 'Order Placed!',
            text: 'Your order has been placed successfully.'
        });
    }

    // Change address handler (exposed to window for inline onclick access)
    window.changeAddress = function() {
        state.selectedAddress = null;
        if (elements.deliveryAddressPanel) {
            elements.deliveryAddressPanel.innerHTML = `
                <h4 class="mt-4">Delivery Address</h4>
                <p class="text-muted">Please select a delivery address</p>
            `;
            elements.deliveryAddressPanel.classList.remove('has-address');
        }
        
        validateOrderButton();

        // Uncheck the selected address radio
        const selectedRadio = document.querySelector('input[name="savedAddress"]:checked');
        if (selectedRadio) {
            selectedRadio.checked = false;
        }
    };

    // Initialize the page
    initializeEventListeners();
});