// Form validation setup function
let validation = null; // Declare and initialize globally

function setupFormValidation({
    formId,
    fields,
    submitUrl,
    successCallback,
    errorCallback,
    method = 'POST',
    customConfig = {},
    beforeSubmitCallback = null,
}) {
    // Ensure JustValidate is available
    if (typeof JustValidate === 'undefined') {
        console.error('JustValidate is not loaded. Please include it before using setupFormValidation.');
        return;
    }

    validation = new JustValidate(formId, {
        errorFieldCssClass: 'is-invalid',
        errorLabelCssClass: 'just-validate-error-label',
        ...customConfig, // Allows custom configurations to override defaults
    });

    // Add validation rules dynamically
    Object.entries(fields).forEach(([fieldId, rules]) => {
        // Check if element exists to avoid errors
        if(document.querySelector(fieldId)) {
            validation.addField(fieldId, rules);
        }
    });

    // Submission handler
    validation.onSuccess(async (event) => {
        // Prevent default submission if it's an event
        if (event && event.preventDefault) {
            event.preventDefault();
        }

        const form = document.querySelector(formId);
        const formData = new FormData(form);
        const csrfTokenInput = document.querySelector('[name=csrfmiddlewaretoken]');
        const csrfToken = csrfTokenInput ? csrfTokenInput.value : '';

        // Hook for modifying formData before submit
        if (beforeSubmitCallback && typeof beforeSubmitCallback === 'function') {
            beforeSubmitCallback(formData);
        }

        // Show loading state
        if (window.Swal) {
            Swal.fire({
                title: 'Processing...',
                text: 'Submitting form, please wait...',
                allowOutsideClick: false,
                didOpen: () => {
                    Swal.showLoading();
                }
            });
        }

        try {
            const response = await fetch(submitUrl, {
                method: method.toUpperCase(),
                headers: {
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest' // Standard for Django AJAX
                },
                body: formData,
            });

            if (response.ok) {
                const data = await response.json();
                if (typeof successCallback === 'function') {
                    successCallback(data); // Call custom success handler
                } else {
                    if(window.Swal) {
                        Swal.fire({
                            icon: 'success',
                            title: 'Success!',
                            text: 'Form submitted successfully!',
                        }).then(() => {
                           window.location.reload();
                        });
                    } else {
                         alert('Form submitted successfully!');
                         window.location.reload();
                    }
                }
            } else {
                const errorData = await response.json();
                if (typeof errorCallback === 'function') {
                    errorCallback(errorData, validation); // Call custom error handler
                } else {
                    // Default error handling if no callback provided
                    handleErrorResponse(errorData);
                }
            }
        } catch (error) {
            console.error('Network Error:', error);
            if(window.Swal) {
                 Swal.fire({
                    icon: 'error',
                    title: 'Network Error',
                    text: 'Failed to submit form due to a network issue.',
                });
            } else {
                alert('Failed to submit form due to a network issue.');
            }
        }
    });
}

// === Error Handler ===
function handleErrorResponse(errorData) {
    if (window.Swal) {
        Swal.close(); // Close loading spinner
    }

    // Clear existing custom error messages if any (JustValidate handles its own, but this is for extra ones)
    document.querySelectorAll('.error-message').forEach((el) => el.textContent = '');

    if (errorData?.error?.errors?.length) {
      // 1. Validation Errors (Field specific)
      // Expected format: { error: { errors: [ { field: 'email', message: '...' } ] } }
      errorData.error.errors.forEach((err) => {
        // Try to match field by ID first, then Name
        let fieldSelector = `#${err.field}`;
        let el = document.querySelector(fieldSelector);

        // If not found by ID, try Django default ID format "id_field"
        if (!el) {
            fieldSelector = `#id_${err.field}`;
            el = document.querySelector(fieldSelector);
        }

        if (el && validation) {
             // Use JustValidate to show error if possible
             validation.showErrors({ [fieldSelector]: err.message });
        } else if (el) {
            // Fallback manual error placement
            let errorEl = el.parentNode.querySelector('.error-message');
            if (!errorEl) {
                errorEl = document.createElement('div');
                errorEl.classList.add('text-tiny+', 'text-error', 'mt-1', 'error-message');
                el.parentNode.appendChild(errorEl);
            }
            errorEl.textContent = err.message;
        }
      });

      if(window.Swal) {
          Swal.fire({
            icon: 'error',
            title: 'Validation Error',
            text: 'Please correct the errors in the form.',
          });
      }

    } else if (errorData.message) {
      // 2. General Error Message
      if (window.Swal) {
        Swal.fire({
          icon: 'error',
          title: 'Error',
          text: errorData.message,
        });
      } else {
        alert(errorData.message);
      }
    } else {
      if (window.Swal) {
          Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to submit form. Check for errors.',
          });
      } else {
          alert('Failed to submit form. Check for errors.');
      }
    }
}

document.addEventListener("DOMContentLoaded", function () {
    const whatsappBtn = document.getElementById("whatsappBtn");

    if (whatsappBtn) {
        // 🔹 Your WhatsApp details
        const phoneNumber = "917265098822"; // Include country code without +
        const message = "Hello, I would like to know more about your services.";

        whatsappBtn.addEventListener("click", function (e) {
        e.preventDefault();

        const encodedMessage = encodeURIComponent(message);
        const whatsappURL = `https://wa.me/${phoneNumber}?text=${encodedMessage}`;

        // Open in new tab
        window.open(whatsappURL, "_blank");
        });
    }
});

window.addEventListener("app:mounted", function () {
    var o = { placement: "bottom-start", modifiers: [{ name: "offset", options: { offset: [0, 4] } }] };
    // Only init if elements exist
    if(document.querySelector("#master-menu-dropdown")) {
        new Popper("#master-menu-dropdown", ".popper-ref", ".popper-root", o);
    }
});

// --- Exposed Helpers ---

/**
 * Expose setupFormValidation to window
 */
window.setupFormValidation = setupFormValidation;
window.validation = validation;

/**
 * Helper to query selector all
 */
window.qsa = (selector) => document.querySelectorAll(selector);

/**
 * Helper to initialize Flatpickr safely
 * @param {string|Element} selector - CSS selector or DOM element
 * @param {object} options - Flatpickr options
 */
window.initFlatpickr = (selector, options = {}) => {
    // Ensure flatpickr is loaded
    if (typeof flatpickr === 'undefined') {
        console.warn('Flatpickr is not loaded.');
        return;
    }

    const el = typeof selector === 'string' ? document.querySelector(selector) : selector;
    if (el) {
        flatpickr(el, options);
    }
};

/**
 * Initialize all standard date fields
 */
window.initAllFlatpickrs = () => {
    // Specific fields requested
    window.initFlatpickr('#dob', { maxDate: 'today' }); // mapped from #dateofbirth for Investor Onboarding
    window.initFlatpickr('#dateofbirth', { maxDate: 'today' }); // User provided ID
    window.initFlatpickr('#dateofjoin', { maxDate: null });
    window.initFlatpickr('#pf_joining_date', { maxDate: null });
    window.initFlatpickr('#esic_joining_date', { maxDate: null });

    // Generic data attribute initialization
    window.qsa('[data-flatpickr]').forEach(el => window.initFlatpickr(el, {}));
};
