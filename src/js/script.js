// Form validation setup function
window.validation = null; // Declare and initialize globally

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

    // Mark form as JS handled so the global loader doesn't interfere
    const formEl = document.querySelector(formId);
    if (formEl) {
        formEl.setAttribute('data-js-handled', 'true');
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

    if (errorData.errors && !Array.isArray(errorData.errors)) {
      // 1. Validation Errors (Django Dict Format: { field: [messages] })
      let unmappedErrors = [];

      Object.entries(errorData.errors).forEach(([field, messages]) => {
          // Check for Formset Errors (Array of Objects)
          if (Array.isArray(messages) && messages.length > 0 && typeof messages[0] === 'object') {
              // Iterate over the formset list
              messages.forEach((formErrors, index) => {
                  // formErrors is a dict { subField: [msgs] }
                  Object.entries(formErrors).forEach(([subField, subMsgs]) => {
                       // Construct ID: id_{prefix}-{index}-{subField}
                       // Use field as prefix (e.g., bank_accounts)
                       let selector = `#id_${field}-${index}-${subField}`;
                       const msg = Array.isArray(subMsgs) ? subMsgs.join(', ') : subMsgs;

                       let el = document.querySelector(selector);
                       if (el && validation) {
                           validation.showErrors({ [selector]: msg });
                       } else if (el) {
                           // Fallback
                            let errorEl = el.parentNode.querySelector('.error-message');
                            if (!errorEl) {
                                errorEl = document.createElement('div');
                                errorEl.classList.add('text-tiny+', 'text-error', 'mt-1', 'error-message');
                                el.parentNode.appendChild(errorEl);
                            }
                            errorEl.textContent = msg;
                       } else {
                           unmappedErrors.push(`${subField}: ${msg}`);
                       }
                  });
              });
              return;
          }

          // Normal Field Errors
          const message = Array.isArray(messages) ? messages.join(', ') : messages;

          if (typeof message !== 'string') {
              unmappedErrors.push(`${field}: Invalid error format`);
              return;
          }

          // Try to match field by ID first, then Name
          let fieldSelector = `#${field}`;
          let el = document.querySelector(fieldSelector);

          // If not found by ID, try Django default ID format "id_field"
          if (!el) {
              fieldSelector = `#id_${field}`;
              el = document.querySelector(fieldSelector);
          }

          if (el && validation) {
               // Use JustValidate to show error if possible
               validation.showErrors({ [fieldSelector]: message });
          } else if (el) {
              // Fallback manual error placement
              let errorEl = el.parentNode.querySelector('.error-message');
              if (!errorEl) {
                  errorEl = document.createElement('div');
                  errorEl.classList.add('text-tiny+', 'text-error', 'mt-1', 'error-message');
                  el.parentNode.appendChild(errorEl);
              }
              errorEl.textContent = message;
          } else {
              unmappedErrors.push(message);
          }
      });

      if(window.Swal) {
          let swalText = 'Please correct the errors in the form.';
          if (unmappedErrors.length > 0) {
              swalText += '\n\n' + unmappedErrors.join('\n');
          }
          Swal.fire({
            icon: 'error',
            title: 'Validation Error',
            text: swalText,
          });
      }

    } else if (errorData?.error?.errors?.length) {
      // 2. Validation Errors (API Standard Format)
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

    // Global Loader for all form submissions
    document.addEventListener('submit', function(e) {
        const form = e.target;

        // Skip if form is handled by setupFormValidation (has data-js-handled attribute)
        if (form.hasAttribute('data-js-handled')) {
            return;
        }

        // Skip if form has explicit no-loader attribute
        if (form.hasAttribute('data-no-loader')) {
            return;
        }

        // Show Loader using SweetAlert2
        if (window.Swal) {
            Swal.fire({
                title: 'Processing...',
                text: 'Please wait while we process your request.',
                allowOutsideClick: false,
                didOpen: () => {
                    Swal.showLoading();
                }
            });
        }
    });
});

// Use a more robust initialization for Header Dropdowns
function initHeaderDropdowns() {
    var o = { placement: "bottom-start", modifiers: [{ name: "offset", options: { offset: [0, 4] } }] };

    // Check if Popper is available (exposed by main.js)
    if (typeof window.Popper === 'undefined') {
        // Retry after a short delay if Popper isn't ready yet
        setTimeout(initHeaderDropdowns, 50);
        return;
    }

    if(document.querySelector("#invest-menu-dropdown")) {
        new window.Popper("#invest-menu-dropdown", ".popper-ref", ".popper-root", o);
    }
    if(document.querySelector("#master-menu-dropdown")) {
        new window.Popper("#master-menu-dropdown", ".popper-ref", ".popper-root", o);
    }
    if(document.querySelector("#payouts-menu-dropdown")) {
        new window.Popper("#payouts-menu-dropdown", ".popper-ref", ".popper-root", o);
    }
    if(document.querySelector("#reports-menu-dropdown")) {
        new window.Popper("#reports-menu-dropdown", ".popper-ref", ".popper-root", o);
    }
    if(document.querySelector("#import-menu-dropdown")) {
        new window.Popper("#import-menu-dropdown", ".popper-ref", ".popper-root", o);
    }
    if(document.querySelector("#admin-menu-dropdown")) {
        new window.Popper("#admin-menu-dropdown", ".popper-ref", ".popper-root", o);
    }
    if(document.querySelector("#kyc-menu-dropdown")) {
        new window.Popper("#kyc-menu-dropdown", ".popper-ref", ".popper-root", o);
    }
    if(document.querySelector("#user-menu-wrapper")) {
        new window.Popper("#user-menu-wrapper", ".popper-ref", ".popper-root", o);
    }
}

// Try initializing when DOM is ready, or wait for app:mounted
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initHeaderDropdowns);
} else {
    initHeaderDropdowns();
}

window.addEventListener("app:mounted", initHeaderDropdowns);


// --- Exposed Helpers ---

/**
 * Expose setupFormValidation to window
 */
window.setupFormValidation = setupFormValidation;


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
