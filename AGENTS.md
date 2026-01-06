# Development Instructions

## UI Development
*   **Theme Folder**: Always refer to the `theme/` folder for UI components and HTML structure. This folder contains the reference templates for the LimeOne theme.
*   **Components**: When building new pages, use the components found in the `theme/` folder to ensure consistency with the design system.

## Form Validation
*   **JustValidate**: Use the `JustValidate` library for form validation.
*   **SetupFormValidation**: Implement form submission using a `SetupFormValidation` function or pattern to handle validation logic consistently across the application.

## Tables
*   **Grid.js**: Use `Grid.js` for all table implementations. Refer to `theme/components-table-gridjs.html` (if available) or the Grid.js documentation for implementation details.

## Asset Management
*   **JavaScript Pages**: Place page-specific JavaScript files in `src/js/pages/`. The build process (configured in `webpack.mix.js`) automatically detects `.js` files in this directory and compiles them to `assets/js/pages/`.
*   **Building**: Run `npm run dev` for development or `npm run prod` for production builds.

## Architecture & Project Structure
*   **Documentation**: Refer to `ARCHITECTURE.md` for the detailed project specification, user roles, and module responsibilities.
*   **Apps**:
    *   `apps/users`: Authentication & Hierarchy.
    *   `apps/products`: MF Schemes.
    *   `apps/investments`: Orders & Portfolios.
    *   `apps/payouts`: Brokerage & Commissions.
    *   `apps/integration`: BSE & RTA Interfaces.
    *   `apps/analytics`: Reports & Dashboards.
