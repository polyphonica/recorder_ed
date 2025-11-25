/**
 * Workshop Detail Page - Terms and Conditions Handler
 * Syncs a single checkbox to multiple registration forms
 */

document.addEventListener('DOMContentLoaded', function() {
    const termsCheckbox = document.getElementById('workshopTermsCheckbox');

    if (!termsCheckbox) {
        // No terms checkbox on page (user not authenticated or is instructor)
        return;
    }

    const registrationForms = document.querySelectorAll('.workshop-registration-form');

    // Handle form submission - add terms_accepted based on checkbox state
    registrationForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!termsCheckbox.checked) {
                e.preventDefault();
                alert('Please accept the Terms and Conditions before registering.');
                termsCheckbox.focus();
                return false;
            }

            // Find or create the terms_accepted input in this form
            let termsInput = form.querySelector('input[name="terms_accepted"]');
            if (termsInput) {
                termsInput.value = 'true';
            } else {
                // Create it if it doesn't exist
                termsInput = document.createElement('input');
                termsInput.type = 'hidden';
                termsInput.name = 'terms_accepted';
                termsInput.value = 'true';
                form.appendChild(termsInput);
            }
        });
    });
});
