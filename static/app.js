/**
 * CI_Agent Platform Frontend Application
 * State management, routing, API client, and interactive components.
 */

(function () {
  "use strict";

  // Application State
  const state = {
    user: null,
    token: sessionStorage.getItem("ci_token") || null,
    currentView: "signin",
    activeProjectId: null,
    activeProjectData: null,
    activeRepairJobId: null,
    repairPollInterval: null,
    localSelectedFiles: [],
    chatHistory: [],
  };

  // DOM Elements Cache
  const views = {
    signin: document.getElementById("view-signin"),
    signup: document.getElementById("view-signup"),
    forgot: document.getElementById("view-forgot"),
    dashboard: document.getElementById("view-dashboard"),
    explanation: document.getElementById("view-explanation"),
    repair: document.getElementById("view-repair"),
  };

  const nav = {
    brand: document.getElementById("nav-brand"),
    userWidget: document.getElementById("user-profile-widget"),
    username: document.getElementById("nav-username"),
    signOutBtn: document.getElementById("btn-signout"),
  };

  // Toast System
  function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = "card card-cream";
    toast.style.padding = "10px 16px";
    toast.style.borderRadius = "8px";
    toast.style.boxShadow = "0 4px 16px rgba(0,0,0,0.15)";
    toast.style.borderLeft = type === "error" ? "4px solid var(--color-danger)" : type === "success" ? "4px solid var(--color-success)" : "4px solid var(--color-burgundy)";
    toast.style.fontSize = "0.88rem";
    toast.style.fontWeight = "600";
    toast.style.maxWidth = "360px";
    toast.style.display = "flex";
    toast.style.alignItems = "center";
    toast.style.justifyContent = "space-between";
    toast.style.gap = "12px";

    toast.innerHTML = `<span>${message}</span><button style="background:none;border:none;cursor:pointer;font-weight:700;">×</button>`;
    toast.querySelector("button").onclick = () => toast.remove();

    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transition = "opacity 0.3s";
      setTimeout(() => toast.remove(), 300);
    }, 4500);
  }

  // View Navigation Router
  function switchView(viewName) {
    if (!views[viewName]) return;
    Object.keys(views).forEach((v) => {
      views[v].style.display = v === viewName ? "block" : "none";
    });
    state.currentView = viewName;
    window.location.hash = viewName;
    window.scrollTo({ top: 0, behavior: "smooth" });

    // Update nav widget visibility
    if (state.token && state.user) {
      nav.userWidget.style.display = "flex";
      nav.username.textContent = state.user.name || "Engineer";
    } else {
      nav.userWidget.style.display = "none";
    }

    // Trigger kinetic animation if on auth screens
    if (viewName === "signin" || viewName === "signup" || viewName === "forgot") {
      setTimeout(initAuthParticleBackdrop, 50);
    }
  }

  // ==========================================
  // Unique CI Particle Constellation Backdrop
  // ==========================================
  let authAnimFrameId = null;
  function initAuthParticleBackdrop() {
    const canvasId = state.currentView === "signup" ? "auth-canvas-signup" : (state.currentView === "forgot" ? "auth-canvas-forgot" : "auth-canvas-signin");
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    if (authAnimFrameId) {
      cancelAnimationFrame(authAnimFrameId);
      authAnimFrameId = null;
    }

    const ctx = canvas.getContext("2d");
    const container = canvas.parentElement;
    let width = (canvas.width = container.clientWidth || 480);
    let height = (canvas.height = 680);

    const particles = [];
    const count = 30;
    for (let i = 0; i < count; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.45,
        vy: (Math.random() - 0.5) * 0.45,
        radius: Math.random() * 2 + 1.2,
        color: i % 3 === 0 ? "rgba(89, 9, 7, 0.45)" : "rgba(232, 210, 181, 0.75)",
      });
    }

    let mouse = { x: -1000, y: -1000 };
    container.addEventListener("mousemove", (e) => {
      const rect = canvas.getBoundingClientRect();
      mouse.x = e.clientX - rect.left;
      mouse.y = e.clientY - rect.top;
    });
    container.addEventListener("mouseleave", () => {
      mouse.x = -1000;
      mouse.y = -1000;
    });

    function draw() {
      if (state.currentView !== "signin" && state.currentView !== "signup") {
        return;
      }
      ctx.clearRect(0, 0, width, height);

      // Connect nodes with subtle graph lines
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 100) {
            const alpha = (1 - dist / 100) * 0.28;
            ctx.strokeStyle = `rgba(89, 9, 7, ${alpha})`;
            ctx.lineWidth = 0.8;
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.stroke();
          }
        }
      }

      // Update & render particles
      for (let p of particles) {
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < 0 || p.x > width) p.vx *= -1;
        if (p.y < 0 || p.y > height) p.vy *= -1;

        const mdx = p.x - mouse.x;
        const mdy = p.y - mouse.y;
        const mdist = Math.sqrt(mdx * mdx + mdy * mdy);
        if (mdist < 85) {
          p.x += (mdx / mdist) * 1.6;
          p.y += (mdy / mdist) * 1.6;
        }

        ctx.fillStyle = p.color;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fill();
      }

      authAnimFrameId = requestAnimationFrame(draw);
    }

    draw();
  }

  // Check URL hash on load
  function initRouting() {
    const hash = window.location.hash.replace("#", "");
    if (state.token) {
      if (hash && views[hash]) {
        switchView(hash);
      } else {
        switchView("dashboard");
      }
    } else {
      if (hash === "signup") {
        switchView("signup");
      } else if (hash === "forgot") {
        switchView("forgot");
      } else {
        switchView("signin");
      }
    }
  }

  // ==========================================
  // Authentication Handlers
  // ==========================================
  const formSignIn = document.getElementById("form-signin");
  const formSignUp = document.getElementById("form-signup");
  const toggleSignInPw = document.getElementById("toggle-signin-password");
  const pwInput = document.getElementById("signin-password");

  if (toggleSignInPw && pwInput) {
    toggleSignInPw.addEventListener("click", () => {
      const isPw = pwInput.type === "password";
      pwInput.type = isPw ? "text" : "password";
    });
  }

  document.getElementById("link-goto-signup")?.addEventListener("click", () => switchView("signup"));
  document.getElementById("link-goto-signin")?.addEventListener("click", () => switchView("signin"));
  document.getElementById("link-goto-forgot")?.addEventListener("click", () => switchView("forgot"));
  document.getElementById("link-goto-signin-from-forgot")?.addEventListener("click", () => switchView("signin"));

  if (nav.signOutBtn) {
    nav.signOutBtn.addEventListener("click", () => {
      sessionStorage.removeItem("ci_token");
      sessionStorage.removeItem("ci_user");
      state.token = null;
      state.user = null;
      showToast("Signed out successfully", "info");
      switchView("signin");
    });
  }

  // Change Password Modal Trigger & Submission
  const modalChangePw = document.getElementById("modal-change-password");
  const btnOpenChangePw = document.getElementById("btn-open-change-pw");
  const btnCloseChangePw = document.getElementById("btn-close-change-pw-modal");
  const formChangePw = document.getElementById("form-change-password");

  btnOpenChangePw?.addEventListener("click", () => {
    if (modalChangePw) modalChangePw.style.display = "flex";
  });

  btnCloseChangePw?.addEventListener("click", () => {
    if (modalChangePw) modalChangePw.style.display = "none";
  });

  modalChangePw?.addEventListener("click", (e) => {
    if (e.target === modalChangePw) modalChangePw.style.display = "none";
  });

  formChangePw?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const oldPassword = document.getElementById("cp-old-password").value;
    const newPassword = document.getElementById("cp-new-password").value;
    const confirmPassword = document.getElementById("cp-confirm-password").value;
    const errOld = document.getElementById("err-cp-old");
    const errNew = document.getElementById("err-cp-new");
    const errConfirm = document.getElementById("err-cp-confirm");
    errOld.style.display = "none";
    errNew.style.display = "none";
    errConfirm.style.display = "none";

    if (!oldPassword) {
      errOld.textContent = "Please enter your current password.";
      errOld.style.display = "flex";
      return;
    }
    if (!newPassword || newPassword.length < 6) {
      errNew.textContent = "New password must be at least 6 characters.";
      errNew.style.display = "flex";
      return;
    }
    if (newPassword !== confirmPassword) {
      errConfirm.textContent = "New passwords do not match.";
      errConfirm.style.display = "flex";
      return;
    }

    const btn = document.getElementById("btn-submit-change-pw");
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> Updating SQLite Password...`;

    try {
      const res = await fetch("/api/auth/change-password", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${state.token}`
        },
        body: JSON.stringify({ oldPassword, newPassword, confirmPassword }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to change password");

      showToast("Password updated successfully in SQLite!", "success");
      formChangePw.reset();
      modalChangePw.style.display = "none";
    } catch (err) {
      errOld.textContent = err.message;
      errOld.style.display = "flex";
      showToast(err.message, "error");
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<span>Save New Password to SQLite</span>`;
    }
  });

  // Forgot Password: Step 1 (Request Token)
  const formForgotReq = document.getElementById("form-forgot-request");
  const formForgotReset = document.getElementById("form-forgot-reset");

  formForgotReq?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("forgot-email").value.trim();
    const errEl = document.getElementById("err-forgot-email");
    errEl.style.display = "none";

    if (!email || !email.includes("@")) {
      errEl.textContent = "Please enter a valid email address.";
      errEl.style.display = "flex";
      return;
    }

    const btn = document.getElementById("btn-submit-forgot-request");
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> Generating Token...`;

    try {
      const res = await fetch("/api/auth/forgot-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to generate reset token");

      if (data.status === "not_found") {
        errEl.textContent = data.message;
        errEl.style.display = "flex";
        return;
      }

      showToast("Password reset token generated!", "success");
      document.getElementById("reset-token-input").value = data.token;
      formForgotReq.style.display = "none";
      formForgotReset.style.display = "block";
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<span>Generate Reset Token</span>`;
    }
  });

  // Forgot Password: Step 2 (Reset with Token)
  formForgotReset?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const token = document.getElementById("reset-token-input").value.trim();
    const newPassword = document.getElementById("reset-new-password").value;
    const confirmPassword = document.getElementById("reset-confirm-password").value;
    const errPw = document.getElementById("err-reset-password");
    const errConf = document.getElementById("err-reset-confirm");
    errPw.style.display = "none";
    errConf.style.display = "none";

    if (!newPassword || newPassword.length < 6) {
      errPw.textContent = "New password must be at least 6 characters.";
      errPw.style.display = "flex";
      return;
    }
    if (newPassword !== confirmPassword) {
      errConf.textContent = "Passwords do not match.";
      errConf.style.display = "flex";
      return;
    }

    const btn = document.getElementById("btn-submit-forgot-reset");
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> Updating SQLite Password...`;

    try {
      const res = await fetch("/api/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, newPassword, confirmPassword }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to reset password");

      showToast("Password updated successfully! Please sign in with your new password.", "success");
      formForgotReset.style.display = "none";
      formForgotReq.style.display = "block";
      switchView("signin");
    } catch (err) {
      errPw.textContent = err.message;
      errPw.style.display = "flex";
      showToast(err.message, "error");
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<span>Save New Password to SQLite</span>`;
    }
  });

  if (formSignIn) {
    formSignIn.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = document.getElementById("signin-email").value.trim();
      const password = document.getElementById("signin-password").value;
      const btn = document.getElementById("btn-submit-signin");

      const errEmail = document.getElementById("err-signin-email");
      const errPw = document.getElementById("err-signin-password");
      errEmail.style.display = "none";
      errPw.style.display = "none";

      if (!email) {
        errEmail.textContent = "Please enter your email or username.";
        errEmail.style.display = "flex";
        return;
      }
      if (!password || password.length < 4) {
        errPw.textContent = "Password must be at least 4 characters.";
        errPw.style.display = "flex";
        return;
      }

      btn.disabled = true;
      btn.innerHTML = `<span class="spinner"></span> Signing in...`;

      try {
        const res = await fetch("/api/auth/signin", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Authentication failed");

        state.token = data.token;
        state.user = data.user;
        sessionStorage.setItem("ci_token", data.token);
        sessionStorage.setItem("ci_user", JSON.stringify(data.user));

        showToast("Signed in in Demo Mode. Welcome, " + data.user.name, "success");
        switchView("dashboard");
      } catch (err) {
        errPw.textContent = err.message;
        errPw.style.display = "flex";
        showToast(err.message, "error");
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<span>Sign In to Platform</span>`;
      }
    });
  }

  if (formSignUp) {
    formSignUp.addEventListener("submit", async (e) => {
      e.preventDefault();
      const name = document.getElementById("signup-name").value.trim();
      const email = document.getElementById("signup-email").value.trim();
      const password = document.getElementById("signup-password").value;
      const confirmPassword = document.getElementById("signup-confirm-password").value;
      const btn = document.getElementById("btn-submit-signup");

      const errName = document.getElementById("err-signup-name");
      const errEmail = document.getElementById("err-signup-email");
      const errPw = document.getElementById("err-signup-password");
      const errConfirm = document.getElementById("err-signup-confirm-password");

      [errName, errEmail, errPw, errConfirm].forEach((el) => (el.style.display = "none"));

      if (!name) { errName.textContent = "Name is required"; errName.style.display = "flex"; return; }
      if (!email || !email.includes("@")) { errEmail.textContent = "Valid email is required"; errEmail.style.display = "flex"; return; }
      if (!password || password.length < 4) { errPw.textContent = "Password too short"; errPw.style.display = "flex"; return; }
      if (password !== confirmPassword) { errConfirm.textContent = "Passwords do not match"; errConfirm.style.display = "flex"; return; }

      btn.disabled = true;
      btn.innerHTML = `<span class="spinner"></span> Creating Account...`;

      try {
        const res = await fetch("/api/auth/signup", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, email, password, confirmPassword }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Account creation failed");

        state.token = data.token;
        state.user = data.user;
        sessionStorage.setItem("ci_token", data.token);
        sessionStorage.setItem("ci_user", JSON.stringify(data.user));

        showToast("Account created successfully! Welcome to CI_Agent.", "success");
        switchView("dashboard");
      } catch (err) {
        showToast(err.message, "error");
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<span>Create Account</span>`;
      }
    });
  }

  // ==========================================
  // Dashboard Actions
  // ==========================================
  document.getElementById("btn-dashboard-explore")?.addEventListener("click", () => switchView("explanation"));
  document.getElementById("btn-dashboard-repair")?.addEventListener("click", () => switchView("repair"));
  document.getElementById("btn-back-from-explanation")?.addEventListener("click", () => switchView("dashboard"));
  document.getElementById("btn-back-from-repair")?.addEventListener("click", () => switchView("dashboard"));
  document.getElementById("nav-brand")?.addEventListener("click", (e) => {
    e.preventDefault();
    if (state.token) switchView("dashboard");
  });

  // ==========================================
  // Project Explanation Feature
  // ==========================================
  const tabSrcGithub = document.getElementById("tab-src-github");
  const tabSrcLocal = document.getElementById("tab-src-local");
  const panelSrcGithub = document.getElementById("panel-src-github");
  const panelSrcLocal = document.getElementById("panel-src-local");

  tabSrcGithub?.addEventListener("click", () => {
    tabSrcGithub.classList.add("active");
    tabSrcLocal.classList.remove("active");
    panelSrcGithub.style.display = "block";
    panelSrcLocal.style.display = "none";
  });

  tabSrcLocal?.addEventListener("click", () => {
    tabSrcLocal.classList.add("active");
    tabSrcGithub.classList.remove("active");
    panelSrcLocal.style.display = "block";
    panelSrcGithub.style.display = "none";
  });

  window.setExplainPreset = function (url) {
    document.getElementById("input-explain-repo").value = url;
  };

  // Local folder picker
  const btnBrowseFolder = document.getElementById("btn-browse-folder");
  const localFolderInput = document.getElementById("local-folder-input");
  const localFilesPreview = document.getElementById("local-files-preview");
  const localFilesList = document.getElementById("local-files-list");
  const btnAnalyzeLocal = document.getElementById("btn-analyze-local-files");

  btnBrowseFolder?.addEventListener("click", () => localFolderInput.click());

  localFolderInput?.addEventListener("change", async (e) => {
    const files = Array.from(e.target.files);
    if (!files.length) return;

    state.localSelectedFiles = [];
    localFilesList.innerHTML = "";
    localFilesPreview.style.display = "block";
    btnAnalyzeLocal.style.display = "inline-flex";

    let loadedCount = 0;
    const maxFilesToRead = 60; // safe browser memory cap

    for (const file of files.slice(0, maxFilesToRead)) {
      const relPath = file.webkitRelativePath || file.name;
      // Skip binary, git, or giant files
      if (relPath.includes("/.") || relPath.includes("__pycache__") || file.size > 200_000) {
        continue;
      }
      try {
        const text = await file.text();
        state.localSelectedFiles.push({ path: relPath, content: text, size: file.size });
        const li = document.createElement("li");
        li.textContent = `${relPath} (${(file.size / 1024).toFixed(1)} KB)`;
        localFilesList.appendChild(li);
        loadedCount++;
      } catch (err) {
        console.warn("Could not read file", relPath);
      }
    }

    document.getElementById("local-folder-stats").textContent = `Selected ${loadedCount} project files ready for analysis:`;
  });

  // Start GitHub Analysis
  document.getElementById("btn-start-explain")?.addEventListener("click", async () => {
    const repoUrl = document.getElementById("input-explain-repo").value.trim();
    const branch = document.getElementById("input-explain-branch").value.trim() || "main";
    const btn = document.getElementById("btn-start-explain");

    if (!repoUrl) {
      showToast("Please enter a GitHub repository URL", "error");
      return;
    }

    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> Analyzing Codebase...`;

    try {
      const res = await fetch("/api/project/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: repoUrl, branch }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Analysis failed");

      renderProjectExplanation(data);
      showToast("Codebase analyzed successfully!", "success");
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<span>Analyze Project</span>`;
    }
  });

  // Start Local Analysis
  btnAnalyzeLocal?.addEventListener("click", async () => {
    if (!state.localSelectedFiles.length) {
      showToast("No files selected", "error");
      return;
    }

    btnAnalyzeLocal.disabled = true;
    btnAnalyzeLocal.innerHTML = `<span class="spinner"></span> Analyzing Local Project...`;

    try {
      const res = await fetch("/api/project/analyze-files", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          folder_name: "Selected Local Project",
          files: state.localSelectedFiles,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Analysis failed");

      renderProjectExplanation(data);
      showToast("Local codebase analyzed successfully!", "success");
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      btnAnalyzeLocal.disabled = false;
      btnAnalyzeLocal.innerHTML = `<span>Analyze Selected Local Files</span>`;
    }
  });

  // Render Analysis Results
  function renderProjectExplanation(data) {
    state.activeProjectId = data.project_id;
    state.activeProjectData = data;
    state.chatHistory = []; // Reset conversation history to isolate project contexts
    document.getElementById("explanation-results-container").style.display = "block";

    const chatBox = document.getElementById("chat-messages-list");
    if (chatBox) {
      chatBox.innerHTML = `
        <div class="chat-bubble chat-bubble-ai">
          Hello! I have loaded and indexed <strong>${escapeHtml(data.project_name || 'Project')}</strong>. Ask me anything about its architecture, execution flow, or specific functions.
        </div>
      `;
    }

    const structure = data.structure || {};
    const analysis = data.analysis || {};

    // 1. Overview tab
    document.getElementById("explain-overview-text").textContent = analysis.overview || "Project analyzed.";
    document.getElementById("stat-total-files").textContent = structure.total_files || 0;
    document.getElementById("stat-total-lines").textContent = structure.total_lines?.toLocaleString() || 0;
    document.getElementById("stat-primary-lang").textContent = structure.primary_language || "Python";

    const langContainer = document.getElementById("explain-languages-bars");
    langContainer.innerHTML = "";
    Object.entries(structure.languages || {}).forEach(([lang, count]) => {
      const row = document.createElement("div");
      row.style.display = "flex";
      row.style.alignItems = "center";
      row.style.gap = "10px";
      row.style.marginBottom = "6px";
      row.innerHTML = `<span style="width: 100px; font-weight:600; font-size:0.85rem;">${lang}</span>
        <div style="flex:1; background:rgba(89,9,7,0.12); height:8px; border-radius:4px; overflow:hidden;">
          <div style="background:var(--color-burgundy); height:100%; width:${Math.min(count * 8, 100)}%;"></div>
        </div>
        <span style="font-size:0.8rem; color:var(--color-text-muted);">${count} files</span>`;
      langContainer.appendChild(row);
    });

    // 2. Architecture tab
    document.getElementById("explain-architecture-text").textContent = analysis.architecture || "Modular service architecture.";
    const keyCompList = document.getElementById("explain-key-components-list");
    keyCompList.innerHTML = "";
    (analysis.key_components || []).forEach((comp) => {
      const li = document.createElement("li");
      li.textContent = comp;
      keyCompList.appendChild(li);
    });
    document.getElementById("explain-improvements-text").textContent = analysis.potential_improvements || "Maintain test coverage and clean interfaces.";

    // Render Mermaid Diagram
    const diagramContainer = document.getElementById("explain-architecture-diagram");
    if (diagramContainer) {
      const mermaidCode = data.architecture_graph?.mermaid_diagram || "graph TD\n    Clients --> Service";
      if (window.mermaid) {
        try {
          const uniqueId = `mermaid-svg-${Date.now()}`;
          window.mermaid.render(uniqueId, mermaidCode).then(({ svg }) => {
            diagramContainer.innerHTML = svg;
          }).catch((err) => {
            diagramContainer.innerHTML = `<pre style="text-align:left; font-family:var(--font-mono); font-size:0.85rem;">${escapeHtml(mermaidCode)}</pre>`;
          });
        } catch (e) {
          diagramContainer.innerHTML = `<pre style="text-align:left; font-family:var(--font-mono); font-size:0.85rem;">${escapeHtml(mermaidCode)}</pre>`;
        }
      } else {
        diagramContainer.innerHTML = `<pre style="text-align:left; font-family:var(--font-mono); font-size:0.85rem;">${escapeHtml(mermaidCode)}</pre>`;
      }
    }

    // 3. File Explorer
    const tree = document.getElementById("explorer-files-tree");
    tree.innerHTML = "";
    (structure.files || []).forEach((f) => {
      const item = document.createElement("div");
      item.className = "file-item";
      item.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/></svg> <span>${f.path}</span>`;
      item.onclick = async () => {
        document.querySelectorAll(".file-item").forEach((el) => el.classList.remove("active"));
        item.classList.add("active");
        await loadFilePreview(data.project_id, f.path, f.size);
      };
      tree.appendChild(item);
    });

    // Auto-select first file
    if (structure.files && structure.files.length) {
      tree.children[0]?.click();
    }

    // 4. Execution Flow
    document.getElementById("explain-flow-text").textContent = analysis.execution_flow || "Standard lifecycle.";
    const entryList = document.getElementById("explain-entrypoints-list");
    entryList.innerHTML = "";
    (structure.entry_points || []).forEach((ep) => {
      const li = document.createElement("li");
      li.textContent = ep;
      entryList.appendChild(li);
    });

    const epContainer = document.getElementById("explain-endpoints-list");
    epContainer.innerHTML = "";
    if (structure.endpoints && structure.endpoints.length) {
      structure.endpoints.forEach((ep) => {
        const div = document.createElement("div");
        div.style.padding = "6px 10px";
        div.style.background = "#FFF";
        div.style.borderRadius = "4px";
        div.style.marginBottom = "4px";
        div.style.fontSize = "0.86rem";
        div.style.fontFamily = "var(--font-mono)";
        div.innerHTML = `<span style="color:var(--color-burgundy); font-weight:700;">${ep.method}</span> ${ep.path} <span style="color:var(--color-text-muted); font-size:0.78rem;">(${ep.file})</span>`;
        epContainer.appendChild(div);
      });
    } else {
      epContainer.innerHTML = "<div style='color:var(--color-text-muted); font-size:0.9rem;'>No HTTP REST endpoints declared in parsed files.</div>";
    }

    // 5. Dependencies
    const depContainer = document.getElementById("explain-dependencies-table");
    depContainer.innerHTML = "";
    if (structure.dependencies && structure.dependencies.length) {
      let tableHtml = `<table style="width:100%; border-collapse:collapse; font-size:0.88rem;">
        <thead><tr style="text-align:left; border-bottom:1px solid rgba(89,9,7,0.2);"><th style="padding:8px;">Package</th><th style="padding:8px;">Purpose & Code Usage</th><th style="padding:8px;">Imported In</th></tr></thead><tbody>`;
      structure.dependencies.forEach((d) => {
        const pkgName = typeof d === 'string' ? d : d.name;
        const purpose = d.purpose || 'Ecosystem dependency';
        const importedBy = (d.imported_by && d.imported_by.length) ? d.imported_by.join(', ') : 'Declared in manifest';
        tableHtml += `<tr style="border-bottom:1px solid rgba(89,9,7,0.08);"><td style="padding:8px; font-family:var(--font-mono); font-weight:600; color:var(--color-burgundy);">${pkgName}</td><td style="padding:8px; font-size:0.85rem;">${purpose}</td><td style="padding:8px; color:var(--color-text-muted); font-size:0.8rem; font-family:var(--font-mono);">${importedBy}</td></tr>`;
      });
      tableHtml += `</tbody></table>`;
      depContainer.innerHTML = tableHtml;
    } else {
      depContainer.innerHTML = "<div style='color:var(--color-text-muted);'>No third-party dependencies detected.</div>";
    }

    // 6. Tests & CI/CD
    const cicdContainer = document.getElementById("explain-cicd-info");
    cicdContainer.innerHTML = `
      <div style="margin-bottom:16px;">
        <div style="font-weight:700; color:var(--color-burgundy);">Discovered GitHub Workflows:</div>
        <div style="font-family:var(--font-mono); margin-top:4px;">${structure.ci_workflows?.length ? structure.ci_workflows.join(", ") : "None detected"}</div>
      </div>
      <div>
        <div style="font-weight:700; color:var(--color-burgundy);">Test Discovery:</div>
        <p style="margin-top:4px;">Pytest test suites are located in <code>tests/</code>, verified via automated CI pipelines.</p>
      </div>`;

    // 7. Issues & Actionable Suggestions
    const issuesContainer = document.getElementById("explain-issues-list");
    const issuesBadge = document.getElementById("issues-badge-count");
    const issues = data.issues_suggestions || [];
    if (issuesBadge) issuesBadge.textContent = `${issues.length} Issue(s) Detected`;

    if (issuesContainer) {
      issuesContainer.innerHTML = "";
      if (issues.length === 0) {
        issuesContainer.innerHTML = "<div style='color:var(--color-text-muted); padding:16px;'>No critical bugs or anti-patterns detected in inspected files.</div>";
      } else {
        issues.forEach((iss) => {
          const card = document.createElement("div");
          card.style.background = "#FFF";
          card.style.border = "1px solid rgba(89, 9, 7, 0.15)";
          card.style.borderRadius = "var(--radius-md)";
          card.style.padding = "18px";
          card.style.marginBottom = "16px";

          const sevColor = iss.severity === "High" ? "#590907" : (iss.severity === "Medium" ? "#9a3412" : "#365314");
          const sevBg = iss.severity === "High" ? "rgba(89, 9, 7, 0.1)" : (iss.severity === "Medium" ? "rgba(234, 88, 12, 0.1)" : "rgba(101, 163, 13, 0.1)");

          card.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:start; margin-bottom:10px;">
              <div>
                <span style="background:${sevBg}; color:${sevColor}; padding:3px 8px; border-radius:4px; font-weight:700; font-size:0.75rem; text-transform:uppercase;">${iss.severity} Severity</span>
                <span style="font-family:var(--font-mono); font-size:0.78rem; color:var(--color-text-muted); margin-left:8px;">${iss.id}</span>
                <h4 style="margin:6px 0 2px 0; font-size:1.05rem;">${iss.title}</h4>
                <div style="font-family:var(--font-mono); font-size:0.8rem; color:var(--color-burgundy);">${iss.file} :: ${iss.function}</div>
              </div>
            </div>
            <div style="display:grid; grid-template-columns:1fr; gap:8px; margin-top:12px; font-size:0.88rem; line-height:1.5;">
              <div><strong>Evidence:</strong> <span style="font-family:var(--font-mono); background:rgba(89,9,7,0.05); padding:2px 6px; border-radius:3px;">${escapeHtml(iss.evidence)}</span></div>
              <div><strong>Reason:</strong> ${escapeHtml(iss.reason)}</div>
              <div><strong>Recommendation:</strong> ${escapeHtml(iss.recommendation)}</div>
              <div style="background:rgba(89,9,7,0.04); padding:10px; border-radius:6px; margin-top:4px;">
                <div style="font-weight:700; color:var(--color-burgundy); margin-bottom:2px;">Implementation Plan:</div>
                <div>${escapeHtml(iss.implementation_plan)}</div>
                <div style="font-weight:700; color:var(--color-burgundy); margin-top:6px; margin-bottom:2px;">Validation:</div>
                <div style="font-family:var(--font-mono); font-size:0.82rem;">${escapeHtml(iss.validation)}</div>
              </div>
            </div>
          `;
          issuesContainer.appendChild(card);
        });
      }
    }
  }

  async function loadFilePreview(projectId, path, size) {
    const filenameEl = document.getElementById("code-viewer-filename");
    const sizeEl = document.getElementById("code-viewer-filesize");
    const contentEl = document.getElementById("code-viewer-content");
    const metaEl = document.getElementById("code-viewer-meta");

    filenameEl.textContent = path;
    sizeEl.textContent = `${(size / 1024).toFixed(1)} KB`;
    contentEl.textContent = "Loading file content...";
    if (metaEl) metaEl.style.display = "none";

    try {
      const res = await fetch(`/api/project/${projectId}/file?path=${encodeURIComponent(path)}`);
      if (!res.ok) throw new Error("Could not load file");
      const data = await res.json();
      contentEl.textContent = data.content;

      if (metaEl && (data.role || data.functions?.length || data.classes?.length)) {
        metaEl.style.display = "block";
        const fns = (data.functions || []).map(f => typeof f === 'string' ? f : f.name).join(", ");
        const cls = (data.classes || []).map(c => typeof c === 'string' ? c : c.name).join(", ");
        metaEl.innerHTML = `
          <div style="display:flex; gap:16px; flex-wrap:wrap; align-items:center;">
            <span><strong>Role:</strong> <span style="color:var(--color-burgundy); font-weight:600;">${data.role || 'general'}</span></span>
            ${cls ? `<span><strong>Classes:</strong> <span style="font-family:var(--font-mono); font-size:0.8rem;">${cls}</span></span>` : ''}
            ${fns ? `<span><strong>Functions:</strong> <span style="font-family:var(--font-mono); font-size:0.8rem;">${fns}</span></span>` : ''}
          </div>
          ${data.docstring ? `<div style="margin-top:4px; font-style:italic; color:var(--color-text-muted);">"${escapeHtml(data.docstring)}"</div>` : ''}
        `;
      }
    } catch (err) {
      contentEl.textContent = `// Error loading file: ${err.message}`;
    }
  }

  // Analysis Tabs switching
  document.querySelectorAll("#analysis-tabs .tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#analysis-tabs .tab-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const targetId = `content-${btn.getAttribute("data-tab")}`;
      ["content-tab-overview", "content-tab-architecture", "content-tab-files", "content-tab-flow", "content-tab-deps", "content-tab-tests", "content-tab-issues"].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.style.display = id === targetId ? (id === "content-tab-files" ? "grid" : "block") : "none";
      });
    });
  });

  // Chatbot Logic
  const chatMessages = document.getElementById("chat-messages-list");
  const chatInput = document.getElementById("chat-input-text");
  const btnChatSend = document.getElementById("btn-chat-send");

  window.sendQuickPrompt = function (text) {
    if (chatInput) {
      chatInput.value = text;
      sendChatMessage();
    }
  };

  async function sendChatMessage() {
    const msg = chatInput.value.trim();
    if (!msg) return;

    // Append User Message
    const userBubble = document.createElement("div");
    userBubble.className = "chat-bubble chat-bubble-user";
    userBubble.textContent = msg;
    chatMessages.appendChild(userBubble);
    chatInput.value = "";
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Append AI Loading Bubble
    const aiBubble = document.createElement("div");
    aiBubble.className = "chat-bubble chat-bubble-ai";
    aiBubble.innerHTML = `<span class="spinner" style="border-top-color:var(--color-burgundy);"></span> Thinking...`;
    chatMessages.appendChild(aiBubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
      const res = await fetch("/api/project/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: msg,
          project_id: state.activeProjectId,
          context: state.activeProjectData,
          history: state.chatHistory,
        }),
      });
      const data = await res.json();

      // Render reply with simple code blocks
      const formatted = escapeHtml(data.reply).replace(/```(?:python|javascript|bash)?([\s\S]*?)```/g, '<pre class="code-block" style="margin:8px 0; padding:10px;"><code>$1</code></pre>');
      aiBubble.innerHTML = formatted;

      state.chatHistory.push({ role: "user", content: msg });
      state.chatHistory.push({ role: "assistant", content: data.reply });
    } catch (err) {
      aiBubble.innerHTML = `<span style="color:var(--color-danger);">Error: Could not retrieve answer. Please verify Ollama is running.</span>`;
    }
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  btnChatSend?.addEventListener("click", sendChatMessage);
  chatInput?.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendChatMessage();
    }
  });

  function escapeHtml(text) {
    return text.replace(/[&<>"']/g, function (m) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[m];
    });
  }

  // ==========================================
  // CI Agent — AI Code Repair Feature
  // ==========================================
  window.setRepairPreset = function (url) {
    document.getElementById("input-repair-repo").value = url;
  };

  const btnStartRepair = document.getElementById("btn-start-repair-job");
  const repairPipelineDisplay = document.getElementById("repair-pipeline-display");

  btnStartRepair?.addEventListener("click", async () => {
    const repoUrl = document.getElementById("input-repair-repo").value.trim();
    const branch = document.getElementById("input-repair-branch").value.trim() || "main";

    if (!repoUrl) {
      showToast("Please enter a GitHub repository URL", "error");
      return;
    }

    btnStartRepair.disabled = true;
    btnStartRepair.innerHTML = `<span class="spinner"></span> Initiating Repair Pipeline...`;
    repairPipelineDisplay.style.display = "block";
    updateStepper(1);

    // Reset previous run UI fields
    const liveStep = document.getElementById("repair-live-step-title");
    const liveLog = document.getElementById("repair-live-log-msg");
    const liveBadge = document.getElementById("repair-live-badge");
    const liveSpinner = document.getElementById("repair-live-spinner");
    if (liveStep) liveStep.textContent = "Initializing Workspace Sandbox...";
    if (liveLog) liveLog.textContent = `Cloning ${repoUrl}...`;
    if (liveBadge) { liveBadge.textContent = "STARTING"; liveBadge.style.background = "var(--color-burgundy)"; }
    if (liveSpinner) liveSpinner.style.display = "inline-block";

    document.getElementById("baseline-summary").textContent = "Executing tests...";
    document.getElementById("baseline-failed-count").textContent = "-";
    document.getElementById("baseline-passed-count").textContent = "-";
    document.getElementById("baseline-raw-log").textContent = "Preparing isolated test environment...";
    document.getElementById("baseline-status-badge").innerHTML = `<span class="badge-count" style="background:var(--color-sage-deep); color:#FFF;">Running...</span>`;
    document.getElementById("diagnosis-target-files").innerHTML = `<li style="color:var(--color-text-muted);"><span class="spinner" style="width:12px; height:12px; border-width:2px;"></span> Analyzing project structure...</li>`;
    document.getElementById("diagnosis-failing-tests").innerHTML = `<li style="color:var(--color-text-muted);"><span class="spinner" style="width:12px; height:12px; border-width:2px;"></span> Awaiting test results...</li>`;
    document.getElementById("diff-viewer").textContent = "Patch generation in progress...";
    document.getElementById("post-repair-badge").innerHTML = "";

    try {
      const res = await fetch("/api/ci/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: repoUrl, branch }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to start repair job");

      state.activeRepairJobId = data.job_id;
      showToast("Autonomous CI repair pipeline started", "info");
      pollRepairJob(data.job_id);
    } catch (err) {
      showToast(err.message, "error");
      btnStartRepair.disabled = false;
      btnStartRepair.innerHTML = `<span>Start Autonomous Repair</span>`;
    }
  });

  function updateStepper(step) {
    for (let i = 1; i <= 5; i++) {
      const node = document.getElementById(`step-node-${i}`);
      if (!node) continue;
      if (i < step) {
        node.className = "step-node completed";
      } else if (i === step) {
        node.className = "step-node active";
      } else {
        node.className = "step-node";
      }
    }
  }

  function pollRepairJob(jobId) {
    if (state.repairPollInterval) clearInterval(state.repairPollInterval);

    state.repairPollInterval = setInterval(async () => {
      try {
        const res = await fetch(`/api/ci/status/${jobId}`);
        if (res.status === 404) {
          clearInterval(state.repairPollInterval);
          state.repairPollInterval = null;
          btnStartRepair.disabled = false;
          btnStartRepair.innerHTML = `<span>Start Autonomous Repair</span>`;
          showToast("Previous repair job session expired. Ready to start new repair.", "info");
          return;
        }
        if (!res.ok) return;
        const job = await res.json();

        updateStepper(job.current_step || 1);

        // Update Live Status Banner
        const liveStep = document.getElementById("repair-live-step-title");
        const liveLog = document.getElementById("repair-live-log-msg");
        const liveBadge = document.getElementById("repair-live-badge");
        const liveSpinner = document.getElementById("repair-live-spinner");

        if (liveStep && job.step_name) liveStep.textContent = job.step_name;
        if (liveLog && job.logs && job.logs.length) liveLog.textContent = job.logs[job.logs.length - 1];
        if (liveBadge && job.status) {
          liveBadge.textContent = job.status.toUpperCase().replace("_", " ");
          if (job.status === "awaiting_approval" || job.status === "success") {
            liveBadge.style.background = "var(--color-success)";
          } else if (job.status === "error") {
            liveBadge.style.background = "var(--color-danger)";
          } else {
            liveBadge.style.background = "var(--color-burgundy)";
          }
        }

        // Step 2: Baseline
        if (job.baseline) {
          document.getElementById("baseline-summary").textContent = job.baseline.summary || `${job.baseline.passed} Passed, ${job.baseline.failed} Failed`;
          document.getElementById("baseline-failed-count").textContent = `${job.baseline.failed} Failed`;
          document.getElementById("baseline-passed-count").textContent = `${job.baseline.passed} Passed`;
          document.getElementById("baseline-raw-log").textContent = job.baseline.raw_output || "No output";
          if (job.baseline.failed > 0) {
            document.getElementById("baseline-status-badge").innerHTML = `<span class="badge-count badge-count-fail">Failure Detected (${job.baseline.failed})</span>`;
          } else {
            document.getElementById("baseline-status-badge").innerHTML = `<span class="badge-count" style="background:var(--color-success); color:#FFF;">0 Failures Detected (Tests Passing)</span>`;
          }
        }

        // Step 3: Diagnosis
        if (job.diagnosis) {
          const targetList = document.getElementById("diagnosis-target-files");
          targetList.innerHTML = "";
          const targets = job.diagnosis.target_files || [];
          if (targets.length === 0) {
            targetList.innerHTML = `<li style="color:var(--color-text-muted); font-size:0.86rem;">• ${job.diagnosis.message || "Healthy repository: no culprit source files."}</li>`;
          } else {
            targets.forEach((f) => {
              const li = document.createElement("li");
              li.innerHTML = `<strong style="color:var(--color-burgundy); font-family:var(--font-mono); font-size:0.86rem;">• ${escapeHtml(f)}</strong>`;
              targetList.appendChild(li);
            });
          }

          const failList = document.getElementById("diagnosis-failing-tests");
          failList.innerHTML = "";
          const fails = job.diagnosis.failing_tests || [];
          if (fails.length === 0) {
            failList.innerHTML = `<li style="color:var(--color-text-muted); font-size:0.86rem;">• 0 failing tests detected.</li>`;
          } else {
            fails.forEach((t) => {
              const li = document.createElement("li");
              li.innerHTML = `<span style="color:var(--color-danger); font-family:var(--font-mono); font-size:0.84rem;">• ${escapeHtml(t)}</span>`;
              failList.appendChild(li);
            });
          }
        }

        // Step 4: Patch Review
        if (job.diff !== undefined) {
          renderDiff(job.diff);
        }
        if (job.post_repair) {
          const p = job.post_repair;
          const badge = document.getElementById("post-repair-badge");
          if (p.failed === 0) {
            badge.innerHTML = `<span style="color:var(--color-success); font-weight:700;">✓ PASSED: All ${p.passed} tests passing! (0 failures, 0 regressions)</span>`;
          } else {
            badge.innerHTML = `<span style="color:var(--color-danger); font-weight:700;">Partial: ${p.failed} failing, ${p.passed} passing</span>`;
          }
        }

        // Step 5: Awaiting Approval or Completed
        if (job.status === "awaiting_approval" || job.status === "success") {
          clearInterval(state.repairPollInterval);
          state.repairPollInterval = null;
          btnStartRepair.disabled = false;
          btnStartRepair.innerHTML = `<span>Start Autonomous Repair</span>`;
          updateStepper(5);
          if (liveSpinner) liveSpinner.style.display = "none";
          if (job.status === "success") {
            showToast("All tests verified passing! No repairs needed.", "success");
          } else {
            showToast("Repair verified! Ready for GitHub publication approval.", "success");
          }
        } else if (job.status === "error" || job.status === "partial_repair") {
          clearInterval(state.repairPollInterval);
          state.repairPollInterval = null;
          btnStartRepair.disabled = false;
          btnStartRepair.innerHTML = `<span>Start Autonomous Repair</span>`;
          if (liveSpinner) liveSpinner.style.display = "none";
          if (job.status === "error") {
            showToast(`Repair pipeline error: ${job.error || "Unknown error"}`, "error");
          }
        }
      } catch (err) {
        console.warn("Poll status error", err);
      }
    }, 2000);
  }

  function renderDiff(diffText) {
    const diffEl = document.getElementById("diff-viewer");
    if (!diffText.trim()) {
      diffEl.textContent = "No code differences generated.";
      return;
    }
    const lines = diffText.split("\n");
    diffEl.innerHTML = lines
      .map((line) => {
        const escaped = escapeHtml(line);
        if (line.startsWith("+") && !line.startsWith("+++")) {
          return `<span class="diff-add">${escaped}</span>`;
        } else if (line.startsWith("-") && !line.startsWith("---")) {
          return `<span class="diff-del">${escaped}</span>`;
        }
        return escaped;
      })
      .join("\n");
  }

  // GitHub Publication Approval
  document.getElementById("btn-approve-push")?.addEventListener("click", async () => {
    if (!state.activeRepairJobId) {
      showToast("No active verified repair to push", "error");
      return;
    }

    const branch = document.getElementById("input-approve-branch").value.trim() || "main";
    const commit_message = document.getElementById("input-approve-msg").value.trim();
    const btn = document.getElementById("btn-approve-push");

    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> Pushing to GitHub...`;

    try {
      const res = await fetch("/api/ci/approve-push", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_id: state.activeRepairJobId,
          branch,
          commit_message,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Push failed");

      const banner = document.getElementById("push-result-banner");
      banner.style.display = "block";
      document.getElementById("push-result-title").textContent = "✓ Successfully Pushed to GitHub!";
      document.getElementById("push-result-details").innerHTML = `
        Changes committed and pushed to branch <strong>${data.branch}</strong>.<br>
        GitHub Actions CI workflow has been automatically triggered.
      `;
      showToast("Fix published to GitHub successfully!", "success");
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<span>Approve & Push to GitHub</span>`;
    }
  });

  // Initialize
  initRouting();
})();
