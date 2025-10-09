// static/js/chat.js
class ChatRoom {
  constructor() {
    this.roomId = document.getElementById("room-id").value;
    this.messagesContainer = document.getElementById("messages-container");
    this.messageForm = document.getElementById("message-form");
    this.messageInput = document.getElementById("message-input");
    this.sendButton = document.getElementById("send-button");
    this.typingIndicator = document.getElementById("typing-indicator");
    this.typingUsers = document.getElementById("typing-users");
    this.onlineDisplay = document.getElementById("online-display");
    this.membersDisplay = document.getElementById("membership-display");
    this.userinitials = document.getElementById("user_meta").dataset.initials;
    this.username = document.getElementById("user_meta").dataset.username;
    this.room_update_bt = document.getElementById("update_room");

    this.websocket = null;
    this.typingTimer = null;
    this.isTyping = false;
    this.typingUsersSet = new Set();

    this.init();
  }

  init() {
    this.connectWebSocket();
    this.setupEventListeners();
    this.scrollToBottom();
  }

  connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/chat/${this.roomId}/`;

    this.websocket = new WebSocket(wsUrl);

    this.websocket.onopen = () => {
      console.log("WebSocket connection established");
      this.showSystemMessage("Connected to chat room");
    };

    this.websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleWebSocketMessage(data);
    };

    this.websocket.onclose = () => {
      console.log("WebSocket connection closed");
      this.showSystemMessage(
        "Disconnected from chat room. Attempting to reconnect...",
      );
      // Attempt reconnect after 3 seconds
      setTimeout(() => this.connectWebSocket(), 3000);
    };

    this.websocket.onerror = (error) => {
      console.error("WebSocket error:", error);
      this.showSystemMessage("Connection error occurred", "error");
    };
  }

  handleWebSocketMessage(data) {
    switch (data.type) {
      case "chat_message":
        this.displayMessage(data);
        break;
      case "user_join":
        this.handleUserJoin(data);
        break;
      case "user_leave":
        this.handleUserLeave(data);
        break;
      case "typing":
        this.handleTypingIndicator(data);
        break;
      case "message_edit":
        this.handleMessageEdit(data);
        break;
      case "message_delete":
        this.handleMessageDelete(data);
        break;
      default:
        console.log("Unknown message type:", data.type);
    }
  }

  displayMessage(data) {
    const messageElement = this.createMessageElement(data);
    this.messagesContainer.appendChild(messageElement);
    this.scrollToBottom();
    this.animateMessage(messageElement);
  }

  createMessageElement(data) {
    const isCurrentUser = data.sender === this.username;
    const messageId = data.message_id || `msg-${Date.now()}`;

    const messageHtml = `
    <div id="${messageId}" class="message-item ${isCurrentUser ? "message-sent" : "message-received"} animate-fade-in">
    <div class="flex space-x-3 w-fit max-w-3xl ${isCurrentUser ? "ml-auto" : ""}">
    ${
      !isCurrentUser
        ? `
      <div class="flex-shrink-0 -mt-2">
      <div class="size-5 sm:size-8 lg:size-10 bg-gradient-to-r from-${data.color || "blue"}-500 to-${data.color || "blue"}-600 rounded-full flex items-center justify-center text-white font-bold text-sm shadow-lg">
      ${data.sender ? data.sender.charAt(0).toUpperCase() : "U"}
      </div>
      </div>
      `
        : ""
    }

    <div class="flex-1 mt-1 ${isCurrentUser ? "text-right" : ""}">
    <div class="${isCurrentUser ? "bg-indigo-500 text-white rounded-tr-none" : "bg-white border border-gray-200 rounded-tl-none"} rounded-2xl px-3 py-1 shadow-sm hover:shadow-md transition-all duration-200">
    ${
      !isCurrentUser
        ? `
      <p class="text-[12px] font-semibold text-gray-900 mb-1">${data.sender}</p>
      `
        : ""
    }
    <p class="${isCurrentUser ? "text-white" : "text-gray-800"} leading-relaxed">${this.escapeHtml(data.message)}</p>
    <p class="flex text-xs justify-end ${isCurrentUser ? "text-blue-100" : "text-gray-500"} mt-0.5">
    ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
    </p>
    </div>

