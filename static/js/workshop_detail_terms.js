/**
 * Workshop Detail Page - Simple Terms and Conditions Checkbox Handler
 * Enables/disables registration buttons based on terms acceptance checkbox
 */

document.addEventListener('DOMContentLoaded', function() {
    const termsCheckbox = document.getElementById('workshopTermsAccepted');
    const submitButtons = document.querySelectorAll('.workshop-submit-btn');
    const termsInputs = document.querySelectorAll('.terms-accepted-input');

    // Only run if checkbox exists (for authenticated non-instructor users)
    if (!termsCheckbox) {
        return;
    }

    // Update all submit buttons and hidden inputs when checkbox changes
    termsCheckbox.addEventListener('change', function() {
        const isChecked = this.checked;

        // Enable/disable all registration buttons
        submitButtons.forEach(button => {
            button.disabled = !isChecked;
            if (isChecked) {
                button.classList.remove('btn-disabled');
            } else {
                button.classList.add('btn-disabled');
            }
        });

        // Update all hidden terms_accepted inputs
        termsInputs.forEach(input => {
            input.value = isChecked ? 'true' : 'false';
        });
    });

    // Initial state - disable all buttons until terms are accepted
    submitButtons.forEach(button => {
        button.disabled = true;
        button.classList.add('btn-disabled');
    });
});
