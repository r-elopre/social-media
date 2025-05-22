document.addEventListener("DOMContentLoaded", function () {
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

  function attachLikeHandlers() {
    document.querySelectorAll(".like-button").forEach(button => {
      button.removeEventListener("click", handleLikeClick); // clean re-bind
      button.addEventListener("click", handleLikeClick);
    });
  }

  async function handleLikeClick(event) {
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
      } else {
        console.error("Server error:", data.message);
      }
    } catch (err) {
      console.error("Network error:", err);
    }
  }

  attachLikeHandlers();

  // 🔁 Lazy Load Posts
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

            // Post header
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
              if (url.endsWith(".mp4") || url.endsWith(".webm")) {
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

            // Actions
            const actions = document.createElement("div");
            actions.className = "post-actions";
            actions.innerHTML = `
              <div class="like-form">
                <button type="button" class="like-button"
                        data-post-id="${post.id}"
                        data-liked="${post.liked_by_user ? "true" : "false"}">
                  ${post.liked_by_user ? "💖 Liked" : "❤️ Like"}
                </button>
                <span class="like-count" id="like-count-${post.id}">
                  ${post.like_count} like${post.like_count !== 1 ? "s" : ""}
                </span>
              </div>
              <form method="POST" action="/comment-post/${post.id}/" class="comment-form">
                <input type="text" name="comment" placeholder="Add a comment..." required>
                <button type="submit">💬</button>
                <span class="comment-count">${post.comment_count} comment${post.comment_count !== 1 ? "s" : ""}</span>
              </form>
            `;
            card.appendChild(actions);

            postGrid.appendChild(card);
          });

          offset += data.length;
          loader.remove();
          isLoading = false;

          attachLikeHandlers(); // re-bind after new posts
        } catch (err) {
          console.error("Failed to load more posts", err);
          loader.remove();
        }
      }
    });
  }


// Cache user info to avoid redundant requests
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

document.querySelectorAll(".view-all-comments").forEach(link => {
  link.addEventListener("click", async function (e) {
    e.preventDefault();

    const postId = this.dataset.postId;
    const full = document.getElementById(`full-comments-${postId}`);

    // Toggle hide
    if (full.style.display === "block") {
      full.style.display = "none";
      this.textContent = `💬 View all comments`;
      return;
    }

    // Show loading
    full.innerHTML = "<p>⏳ Loading comments...</p>";
    full.style.display = "block";

    try {
      const response = await fetch(`/get-post-comments/${postId}/`);
      const comments = await response.json();

      const commentElements = await Promise.all(comments.map(async comment => {
        const user = await getUserInfo(comment.user_id);
        return `
          <p>
            <img src="${user.profile_url}" alt="Avatar" class="comment-avatar">
            <strong>${user.full_name}</strong> ${comment.comment}
            <span class="comment-time">${new Date(comment.created_at).toLocaleString()}</span>
          </p>
        `;
      }));

      full.innerHTML = commentElements.join("");
      this.textContent = `⬆️ Hide comments`;

    } catch (err) {
      full.innerHTML = "<p style='color: red;'>❌ Failed to load comments.</p>";
      console.error("Failed to load comments", err);
    }
  });
});


document.querySelectorAll(".comment-form").forEach(form => {
  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const postId = this.dataset.postId;
    const input = this.querySelector("input[name='comment']");
    const commentText = input.value.trim();
    const countSpan = this.querySelector(".comment-count");

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
        console.error("Error:", result.message);
      }
    } catch (err) {
      console.error("Comment submit error", err);
    }
  });
});






});
