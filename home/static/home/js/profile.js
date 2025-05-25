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

    const postButton = postForm.querySelector('button[type="submit"]');
    postButton.disabled = true;
    postButton.textContent = "Posting...";


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



// 🌍 Global Feed Lazy Loader
const globalGrid = document.getElementById("global-post-grid");
if (globalGrid) {
  let offset = 0;
  let isLoading = false;
  let endOfPosts = false;

async function loadGlobalPosts() {
  if (isLoading || endOfPosts) return;
  isLoading = true;

  const loader = document.createElement("p");
  loader.textContent = "Loading posts...";
  loader.style.textAlign = "center";
  globalGrid.appendChild(loader);

  try {
    const response = await fetch(`/global-posts/?offset=${offset}`);
    const posts = await response.json();

    if (!Array.isArray(posts) || posts.length === 0) {
      endOfPosts = true;
      loader.remove();
      return;
    }

    posts.forEach(post => {
      const card = document.createElement("div");
      card.className = "post-card";

      // Header
      const header = document.createElement("div");
      header.className = "post-header";
      header.innerHTML = `
        <img src="${post.user.profile_url}" class="post-avatar" alt="Avatar">
        <div class="post-user-info">
          <p class="post-author">${post.user.full_name}</p>
          <p class="post-time">🕒 ${new Date(post.created_at).toLocaleString()}</p>
        </div>
      `;
      card.appendChild(header);

      // Content
      const content = document.createElement("p");
      content.className = "post-content";
      content.textContent = post.content;
      card.appendChild(content);

      // Media
      if (post.media_url) {
        const url = post.media_url.toLowerCase();
        let media;
        if (url.includes(".mp4") || url.includes(".webm")) {
          media = `<video src="${post.media_url}" controls class="post-media"></video>`;
        } else {
          media = `<img src="${post.media_url}" class="post-media" alt="Post media">`;
        }
        card.insertAdjacentHTML("beforeend", media);
      }

      // Actions
      const actions = document.createElement("div");
      actions.className = "post-actions";
      actions.innerHTML = `
        <div class="like-form">
          <button type="button" class="like-button"
                  data-post-id="${post.id}"
                  data-liked="${post.liked_by_user}">
            ${post.liked_by_user ? "💖 Liked" : "❤️ Like"}
          </button>
          <span class="like-count" id="like-count-${post.id}">
            ${post.like_count} like${post.like_count !== 1 ? "s" : ""}
          </span>
        </div>
        <form class="comment-form" data-post-id="${post.id}">
          <input type="text" name="comment" placeholder="Add a comment..." required>
          <button type="submit">💬</button>
          <span class="comment-count">
            ${post.comment_count} comment${post.comment_count !== 1 ? "s" : ""}
          </span>
        </form>
      `;
      card.appendChild(actions);

      // Comment preview + view all
      const preview = document.createElement("div");
      preview.className = "post-comments-preview";
      preview.id = `preview-comments-${post.id}`;

     const viewAll = document.createElement("a");
    viewAll.href = "#";
    viewAll.className = "view-all-comments";
    viewAll.dataset.postId = post.id;
    viewAll.textContent = `💬 View all ${post.comment_count} comment${post.comment_count !== 1 ? "s" : ""}`;
    preview.appendChild(viewAll);

      card.appendChild(preview);

      // Full comment section (initially hidden)
      const full = document.createElement("div");
      full.className = "post-comments-full";
      full.id = `full-comments-${post.id}`;
      full.style.display = "none";
      card.appendChild(full);

      globalGrid.appendChild(card);
    });

    offset += posts.length;
    loader.remove();
    isLoading = false;
    attachGlobalLikeHandlers();
    attachGlobalCommentHandlers();
    attachGlobalViewCommentsHandlers();

  } catch (err) {
    console.error("Failed to load global posts", err);
    loader.remove();
  }
}


  function attachGlobalLikeHandlers() {
    document.querySelectorAll(".like-button").forEach(button => {
      button.removeEventListener("click", handleGlobalLikeClick);
      button.addEventListener("click", handleGlobalLikeClick);
    });
  }


  function attachGlobalViewCommentsHandlers() {
  document.querySelectorAll(".view-all-comments").forEach(link => {
    link.removeEventListener("click", handleViewAllClick);
    link.addEventListener("click", handleViewAllClick);
  });
}

async function getUserInfo(userId) {
  if (!getUserInfo.cache) getUserInfo.cache = {};

  if (getUserInfo.cache[userId]) {
    return getUserInfo.cache[userId];
  }

  const res = await fetch(`/get-user-info/${userId}/`);
  const data = await res.json();
  getUserInfo.cache[userId] = data;
  return data;
}


async function handleViewAllClick(e) {
  e.preventDefault();
  const link = e.currentTarget;
  const postId = link.dataset.postId;
  const full = document.getElementById(`full-comments-${postId}`);

  if (full.style.display === "block") {
    full.style.display = "none";
    link.textContent = `💬 View all comments`;
    return;
  }

  full.innerHTML = "<p>⏳ Loading comments...</p>";
  full.style.display = "block";

  try {
    const res = await fetch(`/get-post-comments/${postId}/`);
    const comments = await res.json();

    const elements = await Promise.all(comments.map(async comment => {
      const user = await getUserInfo(comment.user_id);
      return `
        <p>
          <img src="${user.profile_url}" alt="Avatar" class="comment-avatar">
          <strong>${user.full_name}</strong> ${comment.comment}
          <span class="comment-time">${new Date(comment.created_at).toLocaleString()}</span>
        </p>
      `;
    }));

    full.innerHTML = elements.join("");
    link.textContent = `⬆️ Hide comments`;
  } catch (err) {
    console.error("Failed to load comments", err);
    full.innerHTML = "<p style='color:red;'>❌ Failed to load comments.</p>";
  }
}


  async function handleGlobalLikeClick(event) {
    const button = event.currentTarget;
    const postId = button.getAttribute("data-post-id");

    try {
      const response = await fetch(`/like-post/${postId}/`, {
        method: "POST",
        headers: {
          "X-CSRFToken": getCookie("csrftoken")
        }
      });

      const data = await response.json();
      if (data.status === "success") {
        button.setAttribute("data-liked", data.liked.toString());
        button.innerHTML = data.liked ? "💖 Liked" : "❤️ Like";
        const countSpan = document.getElementById(`like-count-${postId}`);
        countSpan.textContent = `${data.new_count} like${data.new_count !== 1 ? "s" : ""}`;
      }
    } catch (err) {
      console.error("Like failed", err);
    }
  }

  function attachGlobalCommentHandlers() {
    document.querySelectorAll(".comment-form").forEach(form => {
      form.removeEventListener("submit", handleGlobalCommentSubmit);
      form.addEventListener("submit", handleGlobalCommentSubmit);
    });
  }

  async function handleGlobalCommentSubmit(e) {
    e.preventDefault();
    const form = e.currentTarget;
    const postId = form.dataset.postId;
    const input = form.querySelector("input[name='comment']");
    const commentText = input.value.trim();
    const countSpan = form.querySelector(".comment-count");

    if (!commentText) return;

    try {
      const response = await fetch(`/comment-post/${postId}/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken")
        },
        body: JSON.stringify({ comment: commentText })
      });

      const result = await response.json();
      if (result.status === "success") {
        input.value = "";
        const currentCount = parseInt(countSpan.textContent) || 0;
        const newCount = currentCount + 1;
        countSpan.textContent = `${newCount} comment${newCount !== 1 ? "s" : ""}`;
      } else {
        console.error("Comment failed:", result.message);
      }
    } catch (err) {
      console.error("Comment error", err);
    }
  }

  // Auto load first batch
  loadGlobalPosts();

  // Infinite scroll
  window.addEventListener("scroll", () => {
    if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 300) {
      loadGlobalPosts();
    }
  });
}


// ✅ notifications

const communitySection = document.getElementById("community-section");
let communityLoaded = false; // ✅ Only load once per page

function loadFollowedPosts() {
  const list = communitySection.querySelector("ul");
  list.innerHTML = "<li>⏳ Loading recent posts from your network...</li>";

  fetch("/followed-posts/")
    .then(res => res.json())
    .then(data => {
      list.innerHTML = "";

      if (!data.length) {
        list.innerHTML = "<li>No recent activity from people you follow.</li>";
        return;
      }

      data.forEach(post => {
        const li = document.createElement("li");
        const timeAgo = timeSince(new Date(post.timestamp));
        li.innerHTML = `
          <img src="${post.author_avatar}" alt="${post.author_name}" class="community-avatar" />
          <span>
            <strong>
              <a href="/user-profile/${post.username}/" style="color: #0984e3; text-decoration: none;">
                ${post.author_name}
              </a>
            </strong> posted: “${post.content}”
            <br><small style="color: #888;">${timeAgo}</small>
          </span>
        `;
        list.appendChild(li);
      });
    })
    .catch(() => {
      list.innerHTML = "<li>❌ Failed to load community posts.</li>";
    });
}

// ✅ Load only once when Community tab is first clicked
document.querySelector('[data-target="community-section"]')?.addEventListener("click", () => {
  if (!communityLoaded) {
    loadFollowedPosts();
    communityLoaded = true;
  }
});

// 🕒 Friendly "X ago" time function
function timeSince(date) {
  const seconds = Math.floor((new Date() - date) / 1000);
  const intervals = [
    { label: "year", seconds: 31536000 },
    { label: "month", seconds: 2592000 },
    { label: "day", seconds: 86400 },
    { label: "hour", seconds: 3600 },
    { label: "minute", seconds: 60 },
    { label: "second", seconds: 1 }
  ];

  for (const interval of intervals) {
    const count = Math.floor(seconds / interval.seconds);
    if (count > 0) {
      return `${count} ${interval.label}${count !== 1 ? "s" : ""} ago`;
    }
  }
  return "just now";
}



});
