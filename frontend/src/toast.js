// Standalone toast utility — separated from App.jsx so Vite Fast Refresh works correctly.
// React components and non-component exports must not live in the same module.

let _addToast = null;

export function registerToastHandler(handler) {
  _addToast = handler;
}

export function showToast(message, type = 'info') {
  if (_addToast) _addToast(message, type);
}
