// Array of product data
const products = [
    { id: 1, name: 'Product 1', price: 600, discount: 49, imageUrl: '/api/placeholder/240/240' },
    { id: 2, name: 'Product 2', price: 800, discount: 25, imageUrl: '/api/placeholder/240/240' },
    // Add more products here
  ];
  
  // Get references to UI elements
  const productImage = document.getElementById('product-image');
  const productName = document.getElementById('product-name');
  const productPrice = document.getElementById('product-price');
  const productDiscount = document.getElementById('product-discount');
  const timerDays = document.getElementById('timer-days');
  const timerHours = document.getElementById('timer-hours');
  const timerMinutes = document.getElementById('timer-minutes');
  const timerSeconds = document.getElementById('timer-seconds');
  const addToCartButton = document.getElementById('add-to-cart');
  
  let currentProductIndex = 0;
  let timerInterval;
  let timerEndTime;
  
  function updateProductDisplay() {
    const currentProduct = products[currentProductIndex];
  
    productImage.src = currentProduct.imageUrl;
    productName.textContent = currentProduct.name;
    productPrice.textContent = `$${currentProduct.price.toFixed(2)}`;
    productDiscount.textContent = `${currentProduct.discount}% OFF`;
  
    // Reset the timer to 1 day
    timerEndTime = new Date().getTime() + 24 * 60 * 60 * 1000;
    updateTimer();
  
    // Activate the add to cart button
    addToCartButton.disabled = false;
  
    // Start the timer
    clearInterval(timerInterval);
    timerInterval = setInterval(() => {
      updateTimer();
    }, 1000);
  }
  
  function updateTimer() {
    const currentTime = new Date().getTime();
    const timeRemaining = timerEndTime - currentTime;
  
    if (timeRemaining <= 0) {
      // Timer has reached 0, move to the next product
      clearInterval(timerInterval);
      currentProductIndex = (currentProductIndex + 1) % products.length;
      updateProductDisplay();
      return;
    }
  
    const days = Math.floor(timeRemaining / (24 * 60 * 60 * 1000));
    const hours = Math.floor((timeRemaining % (24 * 60 * 60 * 1000)) / (60 * 60 * 1000));
    const minutes = Math.floor((timeRemaining % (60 * 60 * 1000)) / (60 * 1000));
    const seconds = Math.floor((timeRemaining % (60 * 1000)) / 1000);
  
    timerDays.textContent = days.toString().padStart(3, '0');
    timerHours.textContent = hours.toString().padStart(2, '0');
    timerMinutes.textContent = minutes.toString().padStart(2, '0');
    timerSeconds.textContent = seconds.toString().padStart(2, '0');
  }
  
  // Initial product display
  updateProductDisplay();
  
  // Next button click handler
  document.getElementById('next-button').addEventListener('click', () => {
    currentProductIndex = (currentProductIndex + 1) % products.length;
    updateProductDisplay();
  });