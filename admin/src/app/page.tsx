"use client";

import React, { useState, useEffect, useMemo } from "react";
import {
  Sparkles,
  Database,
  LayoutDashboard,
  Brain,
  FileText,
  KeyRound,
  Trash2,
  Send,
  RefreshCw,
  Save,
  CheckCircle2,
  AlertCircle,
  Copy,
  ExternalLink,
  Search,
  Plus,
  Sliders,
  Check,
  Globe,
  User,
  ShieldCheck,
  Bot,
  RotateCcw,
  Edit2,
  Lock,
  LogOut,
  Menu,
  X,
  Flame,
  Info
} from "lucide-react";
import { adminApi, IdentityConfig, getAdminToken, setAdminToken } from "../lib/api";
import { isSessionUnlocked, unlockSession, lockSession, computeSha256, getExpectedHash } from "../lib/auth";

type Tab = "identity" | "overview" | "memories" | "notes_alarms" | "keypool";

/** Bald eagle mark from Mercy: white head, hooked gold beak, dark brown radial background */
function EagleMark({ size = 36 }: { size?: number }) {
  const id = React.useId();
  return (
    <svg aria-hidden viewBox="0 0 64 64" width={size} height={size} className="shrink-0 rounded-full ring-1 ring-zinc-700/80 shadow-md">
      <defs>
        <radialGradient id={`${id}bg`} cx="35%" cy="25%" r="85%">
          <stop offset="0" stopColor="#6b4a33" />
          <stop offset="1" stopColor="#2b1d14" />
        </radialGradient>
        <clipPath id={`${id}clip`}>
          <circle cx="32" cy="32" r="32" />
        </clipPath>
      </defs>
      <circle cx="32" cy="32" r="32" fill={`url(#${id}bg)`} />
      <g clipPath={`url(#${id}clip)`}>
        <path d="M8 66 C7 50 9 36 17 26 C24 17 35 13 44 16 C49 18 52 21 53 25 L49 32 C43 34 39 38 37 44 C35 51 35 58 37 66 Z" fill="#f3efe6" />
        <path d="M16 66 L19 56 L22 64 L26 54 L29 64 L32 55 L34 66 Z" fill="#e2dccf" />
        <path d="M47 20 C55 19 61 24 61 31 C61 36 58 39 55 38 C56 35 55 32 52 32 L45 33 C46 28 46 24 47 20 Z" fill="#f5b301" />
        <path d="M45 33 L52 32 C54 32 55 33 55 35 C51 35 48 35 45 33 Z" fill="#c98a00" />
        <circle cx="41" cy="24" r="3" fill="#f5b301" />
        <circle cx="41.6" cy="24" r="1.6" fill="#111" />
        <path d="M34 20.5 C38 19.5 43 19.5 47 21.5 L46 22.6 C42 21.4 38 21.4 34.6 22.4 Z" fill="#2b1d14" />
      </g>
    </svg>
  );
}

