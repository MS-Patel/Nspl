// gridjs-export-utils.js
// Utility for exporting Grid.js table data with customizable export options
// Requires SheetJS (https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js)
// Requires jsPDF (https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js)

const GridJSExportUtils = (() => {
  // Default export options
  const defaultOptions = {
    filename: 'report',
    title: 'Report',
    sheetName: 'Sheet1',
  };

  // Convert array of objects to 2D array for export, including header row
  function convertDataToRows(data, columns) {
    // columns: [{id, name}, ...]
    const headers = columns.map(col => col.name);
    const rows = data.map(row =>
      columns.map(col => (row[col.id] !== undefined ? row[col.id] : ''))
    );
    return [headers, ...rows];
  }

  // CSV export
  function exportCsv(data, columns, options = {}) {
    const opts = {...defaultOptions, ...options};
    const rows = convertDataToRows(data, columns);

    const processRow = (row) =>
      row.map(String)
         .map(v => v.replace(/"/g, '""'))
         .map(v => `"${v}"`)
         .join(',');

    const csvContent = rows.map(processRow).join('\r\n');

    const blob = new Blob([csvContent], {type: 'text/csv;charset=utf-8;'});
    triggerDownload(blob, `${opts.filename}.csv`);
  }

  // Excel export (requires SheetJS)
  function exportExcel(data, columns, options = {}) {
    const opts = {...defaultOptions, ...options};
    if (typeof XLSX === 'undefined') {
      alert('SheetJS (XLSX) library not loaded');
      return;
    }
    const rows = convertDataToRows(data, columns);

    const ws = XLSX.utils.aoa_to_sheet(rows);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, opts.sheetName);

    XLSX.writeFile(wb, `${opts.filename}.xlsx`);
  }

  // PDF export (requires jsPDF)
  async function exportPdf(data, columns, options = {}) {
    const opts = {...defaultOptions, ...options};
    if (typeof jspdf === 'undefined' && typeof window.jspdf === 'undefined') {
      alert('jsPDF library not loaded');
      return;
    }

    // Get jspdf namespace (umd)
    const jsPDF = (typeof jspdf !== 'undefined') ? jspdf.jsPDF : window.jspdf.jsPDF;
    const doc = new jsPDF();

    // Add title
    doc.setFontSize(16);
    doc.text(opts.title, 14, 20);

    // Prepare table data for jsPDF autotable
    const headers = columns.map(col => col.name);
    const body = data.map(row => columns.map(col => row[col.id] || ''));

    // Load autotable plugin if available
    if (doc.autoTable) {
      doc.autoTable({
        startY: 30,
        head: [headers],
        body: body
      });
      doc.save(`${opts.filename}.pdf`);
    } else {
      alert('jsPDF autotable plugin not found. Please include jspdf-autotable.');
    }
  }

  // Copy table data to clipboard as tab-separated text
  function copyToClipboard(data, columns) {
    const rows = convertDataToRows(data, columns);
    const tsv = rows.map(row => row.join('\t')).join('\n');
    navigator.clipboard.writeText(tsv).then(() => {
      alert('Table data copied to clipboard');
    }).catch(() => {
      alert('Failed to copy to clipboard');
    });
  }

  // Helper to trigger download of blob as file
  function triggerDownload(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    URL.revokeObjectURL(url);
    a.remove();
  }

  // Public API
  return {
    exportCsv,
    exportExcel,
    exportPdf,
    copyToClipboard,
  };
})();
