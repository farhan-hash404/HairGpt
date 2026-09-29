/**
 * HairGPT Mobile Bridge Client Helper
 * 
 * Provides typed functions to communicate with the React Native mobile wrapper.
 * Safely degrades to no-op or standard Web APIs when running in standard web browsers.
 */

declare global {
  interface Window {
    ReactNativeWebView?: {
      postMessage: (message: string) => void;
    };
  }
}

/**
 * Checks if the page is currently running inside the React Native mobile app wrapper.
 */
export function isMobileApp(): boolean {
  return typeof window !== 'undefined' && Boolean(window.ReactNativeWebView);
}

/**
 * Sends a message to the React Native host app.
 */
function postToNative(action: { type: string; payload?: unknown }): boolean {
  if (typeof window !== 'undefined' && window.ReactNativeWebView) {
    window.ReactNativeWebView.postMessage(JSON.stringify(action));
    return true;
  }
  return false;
}

/**
 * Triggers native haptic tactile feedback on iOS & Android.
 */
export function triggerHaptic(style: 'light' | 'medium' | 'heavy' | 'success' | 'error' = 'light') {
  return postToNative({
    type: 'HAPTIC',
    payload: { style },
  });
}

/**
 * Opens the native OS share sheet.
 * Falls back to Web Share API if open in a standard mobile browser.
 */
export async function nativeShare(data: { title?: string; message: string; url?: string }) {
  const sentToWrapper = postToNative({
    type: 'SHARE',
    payload: data,
  });

  if (!sentToWrapper && typeof navigator !== 'undefined' && navigator.share) {
    try {
      await navigator.share({
        title: data.title,
        text: data.message,
        url: data.url,
      });
    } catch {
      // User cancelled share or not supported
    }
  }
}

/**
 * Listens to messages dispatched from the React Native shell to the Web app.
 */
export function listenToNativeMessage(callback: (data: unknown) => void) {
  if (typeof window === 'undefined') return () => {};

  const handler = (event: Event) => {
    const customEvent = event as CustomEvent;
    callback(customEvent.detail);
  };

  window.addEventListener('HairGptNativeMessage', handler);
  return () => window.removeEventListener('HairGptNativeMessage', handler);
}
