/**
 * Auto-inject GitHub avatars into project cards across all pages.
 * Scans for GitHub links, fetches avatars from GitHub API, and inserts them.
 */
(function () {
  // Avatar cache: repo -> { avatar, stars, language }
  var AVATAR_CACHE = {
    "1panel-dev/maxkb": { avatar: "https://avatars.githubusercontent.com/u/109613420?v=4&s=64", stars: 21407, language: "Python" },
    "aider-ai/aider": { avatar: "https://avatars.githubusercontent.com/u/172139148?v=4&s=64", stars: 46647, language: "Python" },
    "aigc-apps/easyanimate": { avatar: "https://avatars.githubusercontent.com/u/141981933?v=4&s=64", stars: 2265, language: "Python" },
    "black-forest-labs/flux": { avatar: "https://avatars.githubusercontent.com/u/164064024?v=4&s=64", stars: 25660, language: "Python" },
    "browser-use/browser-use": { avatar: "https://avatars.githubusercontent.com/u/192012301?v=4&s=64", stars: 100427, language: "Python" },
    "comfyanonymous/comfyui": { avatar: "https://avatars.githubusercontent.com/u/166579949?v=4&s=64", stars: 118162, language: "Python" },
    "continuedev/continue": { avatar: "https://avatars.githubusercontent.com/u/127876214?v=4&s=64", stars: 34405, language: "TypeScript" },
    "crewaiinc/crewai": { avatar: "https://avatars.githubusercontent.com/u/170677839?v=4&s=64", stars: 54275, language: "Python" },
    "guoyww/animatediff": { avatar: "https://avatars.githubusercontent.com/u/93254373?v=4&s=64", stars: 12155, language: "Python" },
    "infiniflow/ragflow": { avatar: "https://avatars.githubusercontent.com/u/69962740?v=4&s=64", stars: 83515, language: "Go" },
    "kwai-kolors/kolors": { avatar: "https://avatars.githubusercontent.com/u/171549236?v=4&s=64", stars: 4608, language: "Python" },
    "labring/fastgpt": { avatar: "https://avatars.githubusercontent.com/u/102226726?v=4&s=64", stars: 28613, language: "TypeScript" },
    "langchain-ai/langchain": { avatar: "https://avatars.githubusercontent.com/u/126733545?v=4&s=64", stars: 140073, language: "Python" },
    "langgenius/dify": { avatar: "https://avatars.githubusercontent.com/u/127165244?v=4&s=64", stars: 146410, language: "TypeScript" },
    "lllyasviel/fooocus": { avatar: "https://avatars.githubusercontent.com/u/19834515?v=4&s=64", stars: 50495, language: "Python" },
    "mannaandpoem/openmanus": { avatar: "https://avatars.githubusercontent.com/u/52203545?v=4&s=64", stars: 504, language: "Unknown" },
    "mintplex-labs/anything-llm": { avatar: "https://avatars.githubusercontent.com/u/134426827?v=4&s=64", stars: 62011, language: "JavaScript" },
    "openai/codex": { avatar: "https://avatars.githubusercontent.com/u/14957082?v=4&s=64", stars: 93301, language: "Rust" },
    "qwenlm/qwen2.5-coder": { avatar: "https://avatars.githubusercontent.com/u/141221163?v=4&s=64", stars: 16646, language: "Python" },
    "significant-gravitas/autogpt": { avatar: "https://avatars.githubusercontent.com/u/130738209?v=4&s=64", stars: 185141, language: "Python" },
    "thudm/cogvideo": { avatar: "https://avatars.githubusercontent.com/u/223098841?v=4&s=64", stars: 12815, language: "Python" },
    "wan-video/wan2.1": { avatar: "https://avatars.githubusercontent.com/u/200620180?v=4&s=64", stars: 16316, language: "Python" },
    "anthropics/claude-code": { avatar: "/static/claude-icon.jpg", stars: 134108, language: "Python" },
    "ollama/ollama": { avatar: "https://avatars.githubusercontent.com/u/151674099?v=4&s=64", stars: 174828, language: "Go" },
    "open-webui/open-webui": { avatar: "https://avatars.githubusercontent.com/u/158137808?v=4&s=64", stars: 142821, language: "Python" },
    "getcursor/cursor": { avatar: "https://avatars.githubusercontent.com/u/126759922?v=4&s=64", stars: 32986, language: "TypeScript" },
    "cursor/cursor": { avatar: "https://avatars.githubusercontent.com/u/126759922?v=4&s=64", stars: 32986, language: "TypeScript" },
    "openclaw/openclaw": { avatar: "https://avatars.githubusercontent.com/u/252820863?v=4&s=64", stars: 380230, language: "TypeScript" },
    "tinyhumansai/openhuman": { avatar: "https://avatars.githubusercontent.com/u/246003628?v=4&s=64", stars: 32899, language: "Rust" },
    "qwenlm/qwen-code": { avatar: "https://avatars.githubusercontent.com/u/141221163?v=4&s=64", stars: 25484, language: "TypeScript" }
  };

  var LANG_COLORS = {
    Python: "#3572A5", TypeScript: "#3178c6", Go: "#00ADD8",
    JavaScript: "#f1e05a", Rust: "#dea584", Unknown: "#ccc"
  };

  function formatStars(n) {
    if (n >= 1000) return (n / 1000).toFixed(1).replace(/\.0$/, "") + "K";
    return String(n);
  }

  function getRepoFromLink(href) {
    var m = href.match(/github\.com\/([^/]+\/[^/]+?)(?:\/|$|\?)/);
    return m ? m[1].toLowerCase() : null;
  }

  function injectAvatar(card, repoKey) {
    var data = AVATAR_CACHE[repoKey];
    if (!data) return false;

    // Check if already injected
    if (card.querySelector(".gh-avatar, .gh-avatar-fallback")) return true;

    // Find the name element
    var nameEl = card.querySelector(".agent-name, .ai-name, .proj-name, .card-title, .sv-topic-name");
    if (!nameEl) return false;

    // Make name a flex container if not already
    var computed = getComputedStyle(nameEl);
    if (computed.display !== "flex" && computed.display !== "inline-flex") {
      nameEl.style.display = "flex";
      nameEl.style.alignItems = "center";
      nameEl.style.gap = "8px";
    }

    // Create avatar element (img if avatar URL exists, otherwise fallback div)
    if (data.avatar) {
      var avatar = document.createElement("img");
      avatar.className = "gh-avatar";
      avatar.src = data.avatar;
      avatar.alt = "";
      avatar.loading = "lazy";
      avatar.style.cssText = "width:32px;height:32px;border-radius:8px;flex-shrink:0;object-fit:cover;background:#f0f0f0";
      nameEl.insertBefore(avatar, nameEl.firstChild);
    } else {
      // Fallback: colored circle with initials
      var fallback = document.createElement("div");
      fallback.className = "gh-avatar-fallback";
      var nameText = nameEl.textContent.trim().charAt(0).toUpperCase();
      fallback.textContent = nameText;
      var colors = ["#667eea","#764ba2","#f093fb","#4facfe","#43e97b","#fa709a","#fee140","#30cfd0"];
      var colorIdx = nameText.charCodeAt(0) % colors.length;
      fallback.style.cssText = "width:32px;height:32px;border-radius:8px;flex-shrink:0;display:flex;align-items:center;justify-content:center;color:#fff;font-size:14px;font-weight:700;background:" + colors[colorIdx];
      nameEl.insertBefore(fallback, nameEl.firstChild);
    }

    // Add stars + language after description if possible
    var descEl = card.querySelector(".agent-desc, .ai-desc, .proj-desc, .card-desc, .sv-topic-desc");
    if (descEl && !card.querySelector(".gh-meta")) {
      var meta = document.createElement("div");
      meta.className = "gh-meta";
      meta.style.cssText = "display:flex;align-items:center;gap:10px;font-size:11px;color:#888;margin-top:8px;padding-top:8px;border-top:1px solid #f0f0f0";

      var stars = document.createElement("span");
      stars.style.cssText = "font-weight:600;color:#8b5e00";
      stars.textContent = "★ " + formatStars(data.stars);

      var lang = document.createElement("span");
      lang.style.cssText = "display:inline-flex;align-items:center;gap:3px";
      var dot = document.createElement("span");
      dot.style.cssText = "width:8px;height:8px;border-radius:50%;display:inline-block;background:" + (LANG_COLORS[data.language] || "#ccc");
      lang.appendChild(dot);
      lang.appendChild(document.createTextNode(data.language === "Unknown" ? "—" : data.language));

      meta.appendChild(stars);
      meta.appendChild(lang);

      // Insert after description
      descEl.parentNode.insertBefore(meta, descEl.nextSibling);
    }

    return true;
  }

  function scanCards() {
    // Target various card types across pages
    var cards = document.querySelectorAll(".agent-card, .sv-topic-card, .sv-project-card, .project-card:not(.ai-card)");
    var injected = 0;
    cards.forEach(function (card) {
      var links = card.querySelectorAll('a[href*="github.com"]');
      for (var i = 0; i < links.length; i++) {
        var repo = getRepoFromLink(links[i].href);
        if (repo && AVATAR_CACHE[repo]) {
          if (injectAvatar(card, repo)) injected++;
          break;
        }
      }
    });
    return injected;
  }

  // Run on DOM ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      var n = scanCards();
      if (n > 0) console.log("[GitHub Avatars] Injected " + n + " avatars");
    });
  } else {
    var n = scanCards();
    if (n > 0) console.log("[GitHub Avatars] Injected " + n + " avatars");
  }
})();
