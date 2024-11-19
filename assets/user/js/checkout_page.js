document.addEventListener('DOMContentLoaded', function() {
    // UI Elements
    const elements = {
        // Address related elements
        savedAddressesSection: document.getElementById('savedAddressesSection'),
        newAddressFormSection: document.getElementById('newAddressFormSection'),
        addNewAddressBtn: document.getElementById('addNewAddressBtn'),
        addressForm: document.querySelector('.address-form'),
        cancelBtn: document.querySelector('.btn-cancel'),
        
        // Order related elements
        placeOrderForm: document.getElementById('placeOrderForm'),
        placeOrderBtn: document.querySelector('.btn-place-order'),
        deliveryAddressPanel: document.querySelector('.delivery-address'),
        paymentRadios: document.querySelectorAll('input[name="payment"]'),
        addressRadios: document.querySelectorAll('input[name="savedAddress"]')
    };

    // State management
    let state = {
        isAddingNewAddress: false,
        selectedAddress: null,
        selectedPayment: null,
        isSubmitting: false  // Add this line
    };

    // Address Form Toggle Functions
    function toggleAddressForm(show) {
        state.isAddingNewAddress = show;
        
        if (elements.savedAddressesSection) {
            elements.savedAddressesSection.style.display = show ? 'none' : 'block';
        }
        
        if (elements.newAddressFormSection) {
            elements.newAddressFormSection.style.display = show ? 'block' : 'none';
        }
        
        if (elements.addNewAddressBtn) {
            if (show) {
                elements.addNewAddressBtn.innerHTML = '<i class="fa fa-arrow-left"></i> Back to Saved Addresses';
            } else {
                elements.addNewAddressBtn.innerHTML = '<i class="fa fa-plus"></i> Add New Address';
            }
        }
    }

    // Update delivery address in the order summary
    function updateDeliveryAddress(addressElement) {
        if (!addressElement || !elements.deliveryAddressPanel) return;
    
        const addressDetails = addressElement.querySelector('.address-details');
        const addressType = addressElement.querySelector('.address-type .type-label')?.textContent || 'Home';
        
        // Get address details
        const nameText = addressDetails.querySelector('.name')?.textContent || '';
        const streetText = addressDetails.querySelector('.street')?.textContent || '';
        const areaText = addressDetails.querySelector('.area')?.textContent || '';
        const cityStateText = addressDetails.querySelector('.city-state')?.textContent || '';
        const phoneText = addressDetails.querySelector('.phone')?.textContent || '';
    
        // Update the delivery address panel
        elements.deliveryAddressPanel.innerHTML = `
            <h4 class="delivery-title">Delivery Address</h4>
            <div class="selected-address">
                <div class="address-type-label">
                    <span class="label label-default">${addressType}</span>
                </div>
                <div class="address-info">
                    <p class="name"><strong>${nameText}</strong></p>
                    <p class="street">${streetText}</p>
                    ${areaText ? `<p class="area">${areaText}</p>` : ''}
                    <p class="city-state">${cityStateText}</p>
                    <p class="phone">${phoneText}</p>
                </div>
                <button type="button" class="btn btn-link change-address" onclick="changeAddress()">
                    Change
                </button>
            </div>
        `;
    }

    // Validate and update place order button state
    function validateOrderButton() {
        const isValid = state.selectedAddress && state.selectedPayment;
        
        if (elements.placeOrderBtn) {
            elements.placeOrderBtn.classList.toggle('disabled', !isValid);
            elements.placeOrderBtn.disabled = !isValid;
            elements.placeOrderBtn.style.backgroundColor = isValid ? '#fac825' : '#6c757d';
            elements.placeOrderBtn.style.cursor = isValid ? 'pointer' : 'not-allowed';
        }
    }

    // Handle order placement
    // async function handlePlaceOrder(e) {
    //     e.preventDefault();
    
    //     // Ensure the form exists in the DOM
    //     if (!elements.placeOrderForm) {
    //         console.error("Place order form not found.");
    //         return;
    //     }
    
    //     // Create a FormData object
    //     const formData = new FormData(elements.placeOrderForm);
    
    //     try {
    //         const response = await fetch(elements.placeOrderForm.action, {
    //             method: 'POST',
    //             body: formData,
    //             headers: {
    //                 'X-CSRFToken': formData.get('csrfmiddlewaretoken'),
    //                 'X-Requested-With': 'XMLHttpRequest'
    //             }
    //         });
    
    //         // Process server response
    //         const responseText = await response.text();
    //         let data;
    
    //         try {
    //             data = JSON.parse(responseText); // Parse response JSON
    //         } catch (err) {
    //             console.error('Invalid JSON response:', responseText);
    //             throw new Error('Server returned invalid JSON');
    //         }
    
    //         if (response.ok && data.success) {
    //             // Redirect or handle success
    //             window.location.href = data.redirect_url || '/order-confirmation';
    //         } else {
    //             throw new Error(data.message || 'Failed to place order');
    //         }
    //     } catch (error) {
    //         console.error('Error placing order:', error);
    //         Swal.fire({
    //             icon: 'error',
    //             title: 'Oops...',
    //             text: error.message || 'Failed to place order. Please try again.'
    //         });
    //     }
    // }

    // Initialize event listeners
    function initializeEventListeners() {
        // Add New Address button handler
        if (elements.addNewAddressBtn) {
            elements.addNewAddressBtn.addEventListener('click', function() {
                toggleAddressForm(!state.isAddingNewAddress);
            });
        }

        // Cancel button handler
        if (elements.cancelBtn) {
            elements.cancelBtn.addEventListener('click', function(e) {
                e.preventDefault();
                toggleAddressForm(false);
            });
        }

        // Address form submission handler
        if (elements.addressForm) {
            elements.addressForm.addEventListener('submit', async function(e) {
                e.preventDefault();
                
                try {
                    const formData = new FormData(this);
                    const response = await fetch(this.action, {
                        method: 'POST',
                        body: formData,
                        headers: {
                            'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                        }
                    });

                    if (response.ok) {
                        window.location.reload();
                    } else {
                        throw new Error('Failed to add address');
                    }
                } catch (error) {
                    console.error('Error adding address:', error);
                    Swal.fire({
                        icon: 'error',
                        title: 'Oops...',
                        text: 'Failed to add address. Please try again.'
                    });
                }
            });
        }

        // Address selection handlers
        elements.addressRadios.forEach(radio => {
            const addressItem = radio.closest('.saved-address-item');
            if (addressItem) {
                addressItem.addEventListener('click', function(e) {
                    if (e.target.type === 'radio') return;
                    
                    radio.checked = true;
                    state.selectedAddress = addressItem;
                    updateDeliveryAddress(addressItem);
                    validateOrderButton();
                });

                // Keyboard accessibility
                addressItem.setAttribute('tabindex', '0');
                addressItem.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        radio.checked = true;
                        state.selectedAddress = addressItem;
                        updateDeliveryAddress(addressItem);
                        validateOrderButton();
                    }
                });
            }
        });

        // Payment selection handlers
        elements.paymentRadios.forEach(radio => {
            radio.addEventListener('change', function() {
                state.selectedPayment = this.value;
                validateOrderButton();
            });
        });

        // Place order button handler
        if (elements.placeOrderBtn) {
            elements.placeOrderBtn.addEventListener('click', handlePlaceOrder);
        }
    }

    // Check if there are any saved addresses
    function checkSavedAddresses() {
        const savedAddresses = document.querySelector('.saved-addresses-list');
        if (!savedAddresses || !savedAddresses.children.length) {
            toggleAddressForm(true);
        }
    }

    // Change address handler (exposed globally for the Change button)
    window.changeAddress = function() {
        state.selectedAddress = null;
        if (elements.deliveryAddressPanel) {
            elements.deliveryAddressPanel.innerHTML = `
                <h4 class="mt-4">Delivery Address</h4>
                <p class="text-muted">Please select a delivery address</p>
            `;
        }
        
        validateOrderButton();

        // Uncheck the selected address radio
        const selectedRadio = document.querySelector('input[name="savedAddress"]:checked');
        if (selectedRadio) {
            selectedRadio.checked = false;
        }
    };

    // Initialize everything
    initializeEventListeners();
    checkSavedAddresses();
});