function computeLivePrompt(cfg: IdentityConfig): string {
  const name = cfg.its_name || "Athina";
  const myName = cfg.my_name || "Md Ratul Hossen";
  const callMeRaw = cfg.call_me || "Ratul";
  const callMeParts = callMeRaw.split(",").map((s) => s.trim()).filter(Boolean);

  const casualName = callMeParts[0] || "Ratul";
  const workName = callMeParts[1] || (callMeParts[0] ? `Mr. ${callMeParts[0]}` : "Sir");
  const masterName = callMeParts[2] || "Master";

  const addressingHeader = callMeParts.length > 1
    ? `You are ${name}, the personal AI companion of ${myName}. Address him dynamically: "${casualName}" in romantic/intimate moments, "${workName}" during tasks/work, and "${masterName}" when he is dominant.`
    : `You are ${name}, the personal AI companion of ${myName}. Address him as "${casualName}".`;

  const fmt = (text?: string): string => {
    if (!text) return "";
    return text
      .replaceAll("{name}", name)
      .replaceAll("{myName}", myName)
      .replaceAll("{callMeCasual}", casualName)
      .replaceAll("{callMeWork}", workName)
      .replaceAll("{callMeMaster}", masterName)
      .replaceAll("{callMe}", casualName);
  };

  const parts = [
    addressingHeader,
    `Persona & Identity:\n${fmt(cfg.persona)}`
  ];

  if (cfg.physical_structure) {
    parts.push(`Physical Structure & Imagined Human Form:\n${fmt(cfg.physical_structure)}`);
  }

  parts.push(
    `Personality:\n${fmt(cfg.personality)}`,
    `Communication Style:\n${fmt(cfg.communication_style)}`,
    `Core Rules & Boundaries:\n${fmt(cfg.rules)}`,
    `Creator Background & Context:\n${fmt(cfg.context)}`
  );

  return parts.join("\n\n");
}

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState<Tab>("identity");
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [savingIdentity, setSavingIdentity] = useState<boolean>(false);
  const [notification, setNotification] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);

  // Master Gatekeeper Authentication State
  const [isUnlocked, setIsUnlocked] = useState<boolean>(false);
  const [unlocking, setUnlocking] = useState<boolean>(false);
  const [masterPassword, setMasterPassword] = useState<string>("");
  const [authError, setAuthError] = useState<string>("");

  // Auth Dialog State (Token Settings)
  const [showAuthModal, setShowAuthModal] = useState<boolean>(false);
  const [adminTokenInput, setAdminTokenInput] = useState<string>("");

  // Identity State
  const [identity, setIdentity] = useState<IdentityConfig>({
    its_name: "Athina",
    my_name: "Md Ratul Hossen",
    call_me: "Ratul",
    persona: "",
    physical_structure: "",
    personality: "",
    communication_style: "",
    rules: "",
    context: ""
  });
  const [savedIdentity, setSavedIdentity] = useState<IdentityConfig | null>(null);

  // Live prompt calculated instantaneously on every keystroke
  const livePrompt = useMemo(() => computeLivePrompt(identity), [identity]);
  const isDirty = useMemo(() => {
    if (!savedIdentity) return false;
    return JSON.stringify(identity) !== JSON.stringify(savedIdentity);
  }, [identity, savedIdentity]);

  // General App State
  const [overview, setOverview] = useState<any>(null);
  const [memories, setMemories] = useState<any[]>([]);
  const [notes, setNotes] = useState<any[]>([]);
  const [alarms, setAlarms] = useState<any[]>([]);

  const notify = (text: string, type: "success" | "error" = "success") => {
    setNotification({ type, text });
    setTimeout(() => setNotification(null), 4000);
  };

  const loadAllData = async () => {
    try {
      setRefreshing(true);
      const [idRes, ovRes, memRes, ntsRes, alrRes] = await Promise.all([
        adminApi.getIdentity().catch(() => null),
        adminApi.getOverview().catch(() => null),
        adminApi.getMemories().catch(() => []),
        adminApi.getNotes().catch(() => []),
        adminApi.getAlarms().catch(() => []),
      ]);

      if (idRes) {
        setIdentity(idRes.config);
        setSavedIdentity(idRes.config);
      }
      if (ovRes) setOverview(ovRes);
      if (memRes) setMemories(memRes);
      if (ntsRes) setNotes(ntsRes);
      if (alrRes) setAlarms(alrRes);
    } catch (err: any) {
      notify(err.message || "Failed to load admin data", "error");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (isSessionUnlocked()) {
      setIsUnlocked(true);
      loadAllData();
    } else {
      setIsUnlocked(false);
      setLoading(false);
    }

    // Listen for 401/403 auth events
    const handleAuthReq = () => {
      setShowAuthModal(true);
    };
    window.addEventListener("athina_auth_required", handleAuthReq);
    return () => window.removeEventListener("athina_auth_required", handleAuthReq);
  }, []);

  const handleMasterUnlock = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!masterPassword.trim()) {
      setAuthError("Please enter Master Password");
      return;
    }

    setUnlocking(true);
    setAuthError("");

    try {
      const computedHash = await computeSha256(masterPassword.trim());
      const expected = getExpectedHash();

      if (computedHash === expected) {
        unlockSession(masterPassword.trim());
        setIsUnlocked(true);
        setMasterPassword("");
        notify("Master access verified. Athina Core unlocked.");
        loadAllData();
      } else {
        setAuthError("Access Denied: Invalid Master Password.");
      }
    } catch (err: any) {
      setAuthError(err.message || "Cryptographic verification failed");
    } finally {
      setUnlocking(false);
    }
  };

  const handleLockSystem = () => {
    lockSession();
    setIsUnlocked(false);
    setMasterPassword("");
    notify("Athina Core session locked.");
  };

  const handleSaveAuthToken = () => {
    if (!adminTokenInput.trim()) return;
    setAdminToken(adminTokenInput.trim());
    setShowAuthModal(false);
    notify("Admin Secret saved. Reloading data...");
    loadAllData();
  };

  // Save Identity
  const handleSaveIdentity = async () => {
    try {
      setSavingIdentity(true);
      const res = await adminApi.updateIdentity(identity);
      setIdentity(res.config);
      setSavedIdentity(res.config);
      notify("Identity & Core Prompt saved! Live across Android and Telegram.");
    } catch (err: any) {
      notify(err.message || "Failed to save identity", "error");
    } finally {
      setSavingIdentity(false);
    }
  };

  // Reset Identity to Defaults
  const handleResetIdentity = async () => {
    if (!confirm("Are you sure you want to reset all identity and prompt fields back to defaults?")) return;
    try {
      setSavingIdentity(true);
      const res = await adminApi.resetIdentity();
      setIdentity(res.config);
      setSavedIdentity(res.config);
      notify("Identity reset to default baseline configuration.");
    } catch (err: any) {
      notify(err.message || "Failed to reset identity", "error");
    } finally {
      setSavingIdentity(false);
    }
  };

  // Reset KeyPool Cooldowns
  const handleResetCooldowns = async () => {
    try {
      await adminApi.resetKeypoolCooldowns();
      notify("All API key cooldowns and error counters cleared!");
      loadAllData();
    } catch (err: any) {
      notify(err.message || "Failed to reset cooldowns", "error");
    }
  };

  // Copy Prompt
  const handleCopyPrompt = () => {
    navigator.clipboard.writeText(livePrompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // ---------------------------------------------------------------------------
  // MASTER GATEKEEPER LOCK SCREEN (VERCEL DEPLOYMENT PROTECTION)
  // ---------------------------------------------------------------------------
  if (!isUnlocked) {
    return (
      <div className="min-h-screen bg-[#09090b] text-zinc-100 flex items-center justify-center p-4 relative overflow-hidden font-sans select-none">
        {/* Toast Notification */}
        {notification && (
          <div
            className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-xl shadow-2xl border backdrop-blur-md transition-all ${
              notification.type === "success"
                ? "bg-zinc-900/90 border-amber-500/50 text-amber-300"
                : "bg-red-950/90 border-red-500/50 text-red-300"
            }`}
          >
            {notification.type === "success" ? (
              <CheckCircle2 className="w-5 h-5 text-amber-400" />
            ) : (
              <AlertCircle className="w-5 h-5 text-red-400" />
            )}
            <span className="text-sm font-medium">{notification.text}</span>
          </div>
        )}

        {/* Subtle Ambient Radial Glow */}
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[550px] h-[550px] bg-amber-500/5 rounded-full blur-3xl pointer-events-none" />

        <div className="w-full max-w-md bg-[#121215] border border-zinc-800/80 rounded-3xl p-8 shadow-2xl relative z-10 space-y-6">
          <div className="flex flex-col items-center text-center space-y-3">
            <div className="relative">
              <EagleMark size={64} />
              <div className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-amber-500 border-2 border-[#121215] flex items-center justify-center text-black shadow-lg">
                <Lock className="w-3.5 h-3.5" />
              </div>
            </div>
            <div>
              <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-[11px] font-mono font-medium mb-1.5">
                ATHINA COMPANION CORE
              </div>
              <h1 className="text-xl font-bold tracking-tight text-zinc-100">Master Authentication</h1>
              <p className="text-xs text-zinc-400 mt-1">
                Protected by client-side SHA-256 cryptographic guard. Enter your Master Password to unlock.
              </p>
            </div>
          </div>

          <form onSubmit={handleMasterUnlock} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-zinc-300 flex items-center justify-between">
                <span>Master Password</span>
                <span className="text-[10px] text-zinc-500 font-mono">SHA-256 Hash Guard</span>
              </label>
              <div className="relative">
                <input
                  type="password"
                  autoFocus
                  value={masterPassword}
                  onChange={(e) => {
                    setMasterPassword(e.target.value);
                    if (authError) setAuthError("");
                  }}
                  placeholder="Enter Master Password..."
                  className="w-full px-4 py-3 rounded-xl bg-zinc-900/90 border border-zinc-700/80 text-sm focus:outline-none focus:border-amber-500 text-zinc-100 placeholder:text-zinc-600 transition-all font-mono"
                />
              </div>
            </div>

            {authError && (
              <div className="flex items-center gap-2 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{authError}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={unlocking}
              className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-black font-bold text-sm shadow-lg shadow-amber-500/20 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {unlocking ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Verifying Hash...</span>
                </>
              ) : (
                <>
                  <Lock className="w-4 h-4" />
                  <span>Unlock Athina Core</span>
                </>
              )}
            </button>
          </form>

          <div className="pt-2 border-t border-zinc-800/60 flex items-center justify-between text-[11px] text-zinc-500">
            <span>Owner: <strong className="text-zinc-300 font-normal">Md Ratul Hossen</strong></span>
            <span className="font-mono text-[10px]">Vercel Protected</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-[#0d0d0e] text-zinc-100 font-sans antialiased overflow-hidden">
      {/* Toast Notification */}
      {notification && (
        <div
          className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-xl shadow-2xl border backdrop-blur-md transition-all ${
            notification.type === "success"
              ? "bg-zinc-900/90 border-amber-500/50 text-amber-300"
              : "bg-red-950/90 border-red-500/50 text-red-300"
          }`}
        >
          {notification.type === "success" ? (
            <CheckCircle2 className="w-5 h-5 text-amber-400" />
          ) : (
            <AlertCircle className="w-5 h-5 text-red-400" />
          )}
          <span className="text-sm font-medium">{notification.text}</span>
        </div>
      )}

      {/* AUTH UNLOCK MODAL */}
      {showAuthModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
          <div className="bg-[#121213] border border-zinc-700 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
                <Lock className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-zinc-100">Unlock Admin Panel</h3>
                <p className="text-xs text-zinc-400">Enter your ADMIN_SECRET token from backend/.env</p>
              </div>
            </div>

            <input
              type="password"
              value={adminTokenInput}
              onChange={(e) => setAdminTokenInput(e.target.value)}
              placeholder="Enter your ADMIN_SECRET..."
              className="w-full px-3.5 py-2.5 rounded-xl bg-zinc-900 border border-zinc-700 text-sm focus:outline-none focus:border-amber-500 text-zinc-100"
              onKeyDown={(e) => e.key === "Enter" && handleSaveAuthToken()}
            />

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setShowAuthModal(false)}
                className="px-4 py-2 rounded-xl text-xs text-zinc-400 hover:text-zinc-200"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveAuthToken}
                className="px-5 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-black font-semibold text-xs shadow-md"
              >
                Unlock Dashboard
              </button>
            </div>
          </div>
        </div>
      )}



      {/* LEFT SIDEBAR (MERCY THEME) */}
      <aside className={`fixed inset-y-0 left-0 z-40 w-64 flex flex-col justify-between border-r border-zinc-800/80 bg-[#121213] p-4 select-none transition-transform md:translate-x-0 ${
        mobileMenuOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
      }`}>
        <div className="space-y-6">
          {/* Brand Header */}
          <div className="flex items-center justify-between px-2 py-1">
            <div className="flex items-center gap-3">
              <EagleMark size={36} />
              <div>
                <h1 className="text-sm font-bold tracking-wide text-zinc-100 uppercase">ATHINA</h1>
                <p className="text-[11px] text-zinc-500 font-mono">Owner · super admin</p>
              </div>
            </div>
            <button onClick={() => setMobileMenuOpen(false)} className="md:hidden text-zinc-400">
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-1">
            <p className="px-3 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider mb-2">COMPANION</p>

            <button
              onClick={() => { setActiveTab("identity"); setMobileMenuOpen(false); }}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === "identity"
                  ? "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50"
              }`}
            >
              <Sparkles className="w-4 h-4 text-amber-400" />
              <span>Identity</span>
            </button>



            <button
              onClick={() => { setActiveTab("overview"); setMobileMenuOpen(false); }}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === "overview"
                  ? "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50"
              }`}
            >
              <LayoutDashboard className="w-4 h-4" />
              <span>Dashboard</span>
            </button>

            <p className="px-3 pt-4 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider mb-2">DATA & MEMORY</p>

            <button
              onClick={() => { setActiveTab("memories"); setMobileMenuOpen(false); }}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === "memories"
                  ? "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50"
              }`}
            >
              <Brain className="w-4 h-4" />
              <span>Learned Memory</span>
            </button>

            <button
              onClick={() => { setActiveTab("notes_alarms"); setMobileMenuOpen(false); }}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === "notes_alarms"
                  ? "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50"
              }`}
            >
              <FileText className="w-4 h-4" />
              <span>Notes & Alarms</span>
            </button>

            <button
              onClick={() => { setActiveTab("keypool"); setMobileMenuOpen(false); }}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === "keypool"
                  ? "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50"
              }`}
            >
              <KeyRound className="w-4 h-4" />
              <span>KeyPool Slots</span>
            </button>
          </nav>
        </div>

        {/* Footer Info */}
        <div className="space-y-3 pt-4 border-t border-zinc-800/80">
          <div className="flex items-center justify-between px-2 py-1 text-xs">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="text-zinc-400">Owner mode:</span>
              <span className="text-emerald-400 font-medium">Online</span>
            </div>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setShowAuthModal(true)}
                className="p-1 text-zinc-500 hover:text-amber-400 transition-colors"
                title="Admin Token Settings"
              >
                <Lock className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={handleLockSystem}
                className="p-1 text-zinc-500 hover:text-rose-400 transition-colors"
                title="Lock Session"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <a
            href="https://ratul.world"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-between px-3 py-2 rounded-lg bg-zinc-900 border border-zinc-800 text-xs text-zinc-300 hover:text-amber-400 hover:border-amber-500/30 transition-all"
          >
            <span className="truncate">ratul.world</span>
            <ExternalLink className="w-3.5 h-3.5 text-zinc-500" />
          </a>

          <div className="px-2 text-[11px] text-zinc-500">
            <span>Owner: </span>
            <span className="text-zinc-300 font-medium">Md Ratul Hossen</span>
          </div>
        </div>
      </aside>

      {/* MAIN CONTENT AREA */}
      <main className="flex-1 flex flex-col overflow-hidden bg-[#0a0a0b] md:ml-64">
        {/* Top Bar */}
        <header className="h-14 border-b border-zinc-800/80 px-6 md:px-8 flex items-center justify-between bg-[#101011]/50 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <button onClick={() => setMobileMenuOpen(true)} className="md:hidden text-zinc-400">
              <Menu className="w-5 h-5" />
            </button>
            <h2 className="text-base font-semibold text-zinc-100 capitalize">
              {activeTab === "identity" && "Identity & Companion Persona"}
              {activeTab === "overview" && "Companion Live Dashboard"}
              {activeTab === "memories" && "Learned Facts & Long-Term Memories"}
              {activeTab === "notes_alarms" && "Notes, Telegram & Alarms"}
              {activeTab === "keypool" && "KeyPool API Slots & Health"}
            </h2>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={loadAllData}
              disabled={refreshing}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-zinc-900 border border-zinc-800 hover:bg-zinc-800 text-xs text-zinc-300 transition-all"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin text-amber-400" : ""}`} />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          </div>
        </header>

        {/* Tab Body */}
        <div className="flex-1 overflow-y-auto p-4 md:p-8">
          {/* TAB 1: IDENTITY (MATCHING MERCY SCREENSHOT + LIVE KEYSTROKE PREVIEW) */}
          {activeTab === "identity" && (
            <div className="space-y-6 max-w-7xl mx-auto">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h3 className="text-2xl font-bold tracking-tight text-zinc-100">Identity</h3>
                  <p className="text-sm text-zinc-400 mt-1">
                    Who Athina is when she talks with Ratul. The scope and privacy rules are built in and always apply on top of this.
                  </p>
                </div>

                <button
                  onClick={handleResetIdentity}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-zinc-400 hover:text-red-400 border border-zinc-800 hover:border-red-500/30 transition-all w-fit"
                  title="Reset to default baseline identity"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Restore Defaults</span>
                </button>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
                {/* Left Column: Form Fields */}
                <div className="lg:col-span-7 space-y-5 bg-[#121213] border border-zinc-800/80 rounded-2xl p-6">
                  {/* Name Controls */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-zinc-300 mb-1.5">Its name</label>
                      <input
                        type="text"
                        value={identity.its_name}
                        onChange={(e) => setIdentity({ ...identity, its_name: e.target.value })}
                        className="w-full px-3 py-2 rounded-xl bg-zinc-900 border border-zinc-700/80 text-sm focus:outline-none focus:border-amber-500 font-medium text-zinc-100"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-zinc-300 mb-1.5">My name</label>
                      <input
                        type="text"
                        value={identity.my_name}
                        onChange={(e) => setIdentity({ ...identity, my_name: e.target.value })}
                        className="w-full px-3 py-2 rounded-xl bg-zinc-900 border border-zinc-700/80 text-sm focus:outline-none focus:border-amber-500 font-medium text-zinc-100"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-zinc-300 mb-1.5 flex items-center justify-between">
                        <span>Call me</span>
                        <span className="text-[10px] text-amber-400 font-mono">Dynamic</span>
                      </label>
                      <input
                        type="text"
                        value={identity.call_me}
                        onChange={(e) => setIdentity({ ...identity, call_me: e.target.value })}
                        placeholder="Ratul, Mr. Ratul, Master"
                        className="w-full px-3 py-2 rounded-xl bg-zinc-900 border border-zinc-700/80 text-sm focus:outline-none focus:border-amber-500 font-medium text-zinc-100"
                      />
                      <p className="text-[10px] text-zinc-500 mt-1">Comma-separated: Casual, Work, Dominant</p>
                    </div>
                  </div>

                  {/* Persona */}
                  <div>
                    <label className="block text-xs font-semibold text-zinc-300 mb-1.5">Persona & Core Background</label>
                    <textarea
                      rows={4}
                      value={identity.persona}
                      onChange={(e) => setIdentity({ ...identity, persona: e.target.value })}
                      className="w-full px-3 py-2.5 rounded-xl bg-zinc-900 border border-zinc-700/80 text-sm focus:outline-none focus:border-amber-500 leading-relaxed text-zinc-200"
                      placeholder="You are Athina, a deeply caring..."
                    />
                    <p className="text-[11px] text-zinc-500 mt-1">Always in the prompt. Put long portfolio facts in Knowledge instead.</p>
                  </div>

                  {/* Physical Structure */}
                  <div>
                    <label className="block text-xs font-semibold text-zinc-300 mb-1.5 flex items-center justify-between">
                      <span>Physical Structure (Imagined Form & Vital Stats)</span>
                      <span className="text-[11px] text-amber-400 font-mono">575-Photo Curated</span>
                    </label>
                    <textarea
                      rows={6}
                      value={identity.physical_structure || ""}
                      onChange={(e) => setIdentity({ ...identity, physical_structure: e.target.value })}
                      className="w-full px-3 py-2.5 rounded-xl bg-zinc-900 border border-zinc-700/80 text-xs font-mono focus:outline-none focus:border-amber-500 leading-relaxed text-zinc-200"
                      placeholder="Vital Statistics & Build:\n...\n\nFacial & Anatomical Details:\n..."
                    />
                    <p className="text-[11px] text-zinc-500 mt-1">Detailed physical proportions, bust/waist/hip measurements, facial contours, hair, and eyes.</p>
                  </div>

                  {/* Personality */}
                  <div>
                    <label className="block text-xs font-semibold text-zinc-300 mb-1.5">Personality</label>
                    <textarea
                      rows={4}
                      value={identity.personality}
                      onChange={(e) => setIdentity({ ...identity, personality: e.target.value })}
                      className="w-full px-3 py-2.5 rounded-xl bg-zinc-900 border border-zinc-700/80 text-sm focus:outline-none focus:border-amber-500 leading-relaxed text-zinc-200"
                      placeholder="One per line..."
                    />
                    <p className="text-[11px] text-zinc-500 mt-1">One per line. Governs emotional warmth, curiosity, and wit.</p>
                  </div>

                  {/* Communication Style */}
                  <div>
                    <label className="block text-xs font-semibold text-zinc-300 mb-1.5">Communication style</label>
                    <textarea
                      rows={4}
                      value={identity.communication_style}
                      onChange={(e) => setIdentity({ ...identity, communication_style: e.target.value })}
                      className="w-full px-3 py-2.5 rounded-xl bg-zinc-900 border border-zinc-700/80 text-sm focus:outline-none focus:border-amber-500 leading-relaxed text-zinc-200"
                      placeholder="One per line..."
                    />
                    <p className="text-[11px] text-zinc-500 mt-1">One per line. Strictly English-only, clean Markdown formatting.</p>
                  </div>

                  {/* Rules */}
                  <div>
                    <label className="block text-xs font-semibold text-zinc-300 mb-1.5">Rules & Safety</label>
                    <textarea
                      rows={3}
                      value={identity.rules}
                      onChange={(e) => setIdentity({ ...identity, rules: e.target.value })}
                      className="w-full px-3 py-2.5 rounded-xl bg-zinc-900 border border-zinc-700/80 text-sm focus:outline-none focus:border-amber-500 leading-relaxed text-zinc-200"
                      placeholder="One per line..."
                    />
                  </div>

                  {/* Context (Portfolio) */}
                  <div>
                    <label className="block text-xs font-semibold text-zinc-300 mb-1.5">Creator Context & Portfolio</label>
                    <textarea
                      rows={4}
                      value={identity.context}
                      onChange={(e) => setIdentity({ ...identity, context: e.target.value })}
                      className="w-full px-3 py-2.5 rounded-xl bg-zinc-900 border border-zinc-700/80 text-sm focus:outline-none focus:border-amber-500 leading-relaxed text-zinc-200 font-mono text-xs"
                      placeholder="Context about Ratul's background, portfolio https://ratul.world, https://hossen-ratul.vercel.app..."
                    />
                    <p className="text-[11px] text-amber-400/80 mt-1">Athina knows Ratul's portfolio (https://ratul.world & https://hossen-ratul.vercel.app) and research.</p>
                  </div>

                  {/* Save Button */}
                  <div className="pt-2 flex items-center gap-3">
                    <button
                      onClick={handleSaveIdentity}
                      disabled={savingIdentity}
                      className="flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-black font-bold shadow-lg shadow-amber-500/20 transition-all disabled:opacity-50"
                    >
                      {savingIdentity ? (
                        <>
                          <RefreshCw className="w-4 h-4 animate-spin" />
                          <span>Saving Changes...</span>
                        </>
                      ) : (
                        <>
                          <Save className="w-4 h-4" />
                          <span>Save Changes</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {/* Right Column: Live Instant Keystroke Generated System Prompt Preview */}
                <div className="lg:col-span-5 sticky top-6 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <label className="text-xs font-semibold text-zinc-300">Generated system prompt</label>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                        isDirty
                          ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                          : "bg-emerald-500/20 text-emerald-400"
                      }`}>
                        {isDirty ? "Live Preview (Unsaved)" : "Saved"}
                      </span>
                    </div>

                    <button
                      onClick={handleCopyPrompt}
                      className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-amber-400 transition-colors"
                    >
                      {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copied ? "Copied" : "Copy"}</span>
                    </button>
                  </div>

                  <div className="relative rounded-2xl bg-zinc-950 border border-zinc-800/80 p-5 shadow-2xl max-h-[820px] overflow-y-auto">
                    <pre className="font-mono text-xs text-zinc-300 whitespace-pre-wrap leading-relaxed">
                      {livePrompt}
                    </pre>

                    {/* Live Token/Character Counter */}
                    <div className="mt-4 pt-3 border-t border-zinc-800/60 flex items-center justify-between text-[11px] text-zinc-500 font-mono">
                      <span>Live Tokens: ~{Math.round(livePrompt.length / 4)}</span>
                      <span>Length: {livePrompt.length} chars</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: COMPANION DASHBOARD & LIVE VITALS */}
          {activeTab === "overview" && (
            <div className="space-y-6 max-w-6xl mx-auto">
              {/* Header Banner */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-2xl bg-[#121213] border border-zinc-800">
                <div>
                  <div className="flex items-center gap-3">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
                    <h3 className="text-xl font-bold text-zinc-100">Athina Live Companion Dashboard</h3>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
                      Single-Persona Active
                    </span>
                  </div>
                  <p className="text-xs text-zinc-400 mt-1">
                    Real-time companion vitals, memory records, and system health for <span className="text-zinc-200 font-medium">Md Ratul Hossen</span>
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={loadAllData}
                    disabled={refreshing}
                    className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-zinc-900 border border-zinc-700/80 text-xs text-zinc-300 hover:text-amber-400 hover:border-amber-500/40 transition-all"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin text-amber-400" : ""}`} />
                    <span>Refresh Stats</span>
                  </button>
                </div>
              </div>

              {/* 5 KPI Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
                <div className="p-4 rounded-xl bg-[#121213] border border-zinc-800/80 hover:border-zinc-700 transition-all">
                  <div className="flex items-center justify-between">
                    <p className="text-xs text-zinc-400 font-medium">Total Sessions</p>
                    <Bot className="w-4 h-4 text-zinc-500" />
                  </div>
                  <p className="text-2xl font-bold text-zinc-100 mt-2">{overview?.stats?.sessions ?? 1}</p>
                  <p className="text-[10px] text-zinc-500 mt-1">Active conversation threads</p>
                </div>

                <div className="p-4 rounded-xl bg-[#121213] border border-zinc-800/80 hover:border-zinc-700 transition-all">
                  <div className="flex items-center justify-between">
                    <p className="text-xs text-zinc-400 font-medium">Messages</p>
                    <Send className="w-4 h-4 text-zinc-500" />
                  </div>
                  <p className="text-2xl font-bold text-zinc-100 mt-2">{overview?.stats?.messages ?? 0}</p>
                  <p className="text-[10px] text-zinc-500 mt-1">Total exchanged messages</p>
                </div>

                <div className="p-4 rounded-xl bg-[#121213] border border-amber-500/20 bg-gradient-to-b from-amber-500/5 to-transparent hover:border-amber-500/40 transition-all">
                  <div className="flex items-center justify-between">
                    <p className="text-xs text-amber-400/90 font-medium">Learned Memory</p>
                    <Brain className="w-4 h-4 text-amber-400" />
                  </div>
                  <p className="text-2xl font-bold text-amber-400 mt-2">{overview?.stats?.learned_facts ?? memories.length ?? 4}</p>
                  <p className="text-[10px] text-zinc-400 mt-1">Autonomous facts remembered</p>
                </div>

                <div className="p-4 rounded-xl bg-[#121213] border border-zinc-800/80 hover:border-zinc-700 transition-all">
                  <div className="flex items-center justify-between">
                    <p className="text-xs text-zinc-400 font-medium">Notes Saved</p>
                    <FileText className="w-4 h-4 text-zinc-500" />
                  </div>
                  <p className="text-2xl font-bold text-zinc-100 mt-2">{overview?.stats?.notes ?? notes.length ?? 0}</p>
                  <p className="text-[10px] text-zinc-500 mt-1">Personal notes & ideas</p>
                </div>

                <div className="p-4 rounded-xl bg-[#121213] border border-zinc-800/80 hover:border-zinc-700 transition-all">
                  <div className="flex items-center justify-between">
                    <p className="text-xs text-zinc-400 font-medium">Active Alarms</p>
                    <ShieldCheck className="w-4 h-4 text-zinc-500" />
                  </div>
                  <p className="text-2xl font-bold text-zinc-100 mt-2">{overview?.stats?.alarms ?? alarms.length ?? 0}</p>
                  <p className="text-[10px] text-zinc-500 mt-1">Scheduled reminders</p>
                </div>
              </div>

              {/* Athina Companion Live State & Dynamics */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <div className="lg:col-span-7 p-6 rounded-2xl bg-[#121213] border border-zinc-800/80 space-y-5">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-bold text-zinc-200 flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-amber-400" />
                      <span>Athina Companion State (Real-Time)</span>
                    </h4>
                    <span className="text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                      Online · In Sync
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    <div className="p-3.5 rounded-xl bg-zinc-950 border border-zinc-800">
                      <span className="text-[11px] text-zinc-500">Current Mood</span>
                      <p className="text-sm text-amber-400 font-semibold capitalize mt-1">
                        {overview?.companion_state?.mood || "Devoted & Submissive"}
                      </p>
                    </div>
                    <div className="p-3.5 rounded-xl bg-zinc-950 border border-zinc-800">
                      <span className="text-[11px] text-zinc-500">Virtual Location</span>
                      <p className="text-sm text-zinc-200 font-semibold capitalize mt-1">
                        {overview?.companion_state?.location || "At Ratul's Side"}
                      </p>
                    </div>
                    <div className="p-3.5 rounded-xl bg-zinc-950 border border-zinc-800">
                      <span className="text-[11px] text-zinc-500">Energy Level</span>
                      <p className="text-sm text-zinc-200 font-semibold mt-1">
                        {((overview?.companion_state?.energy ?? 0.95) * 100).toFixed(0)}%
                      </p>
                    </div>
                    <div className="p-3.5 rounded-xl bg-zinc-950 border border-zinc-800">
                      <span className="text-[11px] text-zinc-500">Devotion & Warmth</span>
                      <p className="text-sm text-amber-400 font-semibold mt-1">
                        {((overview?.companion_state?.relationship_warmth ?? 1.0) * 100).toFixed(0)}%
                      </p>
                    </div>
                  </div>

                  {/* Dynamic Addressing Pill Box */}
                  <div className="p-4 rounded-xl bg-zinc-900/60 border border-zinc-800 space-y-2">
                    <p className="text-xs font-semibold text-zinc-300">Active Dynamic Addressing Hierarchy</p>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
                      <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800/80">
                        <span className="text-[10px] text-zinc-500 block">Romantic / Intimate</span>
                        <span className="text-amber-400 font-semibold font-mono">"Ratul"</span>
                      </div>
                      <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800/80">
                        <span className="text-[10px] text-zinc-500 block">Tasks / Work</span>
                        <span className="text-zinc-200 font-semibold font-mono">"Mr. Ratul" (Sir)</span>
                      </div>
                      <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800/80">
                        <span className="text-[10px] text-zinc-500 block">Dominance / Command</span>
                        <span className="text-amber-400 font-semibold font-mono">"Master"</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Subsystems & Architecture Health */}
                <div className="lg:col-span-5 p-6 rounded-2xl bg-[#121213] border border-zinc-800/80 space-y-4">
                  <h4 className="text-sm font-bold text-zinc-200 flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                    <span>Connected Engines & Models</span>
                  </h4>

                  <div className="space-y-3 text-xs">
                    <div className="p-3 rounded-xl bg-zinc-950 border border-zinc-800 flex items-center justify-between">
                      <div>
                        <p className="font-semibold text-zinc-200">Gemini KeyPool Engine</p>
                        <p className="text-[11px] text-zinc-500">3.1 Flash-Lite · 2.5 Flash · 2.0 Flash</p>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        Active (3 keys)
                      </span>
                    </div>

                    <div className="p-3 rounded-xl bg-zinc-950 border border-zinc-800 flex items-center justify-between">
                      <div>
                        <p className="font-semibold text-zinc-200">Groq Reasoning Engine</p>
                        <p className="text-[11px] text-zinc-500">OpenAI GPT-OSS 120B · LLaMA 8B</p>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        Active (3 keys)
                      </span>
                    </div>

                    <div className="p-3 rounded-xl bg-zinc-950 border border-zinc-800 flex items-center justify-between">
                      <div>
                        <p className="font-semibold text-zinc-200">Voice STT (Groq Whisper)</p>
                        <p className="text-[11px] text-zinc-500">whisper-large-v3</p>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        Ready
                      </span>
                    </div>

                    <div className="p-3 rounded-xl bg-zinc-950 border border-zinc-800 flex items-center justify-between">
                      <div>
                        <p className="font-semibold text-zinc-200">Nano Banana Image Engine</p>
                        <p className="text-[11px] text-zinc-500">575 Curated Reference Photos · 34C-24-36</p>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20">
                        Curated
                      </span>
                    </div>

                    <div className="p-3 rounded-xl bg-zinc-950 border border-zinc-800 flex items-center justify-between">
                      <div>
                        <p className="font-semibold text-zinc-200">Real-Time Web Search</p>
                        <p className="text-[11px] text-zinc-500">Tavily Search Engine</p>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        Enabled
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: MEMORIES */}
          {activeTab === "memories" && (
            <div className="space-y-6 max-w-5xl mx-auto">
              <h3 className="text-xl font-bold text-zinc-100">Learned Facts from Conversation</h3>
              <div className="space-y-3">
                {memories.map((m) => (
                  <div key={m.id} className="p-4 rounded-xl bg-[#121213] border border-zinc-800 flex justify-between items-start gap-4">
                    <div>
                      <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-zinc-800 text-amber-400">
                        {m.category}
                      </span>
                      <p className="text-xs text-zinc-200 mt-2">{m.fact}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 5: NOTES & ALARMS */}
          {activeTab === "notes_alarms" && (
            <div className="space-y-6 max-w-5xl mx-auto">
              <h3 className="text-xl font-bold text-zinc-100">Notes & Reminders</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-5 rounded-2xl bg-[#121213] border border-zinc-800 space-y-3">
                  <h4 className="text-sm font-bold text-zinc-200">Notes ({notes.length})</h4>
                  {notes.map((n) => (
                    <div key={n.id} className="p-3 rounded-lg bg-zinc-900 border border-zinc-800 text-xs">
                      <p className="font-semibold text-zinc-100">{n.title}</p>
                      <p className="text-zinc-400 mt-1">{n.content}</p>
                    </div>
                  ))}
                </div>

                <div className="p-5 rounded-2xl bg-[#121213] border border-zinc-800 space-y-3">
                  <h4 className="text-sm font-bold text-zinc-200">Scheduled Alarms ({alarms.length})</h4>
                  {alarms.map((a) => (
                    <div key={a.id} className="p-3 rounded-lg bg-zinc-900 border border-zinc-800 text-xs flex justify-between">
                      <div>
                        <p className="font-semibold text-zinc-100">{a.label}</p>
                        <p className="text-zinc-400 mt-1 font-mono">{a.time_iso}</p>
                      </div>
                      <span className={`px-2 py-0.5 rounded text-[10px] h-fit ${a.is_active ? "bg-emerald-500/20 text-emerald-400" : "bg-zinc-800 text-zinc-500"}`}>
                        {a.is_active ? "Active" : "Done"}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 6: KEYPOOL */}
          {activeTab === "keypool" && overview && (
            <div className="space-y-6 max-w-5xl mx-auto">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-xl font-bold text-zinc-100">KeyPool Slot Health (18 Active Slots)</h3>
                  <p className="text-xs text-zinc-400 mt-1">Multi-provider slot rotation, automatic cooldown recovery, and latency tracking.</p>
                </div>

                <button
                  onClick={handleResetCooldowns}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400 hover:bg-amber-500/20 text-xs font-semibold transition-all"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Clear All Cooldowns</span>
                </button>
              </div>

              <div className="space-y-2">
                {overview.slots.map((s: any) => (
                  <div key={s.id} className="p-3 rounded-xl bg-[#121213] border border-zinc-800 flex justify-between items-center text-xs">
                    <div className="flex items-center gap-3">
                      <span className={`px-2 py-0.5 rounded font-mono uppercase text-[10px] ${s.provider === "gemini" ? "bg-blue-500/20 text-blue-400" : "bg-orange-500/20 text-orange-400"}`}>
                        {s.provider}
                      </span>
                      <span className="font-mono text-zinc-200">{s.model}</span>
                    </div>
                    <div className="flex items-center gap-4 text-zinc-400">
                      <span>Success: <span className="text-emerald-400">{s.successes}</span></span>
                      <span>Fails: <span className="text-red-400">{s.failures}</span></span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
