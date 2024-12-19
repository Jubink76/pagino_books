document.addEventListener('DOMContentLoaded', function() {
    const messageContainer = document.getElementById('message-container');
    if (messageContainer) {
        const alerts = messageContainer.getElementsByClassName('alert');
        
        Array.from(alerts).forEach(alert => {
            // Set initial state
            alert.style.opacity = '1';
            alert.style.transform = 'translateX(0)';
            
            // Auto-dismiss after 3 seconds
            setTimeout(() => {
                dismissAlert(alert);
            }, 3000);

            // Close button handler
            const closeButton = alert.querySelector('.btn-close');
            if (closeButton) {
                closeButton.addEventListener('click', (e) => {
                    e.preventDefault();
                    dismissAlert(alert);
                });
            }
        });
    }
});

function dismissAlert(alert) {
    // Add fade out animation
    alert.style.opacity = '0';
    alert.style.transform = 'translateX(100%)';
    
    // Remove the alert after animation
    setTimeout(() => {
        if (alert.parentElement) {
            alert.parentElement.removeChild(alert);
            
            // Remove container if empty
            const container = document.getElementById('message-container');
            if (container && container.children.length === 0) {
                container.remove();
            }
        }
    }, 300);
}