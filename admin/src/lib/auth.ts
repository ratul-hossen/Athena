/**
 * Athina Admin Panel - Cryptographic Authentication & Gatekeeper
 * Protects Vercel deployment with SHA-256 Hash Verification.
 */

// Pre-computed SHA-256 hash of "A240504":
// 073f484ff5a2b6a1cd580b100044a6274205ad37149d502adc54178603f96661
export const DEFAULT_ADMIN_HASH = "073f484ff5a2b6a1cd580b100044a6274205ad37149d502adc54178603f96661";

export function getExpectedHash(): string {
  if (typeof window !== "undefined") {
    const custom = process.env.NEXT_PUBLIC_ADMIN_PASSWORD_HASH;
    if (custom && custom.trim().length === 64) {
      return custom.trim().toLowerCase();
    }
  }
  return DEFAULT_ADMIN_HASH;
}

/**
 * Computes standard SHA-256 hex string using browser native WebCrypto API.
 */
export async function computeSha256(input: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(input);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * Checks whether the current browser session has already unlocked the dashboard.
 */
export function isSessionUnlocked(): boolean {
  if (typeof window === "undefined") return false;
  return sessionStorage.getItem("athina_admin_unlocked") === "true";
}

/**
 * Sets session to unlocked state and configures the API secret token.
 */
export function unlockSession(secretToken: string): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem("athina_admin_unlocked", "true");
  localStorage.setItem("athina_admin_secret", secretToken.trim());
}

/**
 * Locks the dashboard immediately, clearing session authentication.
 */
export function lockSession(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem("athina_admin_unlocked");
  localStorage.removeItem("athina_admin_secret");
}
