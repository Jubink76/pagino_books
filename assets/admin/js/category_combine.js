document.addEventListener('DOMContentLoaded', function () {
    const offerButtonsContainer = document.querySelector('.categories-container');

    // Attach click event listeners to offer buttons
    if (offerButtonsContainer) {
        offerButtonsContainer.addEventListener('click', handleOfferActions);
    }

    function handleOfferActions(event) {
        const button = event.target.closest('button');
        if (!button) return;

        const categoryId = button.dataset.categoryId;

        if (button.classList.contains('add-offer-btn')) {
            showOfferForm('add', categoryId);
        } else if (button.classList.contains('edit-offer-btn')) {
            fetchOfferData(categoryId).then((offer) => showOfferForm('edit', categoryId, offer));
        } else if (button.classList.contains('delete-offer-btn')) {
            confirmDeleteOffer(categoryId);
        }
    }

    function showOfferForm(action, categoryId, offer = null) {
        Swal.fire({
            title: action === 'add' ? 'Add Offer' : 'Edit Offer',
            html: `
                <form id="offerForm" class="text-left">
                    <div class="mb-3">
                        <label for="offerName">Offer Name</label>
                        <input type="text" id="offerName" class="swal2-input" required 
                               value="${offer ? offer.offer_name : ''}">
                    </div>
                    <div class="mb-3">
                        <label for="discountType">Discount Type</label>
                        <select id="discountType" class="swal2-input">
                            <option value="percentage" ${offer?.discount_type === 'percentage' ? 'selected' : ''}>
                                Percentage
                            </option>
                            <option value="fixed" ${offer?.discount_type === 'fixed' ? 'selected' : ''}>
                                Fixed Amount
                            </option>
                            <option value="bogo" ${offer?.discount_type === 'bogo' ? 'selected' : ''}>
                                Buy One Get One
                            </option>
                            <option value="bundle" ${offer?.discount_type === 'bundle' ? 'selected' : ''}>
                                Bundle Discount
                            </option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label for="discountValue">Discount Value</label>
                        <input type="number" id="discountValue" class="swal2-input" required min="0"
                               value="${offer ? offer.discount_value : ''}">
                    </div>
                    <div class="mb-3">
                        <label for="validFrom">Valid From</label>
                        <input type="datetime-local" id="validFrom" class="swal2-input" required
                               value="${offer ? formatDateTimeLocal(offer.valid_from) : ''}">
                    </div>
                    <div class="mb-3">
                        <label for="validTo">Valid To</label>
                        <input type="datetime-local" id="validTo" class="swal2-input" required
                               value="${offer ? formatDateTimeLocal(offer.valid_to) : ''}">
                    </div>
                    <div class="mb-3">
                        <label for="description">Description</label>
                        <textarea id="description" class="swal2-textarea">${offer ? offer.description : ''}</textarea>
                    </div>
                </form>
            `,
            showCancelButton: true,
            confirmButtonText: action === 'add' ? 'Add Offer' : 'Update Offer',
            preConfirm: () => validateAndGetFormData(),
        }).then((result) => {
            if (result.isConfirmed) {
                if (action === 'add') {
                    submitOffer(categoryId, result.value, 'add');
                } else {
                    submitOffer(categoryId, result.value, 'edit');
                }
            }
        });
    }

    function validateAndGetFormData() {
        const offerName = document.getElementById('offerName').value;
        const discountType = document.getElementById('discountType').value;
        const discountValue = document.getElementById('discountValue').value;
        const validFrom = document.getElementById('validFrom').value;
        const validTo = document.getElementById('validTo').value;
        const description = document.getElementById('description').value;

        if (!offerName || !discountType || !discountValue || !validFrom || !validTo) {
            Swal.showValidationMessage('Please fill in all required fields');
            return false;
        }

        if (new Date(validFrom) >= new Date(validTo)) {
            Swal.showValidationMessage('Valid To date must be after Valid From date');
            return false;
        }

        return {
            offer_name: offerName,
            discount_type: discountType,
            discount_value: parseFloat(discountValue),
            valid_from: validFrom,
            valid_to: validTo,
            description,
        };
    }

    function submitOffer(categoryId, offerData, action) {
        const url = action === 'add' ? `/offers/add/${categoryId}/` : `/offers/edit/${categoryId}/`;
        const method = action === 'add' ? 'POST' : 'PUT';

        fetch(url, {
            method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(offerData),
        })
            .then((response) => response.json())
            .then((data) => {
                Swal.fire({
                    icon: 'success',
                    title: action === 'add' ? 'Offer added successfully!' : 'Offer updated successfully!',
                }).then(() => location.reload());
            })
            .catch((error) => {
                Swal.fire({
                    icon: 'error',
                    title: 'Error',
                    text: 'Failed to process the request. Please try again.',
                });
            });
    }

    function confirmDeleteOffer(categoryId) {
        Swal.fire({
            title: 'Are you sure?',
            text: 'This action will delete the offer permanently!',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#d33',
            cancelButtonColor: '#3085d6',
            confirmButtonText: 'Yes, delete it!',
            cancelButtonText: 'Cancel',
        }).then((result) => {
            if (result.isConfirmed) {
                deleteOffer(categoryId);
            }
        });
    }

    function deleteOffer(categoryId) {
        fetch(`/offers/delete/${categoryId}/`, { method: 'DELETE' })
            .then((response) => response.json())
            .then((data) => {
                Swal.fire({
                    icon: 'success',
                    title: 'Offer deleted successfully!',
                }).then(() => location.reload());
            })
            .catch((error) => {
                Swal.fire({
                    icon: 'error',
                    title: 'Error',
                    text: 'Failed to delete offer. Please try again.',
                });
            });
    }

    function fetchOfferData(categoryId) {
        return fetch(`/offers/get/${categoryId}/`)
            .then((response) => response.json())
            .catch((error) => {
                Swal.fire({
                    icon: 'error',
                    title: 'Error',
                    text: 'Failed to fetch offer data.',
                });
                return null;
            });
    }

    function formatDateTimeLocal(dateString) {
        const date = new Date(dateString);
        return date.toISOString().slice(0, 16);
    }
});
