document.addEventListener("DOMContentLoaded", function () {
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
});
