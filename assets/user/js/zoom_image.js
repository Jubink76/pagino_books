document.addEventListener('DOMContentLoaded', function () {
	function initImageZoom(container) {
	  const mainImage = container.querySelector('#main-image');
	  const zoomContainer = container.querySelector('.image-zoom-container');
  
	  // Reset styles for proper positioning
	  zoomContainer.style.position = 'relative';
	  zoomContainer.style.overflow = 'hidden';
	  mainImage.style.transition = 'transform 0.3s ease-out';
	  mainImage.style.transformOrigin = 'center center';
  
	  // Add event listeners for zoom effect
	  zoomContainer.addEventListener('mousemove', function (e) {
		const rect = zoomContainer.getBoundingClientRect();
		const mouseX = e.clientX - rect.left;
		const mouseY = e.clientY - rect.top;
  
		const zoomLevel = 2.5; // Adjust zoom level here
		const offsetX = Math.min(
		  Math.max((mouseX / rect.width) * 100, 0),
		  100
		); // Clamp between 0 and 100
		const offsetY = Math.min(
		  Math.max((mouseY / rect.height) * 100, 0),
		  100
		);
  
		mainImage.style.transform = `
		  scale(${zoomLevel}) 
		  translate(${50 - offsetX}%, ${50 - offsetY}%)
		`;
		mainImage.style.cursor = 'zoom-in';
	  });
  
	  zoomContainer.addEventListener('mouseleave', function () {
		mainImage.style.transform = 'scale(1) translate(-50%, -50%)';
		mainImage.style.cursor = 'default';
	  });
  
	  // Ensure image maintains aspect ratio and fits container
	  mainImage.style.maxWidth = '100%';
	  mainImage.style.maxHeight = '100%';
	  mainImage.style.objectFit = 'contain';
	}
  
	function initThumbnails() {
	  const thumbnails = document.querySelectorAll(
		'.single-product-gallery-thumbs a'
	  );
	  const mainImage = document.getElementById('main-image');
  
	  thumbnails.forEach((thumbnail) => {
		thumbnail.addEventListener('click', function (e) {
		  e.preventDefault();
		  thumbnails.forEach((t) => t.classList.remove('active'));
		  this.classList.add('active');
  
		  const newImageSrc = this.getAttribute('data-image');
		  mainImage.style.opacity = 0;
  
		  setTimeout(() => {
			mainImage.src = newImageSrc;
			mainImage.setAttribute('data-zoom-image', newImageSrc);
			mainImage.style.transform = 'scale(1) translate(-50%, -50%)'; // Reset transform on image change
			mainImage.style.opacity = 1;
		  }, 300);
		});
	  });
	}
  
	const productGallery = document.getElementById('product-gallery');
	if (productGallery) {
	  initImageZoom(productGallery);
	  initThumbnails();
	}
  });	  
  