document.addEventListener("DOMContentLoaded", function () {
  // 🔍 Search functionality
  const searchInput = document.querySelector(".search-bar");
  const resultsContainer = document.getElementById("search-results");

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
            <strong>${user.full_name}</strong> <span>@${user.username}</span>
          `;
          div.style.cursor = "pointer";
          div.addEventListener("click", () => {
            window.location.href = `/user-profile/${user.username}/`;
          });
          resultsContainer.appendChild(div);
        });
      });
  });

  // 🧭 Section toggle functionality
  const navLinks = document.querySelectorAll(".nav-link");
  const allSections = document.querySelectorAll(".page-section");

  navLinks.forEach(link => {
    link.addEventListener("click", function (e) {
      e.preventDefault();
      const targetId = this.getAttribute("data-target");

      // Hide all page sections
      allSections.forEach(section => {
        section.style.display = "none";
      });

      // Show the target section
      const targetSection = document.getElementById(targetId);
      if (targetSection) {
  // Restore flex display for home-section, block for others
        if (targetId === "home-section") {
          targetSection.style.display = "flex";
          targetSection.style.flexDirection = "column"; // preserve layout
          targetSection.style.gap = "30px";             // reapply spacing if removed
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
let renderedMessageIds = new Set(); // 🧠 Track already-rendered messages

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
      console.warn("Missing senderId (make sure to add data-user-id in HTML)");
      return;
    }

    currentReceiverId = senderId;
    lastFetchedMessageId = null;

    chatAvatar.src = avatar;
    chatName.textContent = name;
    chatMessages.innerHTML = "";
    renderedMessageIds.clear(); // 🧼 Clear previously shown messages
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

  // 🧠 Track whether user is near the bottom
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
        const newScrollHeight = chatMessages.scrollHeight;
        chatMessages.scrollTop = newScrollHeight - previousScrollHeight;
      } else {
        chatMessages.appendChild(fragment);

        // ✅ Scroll to bottom ONLY if already near bottom
        if (isNearBottom) {
          chatMessages.scrollTop = chatMessages.scrollHeight;
        }
      }

      if (data.length > 0) {
        lastFetchedMessageId = data[0].id;
      }
    });
}


chatMessages.addEventListener("scroll", function () {
  if (chatMessages.scrollTop === 0 && lastFetchedMessageId) {
    loader.style.display = "block";
    fetchMessages(lastFetchedMessageId, true);
  }
});

chatForm.addEventListener("submit", function (e) {
  e.preventDefault();
  const message = chatInput.value.trim();
  if (!message || !currentReceiverId) return;

  fetch("/chat/send/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken")
    },
    body: JSON.stringify({
      receiver_id: currentReceiverId,
      message: message
    })
  })
  .then(res => res.json())
  .then(() => {
    chatInput.value = "";
    fetchMessages(); // append new message without wiping
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



  // 📝 Handle post creation
  const postForm = document.getElementById("create-post-form");
  const postContent = document.getElementById("post-content");
  const postMedia = document.getElementById("post-media");
  const postStatus = document.getElementById("post-status");

  postForm.addEventListener("submit", function (e) {
    e.preventDefault();

    const content = postContent.value.trim();
    const mediaFile = postMedia.files[0];

    if (!content) {
      postStatus.textContent = "Please enter some text.";
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
        postForm.reset();
      } else {
        postStatus.textContent = "❌ " + (data.message || "Something went wrong.");
      }
    })
    .catch(err => {
      console.error("Post error:", err);
      postStatus.textContent = "❌ Network error. Try again.";
    });
  });

    // 🎞️ Media preview
  const mediaPreview = document.getElementById("media-preview");

  postMedia.addEventListener("change", function () {
    mediaPreview.innerHTML = ""; // Clear existing

    const file = this.files[0];
    if (!file) return;

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
      mediaPreview.textContent = "Unsupported file type.";
    }
  });




  // 🔁 Lazy Load User Posts (if post-grid exists)
const postGrid = document.querySelector(".post-grid");
if (postGrid) {
  const username = document.body.getAttribute("data-username");
  let offset = postGrid.children.length;
  let isLoading = false;
  let endOfPosts = false;

  window.addEventListener("scroll", async () => {
    if (endOfPosts || isLoading) return;

    if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 300) {
      isLoading = true;
      const loader = document.createElement("p");
      loader.textContent = "Loading more posts...";
      loader.style.textAlign = "center";
      postGrid.appendChild(loader);

      try {
        const response = await fetch(`/user-posts/${username}/?offset=${offset}`);
        const data = await response.json();

        if (!Array.isArray(data) || data.length === 0) {
          endOfPosts = true;
          loader.remove();
          return;
        }

        data.forEach(post => {
          const card = document.createElement("div");
          card.className = "post-card";

          const content = document.createElement("p");
          content.className = "post-content";
          content.textContent = post.content;
          card.appendChild(content);

          if (post.media_url) {
            if (post.media_url.toLowerCase().endsWith(".mp4")) {
              const video = document.createElement("video");
              video.src = post.media_url;
              video.controls = true;
              video.className = "post-media";
              card.appendChild(video);
            } else {
              const img = document.createElement("img");
              img.src = post.media_url;
              img.alt = "Post media";
              img.className = "post-media";
              card.appendChild(img);
            }
          }

          const time = document.createElement("p");
          time.className = "post-time";
          time.textContent = "🕒 " + new Date(post.created_at).toLocaleString();
          card.appendChild(time);

          postGrid.appendChild(card);
        });

        offset += data.length;
        loader.remove();
        isLoading = false;
      } catch (err) {
        console.error("Failed to load more posts", err);
        loader.remove();
      }
    }
  });
}



});

