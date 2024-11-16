document.getElementById("addNewAddressBtn").addEventListener("click", function() {
    $('#savedAddressesSection').fadeOut();

    $('#newAddressFormSection').fadeIn();

    $('#addNewAddressBtn').fadeOut();
});

document.querySelector(".btn-cancel").addEventListener("click", function(e) {
    e.preventDefault();

    $('#newAddressFormSection').fadeOut();

    $('#savedAddressesSection').fadeIn();

    $('#addNewAddressBtn').fadeIn();
});