// Enhanced form handling for Piece creation/editing with stem formsets
// Works with Django inline formsets

document.addEventListener('DOMContentLoaded', function() {
    console.log('Piece form JavaScript loaded');

    // Style formset rows
    const formsetRows = document.querySelectorAll('.stem-form-row, .inline-related');
    formsetRows.forEach(row => {
        row.style.backgroundColor = '#f9f9f9';
        row.style.padding = '15px';
        row.style.marginBottom = '15px';
        row.style.borderRadius = '4px';
        row.style.borderLeft = '3px solid rgb(139, 81, 143)';
    });

    // Add confirmation for delete checkboxes
    const deleteCheckboxes = document.querySelectorAll('input[name$="-DELETE"]');
    deleteCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            if (this.checked) {
                const row = this.closest('.stem-form-row, .inline-related');
                if (row) {
                    row.style.opacity = '0.5';
                    row.style.borderLeft = '3px solid #c0392b';
                }
            } else {
                const row = this.closest('.stem-form-row, .inline-related');
                if (row) {
                    row.style.opacity = '1';
                    row.style.borderLeft = '3px solid rgb(139, 81, 143)';
                }
            }
        });
    });

    // File input styling feedback
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            if (this.files.length > 0) {
                const fileName = this.files[0].name;
                const feedback = document.createElement('small');
                feedback.textContent = `Selected: ${fileName}`;
                feedback.style.color = '#27ae60';
                feedback.style.display = 'block';
                feedback.style.marginTop = '5px';

                // Remove existing feedback
                const existingFeedback = this.parentNode.querySelector('small');
                if (existingFeedback) {
                    existingFeedback.remove();
                }

                this.parentNode.appendChild(feedback);
            }
        });
    });

    // Form validation
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            let isValid = true;
            const requiredFields = form.querySelectorAll('[required]');

            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.style.borderColor = '#c0392b';
                } else {
                    field.style.borderColor = '';
                }
            });

            if (!isValid) {
                e.preventDefault();
                alert('Please fill in all required fields');
            }
        });
    }
});
