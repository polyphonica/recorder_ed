/**
 * Workshop Terms and Conditions Modal Functionality
 * Handles scroll detection, acceptance tracking, and submit button state
 */

// Track whether user has scrolled to bottom
let hasScrolledToBottom = false;
let termsAccepted = false;

// Open terms modal
function openTermsModal() {
    document.getElementById('termsModal').checked = true;
    hasScrolledToBottom = false;
    updateAcceptButton();
}

// Close terms modal
function closeTermsModal() {
    document.getElementById('termsModal').checked = false;
}

// Accept terms
function acceptTerms() {
    if (hasScrolledToBottom) {
        document.getElementById('acceptTerms').checked = true;
        termsAccepted = true;
        updateSubmitButton();
        closeTermsModal();
    }
}

// Update accept button state based on scroll position
function updateAcceptButton() {
    const acceptBtn = document.getElementById('acceptTermsBtn');
    if (hasScrolledToBottom) {
        acceptBtn.disabled = false;
        acceptBtn.classList.remove('btn-disabled');
    } else {
        acceptBtn.disabled = true;
        acceptBtn.classList.add('btn-disabled');
    }
}

// Update submit button state based on terms acceptance
function updateSubmitButton() {
    const submitBtn = document.getElementById('submitBtn');
    const termsCheckbox = document.getElementById('acceptTerms');

    if (termsCheckbox.checked) {
        submitBtn.disabled = false;
        submitBtn.classList.remove('btn-disabled');
    } else {
        submitBtn.disabled = true;
        submitBtn.classList.add('btn-disabled');
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    const termsContent = document.getElementById('termsContent');
    const scrollIndicator = document.getElementById('scrollIndicator');
    const termsCheckbox = document.getElementById('acceptTerms');

    // Check if elements exist (template may not always have them)
    if (!termsContent || !scrollIndicator || !termsCheckbox) {
        return;
    }

    // Check if content is scrollable
    function checkScrollable() {
        if (termsContent.scrollHeight <= termsContent.clientHeight) {
            // Content fits without scrolling
            hasScrolledToBottom = true;
            scrollIndicator.style.display = 'none';
            updateAcceptButton();
        }
    }

    // Scroll detection
    termsContent.addEventListener('scroll', function() {
        const scrolledToBottom = (termsContent.scrollHeight - termsContent.scrollTop) <= (termsContent.clientHeight + 50);

        if (scrolledToBottom && !hasScrolledToBottom) {
            hasScrolledToBottom = true;
            scrollIndicator.style.display = 'none';
            updateAcceptButton();
        }
    });

    // Listen for checkbox changes
    termsCheckbox.addEventListener('change', function() {
        updateSubmitButton();
    });

    // Check scrollable when modal opens
    const modalToggle = document.getElementById('termsModal');
    if (modalToggle) {
        modalToggle.addEventListener('change', function() {
            if (this.checked) {
                setTimeout(checkScrollable, 100);
            }
        });
    }

    // Initial state
    updateSubmitButton();
});
