/**
 * Workshop Detail Page - Terms and Conditions for "Add to Cart"
 * Intercepts direct "Add to Cart" buttons and requires T&Cs acceptance first
 */

let termsAcceptedForCart = false;
let pendingCartForm = null;

// Accept terms specifically for cart
function acceptTermsForCart() {
    if (hasScrolledToBottom) {
        termsAcceptedForCart = true;
        localStorage.setItem('workshop_terms_accepted', 'true');
        document.getElementById('termsModal').checked = false;

        // If there's a pending form submission, submit it now
        if (pendingCartForm) {
            pendingCartForm.submit();
            pendingCartForm = null;
        }
    }
}

// Check if terms have been accepted (persisted in localStorage for session)
function checkTermsAccepted() {
    return localStorage.getItem('workshop_terms_accepted') === 'true' || termsAcceptedForCart;
}

// Intercept all "Add to Cart" form submissions
document.addEventListener('DOMContentLoaded', function() {
    // Find all "Add to Cart" forms
    const addToCartForms = document.querySelectorAll('form[action*="add_to_cart"]');

    addToCartForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!checkTermsAccepted()) {
                e.preventDefault();
                pendingCartForm = form;

                // Open terms modal
                document.getElementById('termsModal').checked = true;

                // Show message
                const alert = document.createElement('div');
                alert.className = 'alert alert-info mb-4';
                alert.innerHTML = `
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    <span>Please review and accept our Terms and Conditions before adding workshops to your cart.</span>
                `;

                // Insert alert before modal content
                const modalBox = document.querySelector('.modal-box');
                const termsContent = document.getElementById('termsContent');
                if (modalBox && termsContent && !document.querySelector('.alert-info')) {
                    modalBox.insertBefore(alert, termsContent);
                }
            }
            // If terms accepted, allow form to submit normally
        });
    });
});
