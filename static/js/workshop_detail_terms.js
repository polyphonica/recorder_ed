/**
 * Workshop Detail Page - Simple Terms and Conditions Checkbox Handler
 * Enables/disables registration buttons based on terms acceptance checkbox
 */

document.addEventListener('DOMContentLoaded', function() {
    const termsCheckbox = document.getElementById('workshopTermsAccepted');
    const submitButtons = document.querySelectorAll('.workshop-submit-btn');
    const termsInputs = document.querySelectorAll('.terms-accepted-input');

    console.log('Terms acceptance script loaded');
    console.log('Found checkbox:', termsCheckbox);
    console.log('Found buttons:', submitButtons.length);
    console.log('Found inputs:', termsInputs.length);

    // Only run if checkbox exists (for authenticated non-instructor users)
    if (!termsCheckbox) {
        console.log('No terms checkbox found, exiting');
        return;
    }

    // Update all submit buttons and hidden inputs when checkbox changes
    termsCheckbox.addEventListener('change', function() {
        const isChecked = this.checked;
        console.log('Checkbox changed, isChecked:', isChecked);

        // Enable/disable all registration buttons
        submitButtons.forEach(button => {
            console.log('Updating button:', button);
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
            console.log('Updated input value:', input.value);
        });
    });

    // Initial state - disable all buttons until terms are accepted
    submitButtons.forEach(button => {
        button.disabled = true;
        button.classList.add('btn-disabled');
        console.log('Initially disabled button:', button);
    });
});
