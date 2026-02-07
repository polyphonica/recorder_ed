// Enhanced form handling for Piece creation/editing with stem formsets
// Works with Django inline formsets

// File size limits (in bytes) - must match server limits
const FILE_SIZE_LIMITS = {
    audio: 15 * 1024 * 1024,      // 15MB per audio file
    image: 5 * 1024 * 1024,       // 5MB for sheet music image
    pdf: 5 * 1024 * 1024,         // 5MB for PDF score
    totalUpload: 50 * 1024 * 1024 // 50MB total (nginx limit is 50MB)
};

// Format bytes to human-readable size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Validate file sizes and return error messages
function validateFileSizes(form) {
    const errors = [];
    let totalSize = 0;

    // Check audio files (stems)
    const audioInputs = form.querySelectorAll('input[type="file"][name*="audio_file"]');
    audioInputs.forEach((input, index) => {
        if (input.files && input.files[0]) {
            const file = input.files[0];
            totalSize += file.size;
            if (file.size > FILE_SIZE_LIMITS.audio) {
                errors.push(`Audio file "${file.name}" is too large (${formatFileSize(file.size)}). Maximum allowed: ${formatFileSize(FILE_SIZE_LIMITS.audio)}`);
            }
        }
    });

    // Check sheet music image
    const imageInput = form.querySelector('input[type="file"][name="svg_image"]');
    if (imageInput && imageInput.files && imageInput.files[0]) {
        const file = imageInput.files[0];
        totalSize += file.size;
        if (file.size > FILE_SIZE_LIMITS.image) {
            errors.push(`Sheet music image "${file.name}" is too large (${formatFileSize(file.size)}). Maximum allowed: ${formatFileSize(FILE_SIZE_LIMITS.image)}`);
        }
    }

    // Check PDF score
    const pdfInput = form.querySelector('input[type="file"][name="pdf_score"]');
    if (pdfInput && pdfInput.files && pdfInput.files[0]) {
        const file = pdfInput.files[0];
        totalSize += file.size;
        if (file.size > FILE_SIZE_LIMITS.pdf) {
            errors.push(`PDF score "${file.name}" is too large (${formatFileSize(file.size)}). Maximum allowed: ${formatFileSize(FILE_SIZE_LIMITS.pdf)}`);
        }
    }

    // Check total upload size
    if (totalSize > FILE_SIZE_LIMITS.totalUpload) {
        errors.push(`Total upload size (${formatFileSize(totalSize)}) exceeds the maximum allowed (${formatFileSize(FILE_SIZE_LIMITS.totalUpload)}). Please compress your audio files or upload fewer files at once.`);
    }

    return errors;
}

