const settingsChatLog = document.getElementById("settings-chat-log");
const settingsInput = document.getElementById("settings-input");
const settingsSendBtn = document.getElementById("settings-send-btn");

settingsSendBtn.addEventListener("click", sendSettingsMessage);
settingsInput.addEventListener("keyup", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    sendSettingsMessage();
  }
});

function appendSettingsMessage(content, className) {
  const messageDiv = document.createElement("div");
  messageDiv.classList.add("message", className);
  messageDiv.textContent = content;
  settingsChatLog.appendChild(messageDiv);
  settingsChatLog.scrollTop = settingsChatLog.scrollHeight;
}

async function sendSettingsMessage() {
  const text = settingsInput.value.trim();
  if (!text) return;

  appendSettingsMessage(text, "user-message");
  settingsInput.value = "";

  try {
    const response = await fetch("/ask_settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    const data = await response.json();
    if (data.error) {
      appendSettingsMessage("Error: " + data.error, "assistant-message");
      return;
    }
    appendSettingsMessage(data.reply, "assistant-message");

    // After GPT might have updated user_settings, fetch them & update UI
    fetchSettingsAndUpdateUI();
  } catch (err) {
    console.error(err);
    appendSettingsMessage("Something went wrong. Please try again.", "assistant-message");
  }
}

// Fetch user_settings from server & update the displayed info
async function fetchSettingsAndUpdateUI() {
  try {
    const resp = await fetch("/get_user_settings");
    const data = await resp.json();
    document.getElementById("setting-name").textContent = data.name || "N/A";
    document.getElementById("setting-age").textContent = data.age || "N/A";
    document.getElementById("setting-email").textContent = data.email || "N/A";
    document.getElementById("setting-height").textContent = data.height || "N/A";
    document.getElementById("setting-weight").textContent = data.weight || "N/A";
    document.getElementById("setting-theme").textContent =
      data.theme.charAt(0).toUpperCase() + data.theme.slice(1) || "Light";
    document.getElementById("setting-font").textContent =
      data.fontSize.charAt(0).toUpperCase() + data.fontSize.slice(1) || "Medium";

    // Apply theme changes to page
    applyThemeAndFont(data.theme, data.fontSize);
  } catch (err) {
    console.error("Failed to fetch settings", err);
  }
}

// Example function to apply user settings to the page appearance
function applyThemeAndFont(theme, fontSize) {
  if (theme === "dark") {
    document.body.classList.add("dark-mode");
  } else {
    document.body.classList.remove("dark-mode");
  }
  document.body.classList.remove("font-small", "font-medium", "font-large");
  if (fontSize === "small") {
    document.body.classList.add("font-small");
  } else if (fontSize === "large") {
    document.body.classList.add("font-large");
  } else {
    document.body.classList.add("font-medium");
  }
}

// On page load, fetch current settings & show them
document.addEventListener("DOMContentLoaded", fetchSettingsAndUpdateUI);
