document.addEventListener("DOMContentLoaded", function () {
  // 🔍 Search functionality
  const searchInput = document.querySelector(".search-bar");
  const resultsContainer = document.getElementById("search-results");

  if (searchInput) {
    searchInput.addEventListener("input", function () {
      const query = this.value.trim();

      if (!query) {
        resultsContainer.innerHTML = "";
        return;
      }

      fetch(`/search-users/?q=${encodeURIComponent(query)}`)
        .then(res => res.json())
        .then(data => {
          resultsContainer.innerHTML = "";

          if (data.length === 0) {
            resultsContainer.innerHTML = "<p>No users found.</p>";
            return;
          }

          data.forEach(user => {
            const div = document.createElement("div");
            div.className = "user-result";
            div.innerHTML = `
              <img src="${user.profile_url}" alt="Profile" width="30" height="30" style="border-radius: 50%;">
              <strong>${user.full_name}</strong>
            `;
            div.style.cursor = "pointer";
            div.addEventListener("click", () => {
              window.location.href = `/user-profile/${user.username}/`;
            });
            resultsContainer.appendChild(div);
          });
        });
    });
  }

  // 🧭 Section toggle functionality
  const navLinks = document.querySelectorAll(".nav-link");
  const allSections = document.querySelectorAll(".page-section");

  navLinks.forEach(link => {
    link.addEventListener("click", function (e) {
      e.preventDefault();
      const targetId = this.getAttribute("data-target");

      // Hide all sections
      allSections.forEach(section => {
        section.style.display = "none";
      });

      // Show the target section
      const targetSection = document.getElementById(targetId);
      if (targetSection) {
        if (targetId === "home-section") {
          targetSection.style.display = "flex";
          targetSection.style.flexDirection = "column";
          targetSection.style.gap = "30px";
        } else {
          targetSection.style.display = "block";
        }
      }
    });
  });

  // 📨 Floating Chat logic
  let pollingInterval = null;
  let lastFetchedMessageId = null;
  let currentReceiverId = null;
  let renderedMessageIds = new Set();

  const chatBox = document.getElementById("floating-chat-box");
  const chatMessages = document.getElementById("chat-messages");
  const chatForm = document.getElementById("chat-form");
  const chatInput = document.getElementById("chat-input");
  const chatAvatar = document.getElementById("chat-user-avatar");
  const chatName = document.getElementById("chat-user-name");
  const loader = document.getElementById("chat-loader");

  document.querySelectorAll(".message-list li").forEach(item => {
    item.addEventListener("click", function () {
      const name = this.querySelector("strong").textContent.trim();
      const avatar = this.querySelector("img").src;
      const senderId = this.querySelector("img").getAttribute("data-user-id") || null;

      if (!senderId) {
        console.warn("Missing senderId");
        return;
      }

      currentReceiverId = senderId;
      lastFetchedMessageId = null;

      chatAvatar.src = avatar;
      chatName.textContent = name;
      chatMessages.innerHTML = "";
      renderedMessageIds.clear();
      loader.style.display = "block";
      chatBox.style.display = "flex";

      fetchMessages();
      if (pollingInterval) clearInterval(pollingInterval);
      pollingInterval = setInterval(() => fetchMessages(), 3000);
    });
  });

  window.closeChatBox = function () {
    chatBox.style.display = "none";
    chatMessages.innerHTML = "";
    clearInterval(pollingInterval);
    renderedMessageIds.clear();
  };

  function fetchMessages(beforeId = null, append = false) {
    if (!currentReceiverId) return Promise.resolve();

    let url = `/chat/messages/?receiver_id=${currentReceiverId}&limit=10`;
    if (beforeId) url += `&before_id=${beforeId}`;

    const previousScrollHeight = chatMessages.scrollHeight;
    const isNearBottom = chatMessages.scrollTop + chatMessages.clientHeight >= chatMessages.scrollHeight - 50;

    return fetch(url)
      .then(res => res.json())
      .then(data => {
        loader.style.display = "none";
        if (data.length === 0) return;

        const fragment = document.createDocumentFragment();
        data.forEach(msg => {
          if (!renderedMessageIds.has(msg.id)) {
            const div = document.createElement("div");
            div.className = `chat-message ${msg.is_you ? "you" : "them"}`;
            div.innerHTML = `${msg.message}<div class="chat-time">${msg.time}</div>`;
            fragment.appendChild(div);
            renderedMessageIds.add(msg.id);
          }
        });

        if (append) {
          chatMessages.insertBefore(fragment, chatMessages.firstChild);
          chatMessages.scrollTop = chatMessages.scrollHeight - previousScrollHeight;
        } else {
          chatMessages.appendChild(fragment);
          if (isNearBottom) {
            chatMessages.scrollTop = chatMessages.scrollHeight;
          }
        }

        if (data.length > 0) {
          lastFetchedMessageId = data[0].id;
        }
      });
  }

  chatMessages?.addEventListener("scroll", function () {
    if (chatMessages.scrollTop === 0 && lastFetchedMessageId) {
      loader.style.display = "block";
      fetchMessages(lastFetchedMessageId, true);
    }
  });

  chatForm?.addEventListener("submit", function (e) {
    e.preventDefault();
    const message = chatInput.value.trim();
    if (!message || !currentReceiverId) return;

    fetch("/chat/send/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken")
      },
      body: JSON.stringify({ receiver_id: currentReceiverId, message })
    })
      .then(res => res.json())
      .then(() => {
        chatInput.value = "";
        fetchMessages();
      });
  });

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      const cookies = document.cookie.split(";");
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.startsWith(name + "=")) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  // 📝 Post creation logic
  const postForm = document.getElementById("create-post-form");
