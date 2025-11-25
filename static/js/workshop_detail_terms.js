/**
 * Workshop Detail Page - Terms and Conditions for "Add to Cart"
 * Intercepts direct "Add to Cart" buttons and requires T&Cs acceptance first
 *
 * This is a self-contained script that doesn't depend on workshop_terms.js
 */

let termsAcceptedForCart = false;
let pendingCartForm = null;
let hasScrolledToBottomForCart = false;

// Accept terms specifically for cart
function acceptTermsForCart() {
    if (hasScrolledToBottomForCart) {
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

// Update the accept button state
function updateAcceptButtonForCart() {
    const acceptBtn = document.getElementById('acceptTermsBtn');
    if (acceptBtn) {
        if (hasScrolledToBottomForCart) {
            acceptBtn.disabled = false;
            acceptBtn.classList.remove('btn-disabled');
        } else {
            acceptBtn.disabled = true;
            acceptBtn.classList.add('btn-disabled');
        }
    }
}

// Initialize scroll detection for the modal
function initializeScrollDetection() {
    const termsContent = document.getElementById('termsContent');
    const scrollIndicator = document.getElementById('scrollIndicator');

    if (!termsContent || !scrollIndicator) return;

    // Check if content is scrollable
    function checkScrollable() {
        if (termsContent.scrollHeight <= termsContent.clientHeight) {
            // Content fits without scrolling
            hasScrolledToBottomForCart = true;
            scrollIndicator.style.display = 'none';
            updateAcceptButtonForCart();
        }
    }

    // Scroll detection
    termsContent.addEventListener('scroll', function() {
        const scrolledToBottom = (termsContent.scrollHeight - termsContent.scrollTop) <= (termsContent.clientHeight + 50);

        if (scrolledToBottom && !hasScrolledToBottomForCart) {
            hasScrolledToBottomForCart = true;
            scrollIndicator.style.display = 'none';
            updateAcceptButtonForCart();
        }
    });

    // Check scrollable when modal opens
    const modalToggle = document.getElementById('termsModal');
    if (modalToggle) {
        modalToggle.addEventListener('change', function() {
            if (this.checked) {
                // Reset scroll state when modal opens
                hasScrolledToBottomForCart = false;
                scrollIndicator.style.display = '';
                updateAcceptButtonForCart();
                setTimeout(checkScrollable, 100);
            }
        });
    }

    // Initial check
    updateAcceptButtonForCart();
}

// Intercept all "Add to Cart" form submissions
document.addEventListener('DOMContentLoaded', function() {
    // Initialize scroll detection
    initializeScrollDetection();

    // Find all "Add to Cart" and "Add Series to Cart" forms
    const addToCartForms = document.querySelectorAll('form[action*="cart/add"], form[action*="add-series"]');

    console.log('Found', addToCartForms.length, 'add to cart forms (including series)'); // Debug log

    addToCartForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!checkTermsAccepted()) {
                e.preventDefault();
                pendingCartForm = form;

                console.log('Terms not accepted, showing modal'); // Debug log

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
            } else {
                console.log('Terms already accepted, submitting form'); // Debug log
            }
            // If terms accepted, allow form to submit normally
        });
    });
});
