/* ClaudeTTS – User Profile Page Interactions */

(function () {
  'use strict';

  const form          = document.getElementById('profileForm');
  const cancelBtn     = document.getElementById('cancelBtn');
  const toast         = document.getElementById('toast');
  const deleteBtn     = document.getElementById('deleteAccountBtn');

  /** Module-level timer reference for the toast */
  var toastTimer = null;

  /** Snapshot of original values so Cancel can restore them */
  const originalValues = {};

  /** RFC 5322–compatible email regex (pragmatic subset) */
  const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  function snapshotForm() {
    form.querySelectorAll('input, select').forEach(function (el) {
      originalValues[el.id] = el.value;
    });
  }

  /** Show a temporary toast notification */
  function showToast(message) {
    toast.textContent = message;
    toast.classList.remove('hidden');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      toast.classList.add('hidden');
    }, 3000);
  }

  /** Handle form submission */
  form.addEventListener('submit', function (event) {
    event.preventDefault();

    const firstName = document.getElementById('firstName').value.trim();
    const lastName  = document.getElementById('lastName').value.trim();
    const email     = document.getElementById('email').value.trim();

    if (!firstName || !lastName) {
      showToast('⚠️ First and last name are required.');
      return;
    }

    if (!EMAIL_RE.test(email)) {
      showToast('⚠️ Please enter a valid email address.');
      return;
    }

    // Update displayed profile name and email
    document.querySelector('.profile-name').textContent = firstName + ' ' + lastName;
    document.querySelector('.profile-email').textContent = email;

    // Refresh snapshot after save
    snapshotForm();

    showToast('✅ Profile updated successfully!');
  });

  /** Cancel restores original values */
  cancelBtn.addEventListener('click', function () {
    Object.keys(originalValues).forEach(function (id) {
      const el = document.getElementById(id);
      if (el) el.value = originalValues[id];
    });
    showToast('↩️ Changes discarded.');
  });

  /** Warn before deleting account */
  deleteBtn.addEventListener('click', function () {
    const confirmed = window.confirm(
      'Are you sure you want to permanently delete your account? This action cannot be undone.'
    );
    if (confirmed) {
      showToast('🗑️ Account deletion requested. You will receive a confirmation email.');
    }
  });

  // Take snapshot on page load
  snapshotForm();
}());
