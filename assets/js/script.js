/******/ (() => { // webpackBootstrap
/*!**************************!*\
  !*** ./src/js/script.js ***!
  \**************************/
function _typeof(o) { "@babel/helpers - typeof"; return _typeof = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function (o) { return typeof o; } : function (o) { return o && "function" == typeof Symbol && o.constructor === Symbol && o !== Symbol.prototype ? "symbol" : typeof o; }, _typeof(o); }
function _regenerator() { /*! regenerator-runtime -- Copyright (c) 2014-present, Facebook, Inc. -- license (MIT): https://github.com/babel/babel/blob/main/packages/babel-helpers/LICENSE */ var e, t, r = "function" == typeof Symbol ? Symbol : {}, n = r.iterator || "@@iterator", o = r.toStringTag || "@@toStringTag"; function i(r, n, o, i) { var c = n && n.prototype instanceof Generator ? n : Generator, u = Object.create(c.prototype); return _regeneratorDefine2(u, "_invoke", function (r, n, o) { var i, c, u, f = 0, p = o || [], y = !1, G = { p: 0, n: 0, v: e, a: d, f: d.bind(e, 4), d: function d(t, r) { return i = t, c = 0, u = e, G.n = r, a; } }; function d(r, n) { for (c = r, u = n, t = 0; !y && f && !o && t < p.length; t++) { var o, i = p[t], d = G.p, l = i[2]; r > 3 ? (o = l === n) && (u = i[(c = i[4]) ? 5 : (c = 3, 3)], i[4] = i[5] = e) : i[0] <= d && ((o = r < 2 && d < i[1]) ? (c = 0, G.v = n, G.n = i[1]) : d < l && (o = r < 3 || i[0] > n || n > l) && (i[4] = r, i[5] = n, G.n = l, c = 0)); } if (o || r > 1) return a; throw y = !0, n; } return function (o, p, l) { if (f > 1) throw TypeError("Generator is already running"); for (y && 1 === p && d(p, l), c = p, u = l; (t = c < 2 ? e : u) || !y;) { i || (c ? c < 3 ? (c > 1 && (G.n = -1), d(c, u)) : G.n = u : G.v = u); try { if (f = 2, i) { if (c || (o = "next"), t = i[o]) { if (!(t = t.call(i, u))) throw TypeError("iterator result is not an object"); if (!t.done) return t; u = t.value, c < 2 && (c = 0); } else 1 === c && (t = i["return"]) && t.call(i), c < 2 && (u = TypeError("The iterator does not provide a '" + o + "' method"), c = 1); i = e; } else if ((t = (y = G.n < 0) ? u : r.call(n, G)) !== a) break; } catch (t) { i = e, c = 1, u = t; } finally { f = 1; } } return { value: t, done: y }; }; }(r, o, i), !0), u; } var a = {}; function Generator() {} function GeneratorFunction() {} function GeneratorFunctionPrototype() {} t = Object.getPrototypeOf; var c = [][n] ? t(t([][n]())) : (_regeneratorDefine2(t = {}, n, function () { return this; }), t), u = GeneratorFunctionPrototype.prototype = Generator.prototype = Object.create(c); function f(e) { return Object.setPrototypeOf ? Object.setPrototypeOf(e, GeneratorFunctionPrototype) : (e.__proto__ = GeneratorFunctionPrototype, _regeneratorDefine2(e, o, "GeneratorFunction")), e.prototype = Object.create(u), e; } return GeneratorFunction.prototype = GeneratorFunctionPrototype, _regeneratorDefine2(u, "constructor", GeneratorFunctionPrototype), _regeneratorDefine2(GeneratorFunctionPrototype, "constructor", GeneratorFunction), GeneratorFunction.displayName = "GeneratorFunction", _regeneratorDefine2(GeneratorFunctionPrototype, o, "GeneratorFunction"), _regeneratorDefine2(u), _regeneratorDefine2(u, o, "Generator"), _regeneratorDefine2(u, n, function () { return this; }), _regeneratorDefine2(u, "toString", function () { return "[object Generator]"; }), (_regenerator = function _regenerator() { return { w: i, m: f }; })(); }
function _regeneratorDefine2(e, r, n, t) { var i = Object.defineProperty; try { i({}, "", {}); } catch (e) { i = 0; } _regeneratorDefine2 = function _regeneratorDefine(e, r, n, t) { function o(r, n) { _regeneratorDefine2(e, r, function (e) { return this._invoke(r, n, e); }); } r ? i ? i(e, r, { value: n, enumerable: !t, configurable: !t, writable: !t }) : e[r] = n : (o("next", 0), o("throw", 1), o("return", 2)); }, _regeneratorDefine2(e, r, n, t); }
function asyncGeneratorStep(n, t, e, r, o, a, c) { try { var i = n[a](c), u = i.value; } catch (n) { return void e(n); } i.done ? t(u) : Promise.resolve(u).then(r, o); }
function _asyncToGenerator(n) { return function () { var t = this, e = arguments; return new Promise(function (r, o) { var a = n.apply(t, e); function _next(n) { asyncGeneratorStep(a, r, o, _next, _throw, "next", n); } function _throw(n) { asyncGeneratorStep(a, r, o, _next, _throw, "throw", n); } _next(void 0); }); }; }
function _slicedToArray(r, e) { return _arrayWithHoles(r) || _iterableToArrayLimit(r, e) || _unsupportedIterableToArray(r, e) || _nonIterableRest(); }
function _nonIterableRest() { throw new TypeError("Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method."); }
function _unsupportedIterableToArray(r, a) { if (r) { if ("string" == typeof r) return _arrayLikeToArray(r, a); var t = {}.toString.call(r).slice(8, -1); return "Object" === t && r.constructor && (t = r.constructor.name), "Map" === t || "Set" === t ? Array.from(r) : "Arguments" === t || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(t) ? _arrayLikeToArray(r, a) : void 0; } }
function _arrayLikeToArray(r, a) { (null == a || a > r.length) && (a = r.length); for (var e = 0, n = Array(a); e < a; e++) n[e] = r[e]; return n; }
function _iterableToArrayLimit(r, l) { var t = null == r ? null : "undefined" != typeof Symbol && r[Symbol.iterator] || r["@@iterator"]; if (null != t) { var e, n, i, u, a = [], f = !0, o = !1; try { if (i = (t = t.call(r)).next, 0 === l) { if (Object(t) !== t) return; f = !1; } else for (; !(f = (e = i.call(t)).done) && (a.push(e.value), a.length !== l); f = !0); } catch (r) { o = !0, n = r; } finally { try { if (!f && null != t["return"] && (u = t["return"](), Object(u) !== u)) return; } finally { if (o) throw n; } } return a; } }
function _arrayWithHoles(r) { if (Array.isArray(r)) return r; }
function ownKeys(e, r) { var t = Object.keys(e); if (Object.getOwnPropertySymbols) { var o = Object.getOwnPropertySymbols(e); r && (o = o.filter(function (r) { return Object.getOwnPropertyDescriptor(e, r).enumerable; })), t.push.apply(t, o); } return t; }
function _objectSpread(e) { for (var r = 1; r < arguments.length; r++) { var t = null != arguments[r] ? arguments[r] : {}; r % 2 ? ownKeys(Object(t), !0).forEach(function (r) { _defineProperty(e, r, t[r]); }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(t)) : ownKeys(Object(t)).forEach(function (r) { Object.defineProperty(e, r, Object.getOwnPropertyDescriptor(t, r)); }); } return e; }
function _defineProperty(e, r, t) { return (r = _toPropertyKey(r)) in e ? Object.defineProperty(e, r, { value: t, enumerable: !0, configurable: !0, writable: !0 }) : e[r] = t, e; }
function _toPropertyKey(t) { var i = _toPrimitive(t, "string"); return "symbol" == _typeof(i) ? i : i + ""; }
function _toPrimitive(t, r) { if ("object" != _typeof(t) || !t) return t; var e = t[Symbol.toPrimitive]; if (void 0 !== e) { var i = e.call(t, r || "default"); if ("object" != _typeof(i)) return i; throw new TypeError("@@toPrimitive must return a primitive value."); } return ("string" === r ? String : Number)(t); }
// Form validation setup function
window.validation = null; // Declare and initialize globally

function setupFormValidation(_ref) {
  var formId = _ref.formId,
    fields = _ref.fields,
    submitUrl = _ref.submitUrl,
    successCallback = _ref.successCallback,
    errorCallback = _ref.errorCallback,
    _ref$method = _ref.method,
    method = _ref$method === void 0 ? 'POST' : _ref$method,
    _ref$customConfig = _ref.customConfig,
    customConfig = _ref$customConfig === void 0 ? {} : _ref$customConfig,
    _ref$beforeSubmitCall = _ref.beforeSubmitCallback,
    beforeSubmitCallback = _ref$beforeSubmitCall === void 0 ? null : _ref$beforeSubmitCall;
  // Ensure JustValidate is available
  if (typeof JustValidate === 'undefined') {
    console.error('JustValidate is not loaded. Please include it before using setupFormValidation.');
    return;
  }
  validation = new JustValidate(formId, _objectSpread({
    errorFieldCssClass: 'is-invalid',
    errorLabelCssClass: 'just-validate-error-label'
  }, customConfig));

  // Add validation rules dynamically
  Object.entries(fields).forEach(function (_ref2) {
    var _ref3 = _slicedToArray(_ref2, 2),
      fieldId = _ref3[0],
      rules = _ref3[1];
    // Check if element exists to avoid errors
    if (document.querySelector(fieldId)) {
      validation.addField(fieldId, rules);
    }
  });

  // Submission handler
  validation.onSuccess(/*#__PURE__*/function () {
    var _ref4 = _asyncToGenerator(/*#__PURE__*/_regenerator().m(function _callee(event) {
      var form, formData, csrfTokenInput, csrfToken, response, data, errorData, _t;
      return _regenerator().w(function (_context) {
        while (1) switch (_context.p = _context.n) {
          case 0:
            // Prevent default submission if it's an event
            if (event && event.preventDefault) {
              event.preventDefault();
            }
            form = document.querySelector(formId);
            formData = new FormData(form);
            csrfTokenInput = document.querySelector('[name=csrfmiddlewaretoken]');
            csrfToken = csrfTokenInput ? csrfTokenInput.value : ''; // Hook for modifying formData before submit
            if (beforeSubmitCallback && typeof beforeSubmitCallback === 'function') {
              beforeSubmitCallback(formData);
            }

            // Show loading state
            if (window.Swal) {
              Swal.fire({
                title: 'Processing...',
                text: 'Submitting form, please wait...',
                allowOutsideClick: false,
                didOpen: function didOpen() {
                  Swal.showLoading();
                }
              });
            }
            _context.p = 1;
            _context.n = 2;
            return fetch(submitUrl, {
              method: method.toUpperCase(),
              headers: {
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest' // Standard for Django AJAX
              },
              body: formData
            });
          case 2:
            response = _context.v;
            if (!response.ok) {
              _context.n = 4;
              break;
            }
            _context.n = 3;
            return response.json();
          case 3:
            data = _context.v;
            if (typeof successCallback === 'function') {
              successCallback(data); // Call custom success handler
            } else {
              if (window.Swal) {
                Swal.fire({
                  icon: 'success',
                  title: 'Success!',
                  text: 'Form submitted successfully!'
                }).then(function () {
                  window.location.reload();
                });
              } else {
                alert('Form submitted successfully!');
                window.location.reload();
              }
            }
            _context.n = 6;
            break;
          case 4:
            _context.n = 5;
            return response.json();
          case 5:
            errorData = _context.v;
            if (typeof errorCallback === 'function') {
              errorCallback(errorData, validation); // Call custom error handler
            } else {
              // Default error handling if no callback provided
              handleErrorResponse(errorData);
            }
          case 6:
            _context.n = 8;
            break;
          case 7:
            _context.p = 7;
            _t = _context.v;
            console.error('Network Error:', _t);
            if (window.Swal) {
              Swal.fire({
                icon: 'error',
                title: 'Network Error',
                text: 'Failed to submit form due to a network issue.'
              });
            } else {
              alert('Failed to submit form due to a network issue.');
            }
          case 8:
            return _context.a(2);
        }
      }, _callee, null, [[1, 7]]);
    }));
    return function (_x) {
      return _ref4.apply(this, arguments);
    };
  }());
}

// === Error Handler ===
function handleErrorResponse(errorData) {
  var _errorData$error;
  if (window.Swal) {
    Swal.close(); // Close loading spinner
  }

  // Clear existing custom error messages if any (JustValidate handles its own, but this is for extra ones)
  document.querySelectorAll('.error-message').forEach(function (el) {
    return el.textContent = '';
  });
  if (errorData !== null && errorData !== void 0 && (_errorData$error = errorData.error) !== null && _errorData$error !== void 0 && (_errorData$error = _errorData$error.errors) !== null && _errorData$error !== void 0 && _errorData$error.length) {
    // 1. Validation Errors (Field specific)
    // Expected format: { error: { errors: [ { field: 'email', message: '...' } ] } }
    errorData.error.errors.forEach(function (err) {
      // Try to match field by ID first, then Name
      var fieldSelector = "#".concat(err.field);
      var el = document.querySelector(fieldSelector);

      // If not found by ID, try Django default ID format "id_field"
      if (!el) {
        fieldSelector = "#id_".concat(err.field);
        el = document.querySelector(fieldSelector);
      }
      if (el && validation) {
        // Use JustValidate to show error if possible
        validation.showErrors(_defineProperty({}, fieldSelector, err.message));
      } else if (el) {
        // Fallback manual error placement
        var errorEl = el.parentNode.querySelector('.error-message');
        if (!errorEl) {
          errorEl = document.createElement('div');
          errorEl.classList.add('text-tiny+', 'text-error', 'mt-1', 'error-message');
          el.parentNode.appendChild(errorEl);
        }
        errorEl.textContent = err.message;
      }
    });
    if (window.Swal) {
      Swal.fire({
        icon: 'error',
        title: 'Validation Error',
        text: 'Please correct the errors in the form.'
      });
    }
  } else if (errorData.message) {
    // 2. General Error Message
    if (window.Swal) {
      Swal.fire({
        icon: 'error',
        title: 'Error',
        text: errorData.message
      });
    } else {
      alert(errorData.message);
    }
  } else {
    if (window.Swal) {
      Swal.fire({
        icon: 'error',
        title: 'Error',
        text: 'Failed to submit form. Check for errors.'
      });
    } else {
      alert('Failed to submit form. Check for errors.');
    }
  }
}
document.addEventListener("DOMContentLoaded", function () {
  var whatsappBtn = document.getElementById("whatsappBtn");
  if (whatsappBtn) {
    // 🔹 Your WhatsApp details
    var phoneNumber = "917265098822"; // Include country code without +
    var message = "Hello, I would like to know more about your services.";
    whatsappBtn.addEventListener("click", function (e) {
      e.preventDefault();
      var encodedMessage = encodeURIComponent(message);
      var whatsappURL = "https://wa.me/".concat(phoneNumber, "?text=").concat(encodedMessage);

      // Open in new tab
      window.open(whatsappURL, "_blank");
    });
  }
});

// Use a more robust initialization for Header Dropdowns
function initHeaderDropdowns() {
  var o = {
    placement: "bottom-start",
    modifiers: [{
      name: "offset",
      options: {
        offset: [0, 4]
      }
    }]
  };

  // Check if Popper is available (exposed by main.js)
  if (typeof window.Popper === 'undefined') {
    // Retry after a short delay if Popper isn't ready yet
    setTimeout(initHeaderDropdowns, 50);
    return;
  }
  if (document.querySelector("#invest-menu-dropdown")) {
    new window.Popper("#invest-menu-dropdown", ".popper-ref", ".popper-root", o);
  }
  if (document.querySelector("#master-menu-dropdown")) {
    new window.Popper("#master-menu-dropdown", ".popper-ref", ".popper-root", o);
  }
  if (document.querySelector("#user-menu-wrapper")) {
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
window.qsa = function (selector) {
  return document.querySelectorAll(selector);
};

/**
 * Helper to initialize Flatpickr safely
 * @param {string|Element} selector - CSS selector or DOM element
 * @param {object} options - Flatpickr options
 */
window.initFlatpickr = function (selector) {
  var options = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : {};
  // Ensure flatpickr is loaded
  if (typeof flatpickr === 'undefined') {
    console.warn('Flatpickr is not loaded.');
    return;
  }
  var el = typeof selector === 'string' ? document.querySelector(selector) : selector;
  if (el) {
    flatpickr(el, options);
  }
};

/**
 * Initialize all standard date fields
 */
window.initAllFlatpickrs = function () {
  // Specific fields requested
  window.initFlatpickr('#dob', {
    maxDate: 'today'
  }); // mapped from #dateofbirth for Investor Onboarding
  window.initFlatpickr('#dateofbirth', {
    maxDate: 'today'
  }); // User provided ID
  window.initFlatpickr('#dateofjoin', {
    maxDate: null
  });
  window.initFlatpickr('#pf_joining_date', {
    maxDate: null
  });
  window.initFlatpickr('#esic_joining_date', {
    maxDate: null
  });

  // Generic data attribute initialization
  window.qsa('[data-flatpickr]').forEach(function (el) {
    return window.initFlatpickr(el, {});
  });
};
/******/ })()
;