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
});