    <div class="flex items-center space-x-2 mt-1 ${isCurrentUser ? "justify-end" : ""}">
    <button class="text-gray-400 hover:text-gray-600 transition-colors text-sm" onclick="chat.reactToMessage('${messageId}', '👍')">
    👍
    </button>
    <button class="text-gray-400 hover:text-gray-600 transition-colors text-sm" onclick="chat.reactToMessage('${messageId}', '❤️')">
    ❤️
    </button>
    <button class="text-gray-400 hover:text-gray-600 transition-colors text-sm" onclick="chat.reactToMessage('${messageId}', '😮')">
    😮
    </button>
    <button class="text-gray-500 hover:text-gray-600 transition-colors text-sm" onclick="chat.showMessageActions('${messageId}')">
    ⋮
    </button>
    </div>
    </div>

    ${
      isCurrentUser
        ? `
      <div class="flex-shrink-0 -mt-2">
      <div class="size-5 sm:size-8 lg:size-10 bg-gradient-to-r from-green-500 to-teal-600 rounded-full flex items-center justify-center text-white font-bold text-sm shadow-lg">
      ${this.userinitials}
      </div>
      </div>
      `
        : ""
    }
    </div>
    </div>
    `;

    const template = document.createElement("template");
    template.innerHTML = messageHtml.trim();
    return template.content.firstChild;
  }

  animateMessage(element) {
    element.style.opacity = "0";
    element.style.transform = "translateY(20px)";

    requestAnimationFrame(() => {
      element.style.transition = "all 0.3s ease-out";
      element.style.opacity = "1";
      element.style.transform = "translateY(0)";
    });
  }

  handleUserJoin(data) {
    this.showSystemMessage(`${data.user} joined the room`);
    this.updateOnlineUsers("enter");
  }

  handleUserLeave(data) {
    this.showSystemMessage(`${data.user} left the room`);
    this.updateOnlineUsers("leave");
  }

  /**
   * This additionally flatten original value to disregard 1
   * since it account for current user who is the initial online user added during load,
   * also still triggers join
   * leading to benign users+1
   * */
  updateOnlineUsers(action) {
    const current_onlineusers = parseInt(this.onlineDisplay.textContent);

    let value =
      action === "enter"
        ? current_onlineusers !== 1
          ? current_onlineusers + 1
          : current_onlineusers
        : current_onlineusers - 1;
    value = value >= 0 ? value : 0;

    // Online members cannot except total members, this is beacuse user may be using multiple session
    this.onlineDisplay.textContent =
      value <= parseInt(this.membersDisplay?.textContent | 0)
        ? value
        : parseInt(this.membersDisplay.textContent);
  }

  handleTypingIndicator(data) {
    if (data.typing) {
      this.typingUsersSet.add(data.user);
    } else {
      this.typingUsersSet.delete(data.user);
    }

    this.updateTypingIndicator();
  }

  updateTypingIndicator() {
    if (this.typingUsersSet.size > 0) {
      const users = Array.from(this.typingUsersSet);
      let text = "";

      if (users.length === 1) {
        text = `${users[0]} is typing...`;
      } else if (users.length === 2) {
        text = `${users[0]} and ${users[1]} are typing...`;
      } else {
        text = `${users[0]} and ${users.length - 1} others are typing...`;
      }

      this.typingUsers.textContent = text;
      this.typingIndicator.classList.remove("hidden");
    } else {
      this.typingIndicator.classList.add("hidden");
    }
  }

  showSystemMessage(message, type = "info") {
    const systemMessage = document.createElement("div");
    systemMessage.className = `text-center py-2`;
    systemMessage.innerHTML = `
    <span class="inline-block bg-${type === "error" ? "red" : "gray"}-100 text-${type === "error" ? "red" : "gray"}-700 text-sm px-3 py-1 rounded-full">
    ${this.escapeHtml(message)}
    </span>
    `;
    this.messagesContainer.appendChild(systemMessage);
    this.scrollToBottom();
  }

  setupEventListeners() {
    // Message form submission
    this.messageForm.addEventListener("submit", (e) => {
      e.preventDefault();
      this.sendMessage();
    });

    // Message input events
    this.messageInput.addEventListener("input", () => {
      this.autoResize(this.messageInput);
    });

    this.messageInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });

    // Typing indicators
    this.messageInput.addEventListener("input", () => {
      this.handleLocalTyping();
    });

    this.messageInput.addEventListener("blur", () => {
      this.stopTyping();
    });

    // Keyboard shortcuts
    document.addEventListener("keydown", (e) => {
      if (e.key.toLocaleLowerCase() === "escape") {
        e.preventDefault();
        this.hideMessageActions();
        this.hideRoomSettings();
      }

      // Focus message input with Ctrl+K or Cmd+K
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        this.messageInput.focus();
      }
    });

    // Handle window resize
    window.addEventListener("resize", () => {
      this.autoResize(this.messageInput);
    });
  }

  sendMessage() {
    const message = this.messageInput.value.trim();

    if (
      !message ||
      !this.websocket ||
      this.websocket.readyState !== WebSocket.OPEN
    ) {
      return;
    }

    // Show sending state
    const originalText = this.sendButton.innerHTML;
    this.sendButton.innerHTML = `
    <div class="flex items-center space-x-2">
    <div class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
    <span>Sending...</span>
    </div>
    `;
    this.sendButton.disabled = true;

    // Send message via WebSocket
    this.websocket.send(
      JSON.stringify({
        type: "chat_message",
        message: message,
        sender: this.username,
      }),
    );

    // Clear input and reset button
    this.messageInput.value = "";
    this.autoResize(this.messageInput);
    this.stopTyping();

    // Reset button after short delay
    setTimeout(() => {
      this.sendButton.innerHTML = originalText;
      this.sendButton.disabled = false;
    }, 1000);
  }

  handleLocalTyping() {
    // Clear existing timer
    if (this.typingTimer) {
      clearTimeout(this.typingTimer);
    }

    // Set new timer to stop typing indicator
    this.typingTimer = setTimeout(() => {
      this.stopTyping();
    }, 3000);

    if (!this.isTyping) {
      this.isTyping = true;
      this.websocket.send(
        JSON.stringify({
          type: "typing",
          typing: true,
          user: this.username,
        }),
      );
    }
  }

  stopTyping() {
    if (this.isTyping) {
      this.isTyping = false;
      this.websocket.send(
        JSON.stringify({
          type: "typing",
          typing: false,
          user: this.username,
        }),
      );
    }

    if (this.typingTimer) {
      clearTimeout(this.typingTimer);
    }
  }

  autoResize(textarea) {
    textarea.style.height = "auto";
    textarea.style.height = Math.min(textarea.scrollHeight, 128) + "px";
  }

  scrollToBottom() {
    requestAnimationFrame(() => {
      this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    });
  }

  reactToMessage(messageId, reaction) {
    // Implement reaction functionality
    console.log(`Reacted with ${reaction} to message ${messageId}`);
    // Send reaction via WebSocket
    this.websocket.send(
      JSON.stringify({
        type: "reaction",
        message_id: messageId,
        reaction: reaction,
        user: this.username,
      }),
    );
  }

  showMessageActions(messageId) {
    const modal = document.getElementById("message-actions-modal");
    modal.classList.remove("hidden");
    setTimeout(() => {
      modal
        .querySelector(".bg-white")
        .classList.remove("scale-95", "opacity-0");
      modal
        .querySelector(".bg-white")
        .classList.add("scale-100", "opacity-100");
    }, 10);
  }

  hideMessageActions() {
    const modal = document.getElementById("message-actions-modal");
    const content = modal.querySelector(".bg-white");
    content.classList.remove("scale-100", "opacity-100");
    content.classList.add("scale-95", "opacity-0");
    setTimeout(() => modal.classList.add("hidden"), 300);
  }

  escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  // Utility methods for UI interactions
  toggleMembersSidebar() {
    const sidebar = document.getElementById("members-sidebar");
    const backdrop = document.getElementById("sidebar-backdrop");

    if (sidebar.classList.contains("translate-x-full")) {
      sidebar.classList.remove("translate-x-full");
      backdrop.classList.remove("hidden");
    } else {
      sidebar.classList.add("translate-x-full");
      backdrop.classList.add("hidden");
    }
  }

  showRoomSettings() {
    const modal = document.getElementById("room-settings-modal");
    modal.classList.remove("hidden");
    setTimeout(() => {
      modal
        .querySelector(".bg-white")
        .classList.remove("scale-95", "opacity-0");
      modal
        .querySelector(".bg-white")
        .classList.add("scale-100", "opacity-100");
    }, 10);

    document.getElementById("cancel-settings").addEventListener("click", () => {
      this.hideRoomSettings();
    });
  }

  hideRoomSettings() {
    const modal = document.getElementById("room-settings-modal");
    const content = modal.querySelector(".bg-white");
    content.classList.remove("scale-100", "opacity-100");
    content.classList.add("scale-95", "opacity-0");
    setTimeout(() => modal.classList.add("hidden"), 300);
  }
}

// Initialize chat when DOM is loaded
document.addEventListener("DOMContentLoaded", function () {
  window.chat = new ChatRoom();

  // Close sidebar when clicking backdrop
  document
    .getElementById("sidebar-backdrop")
    .addEventListener("click", function () {
      window.chat.toggleMembersSidebar();
    });

  // Close modals when clicking outside
  document.addEventListener("click", function (e) {
    if (e.target.id === "message-actions-modal") {
      window.chat.hideMessageActions();
    }
    if (e.target.id === "room-settings-modal") {
      window.chat.hideRoomSettings();
    }
  });
  window.chat.room_update_bt.addEventListener("click", function (e) {
    e.preventDefault();
    const r_name = document.getElementById("room_name").value;
    const r_desc = document.getElementById("room_description").value;
    UpdateRoom(window.chat.roomId, {
      room_name: r_name,
      room_description: r_desc,
    });
  });
});

// Global functions for HTML onclick attributes
function toggleMembersSidebar() {
  if (window.chat) window.chat.toggleMembersSidebar();
}

function showRoomSettings() {
  if (window.chat) window.chat.showRoomSettings();
}

function hideMessageActions() {
  if (window.chat) window.chat.hideMessageActions();
}

function showMessageActions(messageId) {
  if (window.chat) window.chat.showMessageActions(messageId);
}

function autoResize(textarea) {
  if (window.chat) window.chat.autoResize(textarea);
}

function handleTyping() {
  if (window.chat) window.chat.handleLocalTyping();
}

async function UpdateRoom(RoomId, room_data) {
  const button = window.chat.room_update_bt;
  const originalContent = window.showLoading(button);

  try {
    const response = await fetch(`/chat/room/${RoomId}/update/`, {
      method: "PATCH",
      headers: {
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify(room_data),
    });

    const data = await response.json();

    if (data.status === "success") {
      window.showMessage("Room updated successfully!", "success");
      window.chat.hideRoomSettings();
      setTimeout(() => location.reload(), 1000);
    } else {
      window.showMessage("Error updating room: " + data.error, "error");
      window.hideLoading(button, originalContent);
    }
  } catch (error) {
    console.error(error);
    window.showMessage("Error updating room: " + error, "error");
    window.hideLoading(button, originalContent);
  }
}

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let c of cookies) {
      const cookie = c.trim();
      if (cookie.startsWith(name + "=")) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  console.log(cookieValue);
  return cookieValue;
}
