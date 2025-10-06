// Message handling functionality
document.addEventListener("DOMContentLoaded", function () {
  initializeMessages();
});

function initializeMessages() {
  const messageAlerts = document.querySelectorAll(".message-alert");
  console.log(messageAlerts);
  messageAlerts.forEach((alert, index) => {
    console.log(alert.dataset.autoDismiss);

    // Animate message in
    setTimeout(() => {
      alert.classList.remove("opacity-0", "translate-x-full");
      alert.classList.add("opacity-100", "translate-x-0");
    }, 100 * index);

    // Auto-dismiss if enabled
    if (alert.dataset.autoDismiss === "true") {
      setTimeout(() => {
        dismissMessageElement(alert);
      }, 4000); // 4 seconds total (2s visible + animation time)
    }
  });
}

function dismissMessage(button) {
  const alert = button.closest(".message-alert");
  dismissMessageElement(alert);
}

function dismissMessageElement(alert) {
  if (!alert) return;

  // Animate out
  alert.classList.remove("opacity-100", "translate-x-0");
  alert.classList.add("opacity-0", "translate-x-full");

  // Remove from DOM after animation
  setTimeout(() => {
    if (alert.parentNode) {
      alert.parentNode.removeChild(alert);

      // Remove container if no messages left
      const container = document.getElementById("message-container");
      if (container && container.children.length === 0) {
        container.remove();
      }
    }
  }, 300);
}

// Add manual dismiss with escape key
document.addEventListener("keydown", function (e) {
  if (e.key === "Escape") {
    const alerts = document.querySelectorAll(".message-alert");
    alerts.forEach((alert) => dismissMessageElement(alert));
  }
});

// Optional: Add swipe to dismiss on mobile
let touchStartX = 0;
document.addEventListener("touchstart", function (e) {
  if (e.target.closest(".message-alert")) {
    touchStartX = e.changedTouches[0].screenX;
  }
});

document.addEventListener("touchend", function (e) {
  if (e.target.closest(".message-alert")) {
    const touchEndX = e.changedTouches[0].screenX;
    const diff = touchEndX - touchStartX;

    if (diff > 50) {
      // Swipe right to dismiss
      dismissMessageElement(e.target.closest(".message-alert"));
    }
  }
});
