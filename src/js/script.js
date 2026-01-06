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
    validation = new JustValidate(formId, {
        errorFieldCssClass: 'is-invalid',
        errorLabelCssClass: 'just-validate-error-label',
        ...customConfig, // Allows custom configurations to override defaults
    });

    // Add validation rules dynamically
    Object.entries(fields).forEach(([fieldId, rules]) => {
        validation.addField(fieldId, rules);
    });

    // Submission handler
    validation.onSuccess(async (event) => {
        event.preventDefault();

        const form = document.querySelector(formId);
        const formData = new FormData(form);
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

        const loader = document.getElementById('loader');

        // if (loader) loader.classList.add('active'); // Activate the loader
        Swal.fire({
            title: 'Processing...',
            text: 'Submitting form, please wait...',
            allowOutsideClick: false,
            didOpen: () => {
                Swal.showLoading();
            }
        });
        if (beforeSubmitCallback && typeof beforeSubmitCallback === 'function') {
            beforeSubmitCallback(formData);
        }

        try {
            const response = await fetch(submitUrl, {
                method: method.toUpperCase(),
                headers: {
                    'X-CSRFToken': csrfToken,
                },
                body: formData,
            });

            if (response.ok) {
                const data = await response.json();
                if (typeof successCallback === 'function') {
                    successCallback(data); // Call custom success handler
                } else {
                    alert('Form submitted successfully!');
                }
            } else {
                const errorData = await response.json();
                if (typeof errorCallback === 'function') {
                    errorCallback(errorData, validation); // Call custom error handler
                } else {
                    alert('Error submitting form. Check for any backend issues.');
                }
            }
        } catch (error) {
            console.error('Network Error:', error);
            alert('Failed to submit form due to a network issue.');
        } finally {
            // if (loader) loader.classList.remove('active'); // Deactivate the loader
        }
    });
}

  document.addEventListener("DOMContentLoaded", function () {
    const whatsappBtn = document.getElementById("whatsappBtn");

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
  });