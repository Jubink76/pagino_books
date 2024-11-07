
    $(document).ready(function() {
		// Initialize Owl Carousel for the main product and thumbnails
		$("#owl-single-product").owlCarousel({
			items: 1,
			navigation: true,
			pagination: false,
		});
	
		$("#owl-single-product-thumbnails").owlCarousel({
			items: 4,
		});
	
		// Zoom and pan effect on main image
		const zoomImages = document.querySelectorAll("#owl-single-product .single-product-gallery-item img");
	
		zoomImages.forEach((img) => {
			img.addEventListener("mouseenter", function() {
				img.style.transform = "scale(1.5)";
			});
	
			img.addEventListener("mousemove", function(event) {
				const rect = img.getBoundingClientRect();
				const x = event.clientX - rect.left;
				const y = event.clientY - rect.top;
	
				const xPercent = (x / rect.width) * 100;
				const yPercent = (y / rect.height) * 100;
	
				img.style.transformOrigin = `${xPercent}% ${yPercent}%`;
			});
	
			img.addEventListener("mouseleave", function() {
				img.style.transform = "scale(1)";
				img.style.transformOrigin = "center center";
			});
		});
	
		// Change main image on thumbnail click
		$("#owl-single-product-thumbnails").on("click", ".horizontal-thumb", function(event) {
			event.preventDefault();
	
			// Get the URL of the clicked thumbnail's image
			const newImageUrl = $(this).data("image");
	
			// Find the main image element and update its src
			$("#owl-single-product .single-product-gallery-item img").attr("src", newImageUrl);
			$("#owl-single-product .single-product-gallery-item img").attr("data-zoom-image", newImageUrl);
	
			// Update zoom effect by reinitializing the zoom events
			zoomImages.forEach((img) => {
				img.style.transform = "scale(1)";
				img.style.transformOrigin = "center center";
			});
		});
	});
