document.addEventListener('DOMContentLoaded', function() {
    // Existing functionality for address management
    const savedAddressesSection = document.getElementById('savedAddressesSection');
    const newAddressFormSection = document.getElementById('newAddressFormSection');
    const addNewAddressBtn = document.getElementById('addNewAddressBtn');
    const savedAddressItems = document.querySelectorAll('.saved-address-item');
    const deliveryAddressSection = document.querySelector('.delivery-address');
    const previewAddress = document.querySelector('.preview-address') || createPreviewAddress();

    // New elements for checkout validation
    const addressRadios = document.querySelectorAll('input[name="savedAddress"]');
    const paymentRadios = document.querySelectorAll('input[name="payment"]');
    const placeOrderBtn = document.querySelector('.btn-place-order');

    // Initialize preview address section
    function createPreviewAddress() {
        const previewDiv = document.createElement('div');
        previewDiv.className = 'preview-address';
        deliveryAddressSection.appendChild(previewDiv);
        return previewDiv;
    }

    // Function to check selections and update button state
    function updatePlaceOrderButton() {
        const isAddressSelected = Array.from(addressRadios).some(radio => radio.checked);
        const isPaymentSelected = Array.from(paymentRadios).some(radio => radio.checked);

        if (isAddressSelected && isPaymentSelected) {
            placeOrderBtn.classList.remove('disabled');
            placeOrderBtn.removeAttribute('disabled');
        } else {
            placeOrderBtn.classList.add('disabled');
            placeOrderBtn.setAttribute('disabled', '');
        }
    }

    // Handle address selection
    savedAddressItems.forEach(item => {
        item.addEventListener('click', function() {
            // Remove selection from all items
            savedAddressItems.forEach(addr => addr.classList.remove('selected'));
            
            // Add selection to clicked item
            this.classList.add('selected');
            
            // Find and check the radio button within this address item
            const radio = this.querySelector('input[type="radio"]');
            if (radio) {
                radio.checked = true;
                // Trigger the place order button update
                updatePlaceOrderButton();
            }
            
            // Update the delivery address preview
            updateDeliveryAddress(this);
        });
    });

    // Function to update delivery address preview
    function updateDeliveryAddress(selectedAddress) {
        const addressContent = selectedAddress.querySelector('.address-details').cloneNode(true);
        
        // Clear and update preview
        previewAddress.innerHTML = '';
        previewAddress.appendChild(addressContent);
        
        // Show preview and update section styles
        previewAddress.classList.add('active');
        deliveryAddressSection.classList.add('has-address');
        
        // Update or hide the placeholder text
        const textMuted = deliveryAddressSection.querySelector('.text-muted');
        if (textMuted) {
            textMuted.style.display = 'none';
        }

        // Smooth scroll to delivery address section on mobile
        if (window.innerWidth < 768) {
            deliveryAddressSection.scrollIntoView({ behavior: 'smooth' });
        }
    }

    // Handle "Add New Address" button
    addNewAddressBtn?.addEventListener('click', function() {
        savedAddressesSection.style.display = 'none';
        newAddressFormSection.style.display = 'block';
        addNewAddressBtn.style.display = 'none';
    });

    // Handle address form submission
    document.querySelector('.address-form')?.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        if (validateForm()) {
            const formData = new FormData(this);
            try {
                const response = await fetch('/api/save-address/', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    }
                });
                
                if (response.ok) {
                    window.location.reload();
                }
            } catch (error) {
                console.error('Error saving address:', error);
            }
        }
    });

    // Handle form cancellation
    window.cancelNewAddress = function() {
        const hasExistingAddresses = document.querySelector('.saved-address-item');
        if (hasExistingAddresses) {
            savedAddressesSection.style.display = 'block';
            addNewAddressBtn.style.display = 'block';
            newAddressFormSection.style.display = 'none';
        }
    };

    // Address type selector functionality
    document.querySelectorAll('.type-option').forEach(option => {
        option.addEventListener('click', () => {
            document.querySelectorAll('.type-option').forEach(opt => 
                opt.classList.remove('active')
            );
            option.classList.add('active');
        });
    });

    // Add change event listeners for checkout validation
    addressRadios.forEach(radio => {
        radio.addEventListener('change', updatePlaceOrderButton);
    });

    paymentRadios.forEach(radio => {
        radio.addEventListener('change', updatePlaceOrderButton);
    });

    // Initial check when page loads
    updatePlaceOrderButton();
});

function validateForm() {
    // Add your form validation logic here
    return true;
}