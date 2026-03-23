/**
 * Bridge between the Next.js frontend and Tauri native APIs.
 * Falls back gracefully when running in a browser (non-Tauri) context.
 */

const isTauri = typeof window !== "undefined" && "__TAURI__" in window;

async function invoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  if (!isTauri) throw new Error("Not running in Tauri");
  const { invoke } = await import("@tauri-apps/api/core");
  return invoke<T>(cmd, args);
}

export async function sendDesktopNotification(
  title: string,
  body: string
): Promise<void> {
  if (!isTauri) {
    // Fallback: browser Notification API
    if ("Notification" in window && Notification.permission === "granted") {
      new Notification(title, { body });
    }
    return;
  }
  await invoke("send_desktop_notification", { title, body });
}

export async function storeToken(token: string): Promise<void> {
  if (!isTauri) {
    sessionStorage.setItem("access_token", token);
    return;
  }
  await invoke("store_token", { token });
}

export async function getStoredToken(): Promise<string | null> {
  if (!isTauri) {
    return sessionStorage.getItem("access_token");
  }
  return invoke<string | null>("get_stored_token");
}

export async function clearStoredToken(): Promise<void> {
  if (!isTauri) {
    sessionStorage.removeItem("access_token");
    return;
  }
  await invoke("clear_stored_token");
}

export { isTauri };