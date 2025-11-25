/**
 * Workshop Detail Page - Terms and Conditions Handler
 * Syncs a single checkbox to multiple registration forms
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Workshop terms script loading...');

    const termsCheckbox = document.getElementById('workshopTermsCheckbox');
    console.log('Terms checkbox found:', termsCheckbox);

    if (!termsCheckbox) {
        console.log('No terms checkbox - exiting');
        return;
    }

    const registrationForms = document.querySelectorAll('.workshop-registration-form');
    console.log('Registration forms found:', registrationForms.length);

    // Handle form submission - add terms_accepted based on checkbox state
    registrationForms.forEach((form, index) => {
        console.log('Attaching listener to form', index, form);

        form.addEventListener('submit', function(e) {
            console.log('Form submitted! Checkbox checked:', termsCheckbox.checked);

            if (!termsCheckbox.checked) {
                console.log('Preventing submission - terms not accepted');
                e.preventDefault();
                alert('Please accept the Terms and Conditions before registering.');
                termsCheckbox.focus();
                return false;
            }

            console.log('Terms accepted - adding hidden input');

            // Find or create the terms_accepted input in this form
            let termsInput = form.querySelector('input[name="terms_accepted"]');
            if (termsInput) {
                console.log('Found existing terms_accepted input, updating value');
                termsInput.value = 'true';
            } else {
                console.log('Creating new terms_accepted input');
                termsInput = document.createElement('input');
                termsInput.type = 'hidden';
                termsInput.name = 'terms_accepted';
                termsInput.value = 'true';
                form.appendChild(termsInput);
            }

            console.log('Form will now submit with terms_accepted =', termsInput.value);
        });
    });

    console.log('Workshop terms script initialized successfully');
});
