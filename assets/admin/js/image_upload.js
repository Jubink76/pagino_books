function previewImages(event) {
    const imagePreviewContainer = document.getElementById('image-preview-container');
    const errorMessage = document.getElementById('error-message');
  
    // Clear previous previews
    imagePreviewContainer.innerHTML = '';
  
    // Loop through the selected files
    for (let i = 0; i < event.target.files.length; i++) {
      const file = event.target.files[i];
  
      // Resize the image
      resizeImage(file, 240, 240)
        .then((resizedImage) => {
          // Display the resized image preview
          const preview = document.createElement('img');
          preview.src = URL.createObjectURL(resizedImage);
          preview.alt = 'Uploaded Image';
          preview.classList.add('img-fluid', 'rounded');
          imagePreviewContainer.appendChild(preview);
        })
        .catch((error) => {
          // Display an error message if image resizing fails
          errorMessage.textContent = 'Error uploading images. Please try again.';
          errorMessage.classList.remove('d-none');
        });
    }
  
    // Show an error message if the file size is not within the allowed range
    if (event.target.files.length > 4) {
      errorMessage.textContent = 'Maximum of 4 images can be uploaded.';
      errorMessage.classList.remove('d-none');
    } else {
      errorMessage.classList.add('d-none');
    }
  }
  
  function resizeImage(file, maxWidth, maxHeight) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.src = URL.createObjectURL(file);
      img.onload = () => {
        let width = img.width;
        let height = img.height;
  
        if (width > height) {
          if (width > maxWidth) {
            height *= maxWidth / width;
            width = maxWidth;
          }
        } else {
          if (height > maxHeight) {
            width *= maxHeight / height;
            height = maxHeight;
          }
        }
  
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, width, height);
  
        canvas.toBlob((blob) => {
          resolve(blob);
        }, 'image/jpeg', 0.9);
      };
      img.onerror = () => {
        reject(new Error('Error uploading image.'));
      };
    });
  }