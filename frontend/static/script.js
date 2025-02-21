const chatLog = document.getElementById("chat-log");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");

sendBtn.addEventListener("click", sendMessage);
userInput.addEventListener("keyup", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    sendMessage();
  }
});

function appendMessage(content, className) {
  const messageDiv = document.createElement("div");
  messageDiv.classList.add("message", className);
  messageDiv.innerHTML = content;
  chatLog.appendChild(messageDiv);
  chatLog.scrollTop = chatLog.scrollHeight;
}

async function sendMessage() {
  const text = userInput.value.trim();
  if (!text) return;
  appendMessage(text, "user-message");
  userInput.value = "";
  try {
    const response = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    const data = await response.json();
    if (data.error) {
      appendMessage("Error: " + data.error, "assistant-message");
      return;
    }
    appendMessage(data.reply, "assistant-message");
  } catch (err) {
    console.error(err);
    appendMessage("Something went wrong. Please try again.", "assistant-message");
  }
}