const postContent = document.getElementById("post-content");
const postMedia = document.getElementById("post-media");
const postStatus = document.getElementById("post-status");
const mediaPreview = document.getElementById("media-preview");

postForm?.addEventListener("submit", function (e) {
  e.preventDefault();

  const content = postContent.value.trim();
  const mediaFile = postMedia.files[0];

  postStatus.textContent = "";
  postStatus.style.color = "";

  if (!content) {
    postStatus.textContent = "❌ Please enter some text.";
    postStatus.style.color = "red";
    return;
  }

  // Check again on submit in case user bypassed the onchange check
  if (mediaFile && mediaFile.size > 30 * 1024 * 1024) {
    postStatus.textContent = "❌ File should be less than 30MB.";
    postStatus.style.color = "red";
    return;
  }

  const formData = new FormData();
  formData.append("content", content);
  if (mediaFile) {
    formData.append("media", mediaFile);
  }

  fetch("/create-post/", {
    method: "POST",
    headers: {
      "X-CSRFToken": getCookie("csrftoken")
    },
    body: formData
  })
    .then(res => res.json())
    .then(data => {
      if (data.status === "success") {
        postStatus.textContent = "✅ Post created!";
        postStatus.style.color = "green";
        postForm.reset();
        mediaPreview.innerHTML = "";
        setTimeout(() => {
          window.location.reload(); // Reload to show new post
        }, 1000);
      } else {
        postStatus.textContent = "❌ " + (data.message || "Something went wrong.");
        postStatus.style.color = "red";
      }
    })
    .catch(err => {
      console.error("Post error:", err);
      postStatus.textContent = "❌ Network error. Try again.";
      postStatus.style.color = "red";
    });
});

// 🎞️ Media preview + validation (on file select)
postMedia?.addEventListener("change", function () {
  mediaPreview.innerHTML = "";
  postStatus.textContent = "";
  postStatus.style.color = "";

  const file = this.files[0];
  if (!file) return;

  if (file.size > 30 * 1024 * 1024) {
    postStatus.textContent = "❌ File should be less than 30MB.";
    postStatus.style.color = "red";
    this.value = ""; // clear input
    return;
  }

  const url = URL.createObjectURL(file);
  if (file.type.startsWith("image/")) {
    const img = document.createElement("img");
    img.src = url;
    mediaPreview.appendChild(img);
  } else if (file.type.startsWith("video/")) {
    const video = document.createElement("video");
    video.src = url;
    video.controls = true;
    mediaPreview.appendChild(video);
  } else {
    postStatus.textContent = "❌ Unsupported file type.";
    postStatus.style.color = "red";
    this.value = ""; // clear input
  }
});

// 🧠 CSRF helper
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.startsWith(name + "=")) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

});