// Show error modal/alert with file size errors
function showFileSizeErrors(errors) {
    // Create a more user-friendly error display
    const errorMessage = 'Your files are too large to upload:\n\n' +
        errors.map(e => '• ' + e).join('\n') +
        '\n\nPlease compress your audio files (try using a lower bitrate like 128kbps) and try again.';

    alert(errorMessage);
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('Piece form JavaScript loaded');

    // Handle composer toggle
    const composerToggle = document.getElementById('new-composer-toggle');
    if (composerToggle) {
        composerToggle.addEventListener('change', function() {
            // Find the content div - it's the next sibling after the label
            const label = this.nextElementSibling;
            const contentDiv = label ? label.nextElementSibling : null;
            if (contentDiv) {
                if (this.checked) {
                    contentDiv.classList.remove('hidden');
                } else {
                    contentDiv.classList.add('hidden');
                }
            }
        });
    }

    // Handle tags toggle
    const tagsToggle = document.getElementById('new-tags-toggle');
    if (tagsToggle) {
        tagsToggle.addEventListener('change', function() {
            // Find the content div - it's the next sibling after the label
            const label = this.nextElementSibling;
            const contentDiv = label ? label.nextElementSibling : null;
            if (contentDiv) {
                if (this.checked) {
                    contentDiv.classList.remove('hidden');
                } else {
                    contentDiv.classList.add('hidden');
                }
            }
        });
    }

    // Add Stem Button Functionality
    const addStemButton = document.getElementById('add-stem-button');
    const totalFormsInput = document.getElementById('id_stems-TOTAL_FORMS');
    const stemTemplate = document.getElementById('stem-form-template');
    const stemContainer = document.getElementById('stem-formset-container');

    if (addStemButton && totalFormsInput && stemContainer) {
        addStemButton.addEventListener('click', function() {
            const totalForms = parseInt(totalFormsInput.value);
            let newForm;

            // Use template to create new form
            if (stemTemplate) {
                newForm = stemTemplate.content.cloneNode(true).querySelector('.stem-form-row');
                // Replace __prefix__ with actual index
                newForm.innerHTML = newForm.innerHTML.replace(/__prefix__/g, totalForms);
            } else {
                // Fallback: clone existing form if template not available
                const currentForms = document.querySelectorAll('.stem-form-row');
                if (currentForms.length === 0) {
                    console.error('No stem form template or existing forms to clone');
                    return;
                }
                const lastForm = currentForms[currentForms.length - 1];
                newForm = lastForm.cloneNode(true);

                // Update form index in all fields
                const formRegex = new RegExp('stems-\\d+-', 'g');
                newForm.innerHTML = newForm.innerHTML.replace(formRegex, 'stems-' + totalForms + '-');

                // Clear all input values in the new form
                newForm.querySelectorAll('input[type="text"], input[type="number"], input[type="file"]').forEach(function(input) {
                    input.value = '';
                });

                // Remove any current file display from cloned form
                newForm.querySelectorAll('.bg-green-50').forEach(function(el) {
                    el.remove();
                });

                // Remove delete checkbox section from new forms
                const deleteSection = newForm.querySelector('.bg-red-50');
                if (deleteSection) {
                    deleteSection.remove();
                }

                // Clear any error messages
                newForm.querySelectorAll('.text-red-600').forEach(function(error) {
                    error.remove();
                });
            }

            // Update the header
            const header = newForm.querySelector('h3');
            if (header) {
                header.textContent = 'New Stem ' + (totalForms + 1);
            }

            // Add the new form to the container
            stemContainer.appendChild(newForm);

            // Increment total forms
            totalFormsInput.value = totalForms + 1;

            // Apply styling to new form
            newForm.style.backgroundColor = '#f9f9f9';
            newForm.style.borderLeft = '3px solid rgb(139, 81, 143)';

            console.log('Added new stem form. Total forms now:', totalForms + 1);
        });
    }

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
    const conversionOverlay = document.getElementById('conversion-overlay');

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
                return;
            }

            // Validate file sizes before submission
            const fileSizeErrors = validateFileSizes(form);
            if (fileSizeErrors.length > 0) {
                e.preventDefault();
                showFileSizeErrors(fileSizeErrors);
                return;
            }

            // Check if there are any AIFF files being uploaded
            const audioInputs = form.querySelectorAll('input[type="file"][name*="audio_file"]');
            let hasAiffFiles = false;
            audioInputs.forEach(input => {
                if (input.files && input.files[0]) {
                    const fileName = input.files[0].name.toLowerCase();
                    if (fileName.endsWith('.aiff') || fileName.endsWith('.aif')) {
                        hasAiffFiles = true;
                    }
                }
            });

            // Show conversion overlay if there are AIFF files or any audio files (to be safe)
            let hasAnyAudioFiles = false;
            audioInputs.forEach(input => {
                if (input.files && input.files[0]) {
                    hasAnyAudioFiles = true;
                }
            });

            if (conversionOverlay && hasAnyAudioFiles) {
                conversionOverlay.classList.remove('hidden');
                conversionOverlay.classList.add('flex');
            }
        });
    }

    // Handle dismissible message alerts
    const messageCloseButtons = document.querySelectorAll('.message-close');
    messageCloseButtons.forEach(button => {
        button.addEventListener('click', function() {
            const alert = this.closest('.message-alert');
            if (alert) {
                alert.style.transition = 'opacity 0.3s ease-out';
                alert.style.opacity = '0';
                setTimeout(() => {
                    alert.remove();
                }, 300);
            }
        });
    });

    // Real-time file size validation on file input change
    const allFileInputs = document.querySelectorAll('input[type="file"]');
    allFileInputs.forEach(input => {
        input.addEventListener('change', function() {
            // Remove any existing size warning
            const existingWarning = this.parentNode.querySelector('.file-size-warning');
            if (existingWarning) {
                existingWarning.remove();
            }

            if (this.files && this.files[0]) {
                const file = this.files[0];
                const isAudio = this.name.includes('audio_file');
                const isPdf = this.name === 'pdf_score';
                const limit = isAudio ? FILE_SIZE_LIMITS.audio :
                             isPdf ? FILE_SIZE_LIMITS.pdf : FILE_SIZE_LIMITS.image;

                if (file.size > limit) {
                    // Show warning immediately
                    const warning = document.createElement('p');
                    warning.className = 'file-size-warning mt-2 text-sm font-medium text-red-600 flex items-center gap-1';
                    warning.innerHTML = `
                        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
                        </svg>
                        File too large (${formatFileSize(file.size)}). Max: ${formatFileSize(limit)}
                    `;
                    this.parentNode.appendChild(warning);
                    this.style.borderColor = '#c0392b';
                } else {
                    this.style.borderColor = '';
                }
            }
        });
    });
});
