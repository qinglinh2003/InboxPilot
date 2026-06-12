// ---------------------------------------------------------------------------
// Outlook Office.js integration layer
// ---------------------------------------------------------------------------

/* global Office */
declare const Office: any;

// ---- Types ----------------------------------------------------------------

export interface EmailData {
  subject: string;
  sender: string;
  recipients: string[];
  body: string;
  messageId: string;
  conversationId: string;
  existingCategories: string[];
}

// ---- Helpers --------------------------------------------------------------

/** Promisify the Office async-callback pattern. */
function asyncResult<T>(
  fn: (callback: (result: any) => void) => void,
): Promise<T> {
  return new Promise((resolve, reject) => {
    fn((result: any) => {
      if (result.status === Office.AsyncResultStatus?.Failed) {
        reject(new Error(result.error?.message ?? "Office async call failed"));
      } else {
        resolve(result.value);
      }
    });
  });
}

// ---- Public API -----------------------------------------------------------

/**
 * Read all relevant fields from the currently-selected email message using
 * Office.context.mailbox.item.
 */
export async function getCurrentEmail(): Promise<EmailData> {
  if (typeof Office === "undefined" || !Office.context?.mailbox?.item) {
    throw new Error("No email is currently selected. Make sure you opened this from within Outlook.");
  }
  const item = Office.context.mailbox.item;

  // Subject & sender are synchronous properties
  const subject: string = item.subject ?? "";
  const sender: string = item.sender?.emailAddress ?? item.from?.emailAddress ?? "";

  // Recipients (to + cc)
  const toRecipients: string[] = (item.to ?? []).map(
    (r: any) => r.emailAddress as string,
  );
  const ccRecipients: string[] = (item.cc ?? []).map(
    (r: any) => r.emailAddress as string,
  );
  const recipients = [...toRecipients, ...ccRecipients];

  // Body — try plain text first, fall back to HTML
  let body: string = "";
  try {
    body = await asyncResult<string>((cb) =>
      item.body.getAsync(Office.CoercionType?.Text ?? "text", cb),
    );
  } catch {
    // Text coercion failed, ignore
  }

  // If text body is empty, try HTML and strip tags
  if (!body.trim()) {
    try {
      const html: string = await asyncResult<string>((cb) =>
        item.body.getAsync(Office.CoercionType?.Html ?? "html", cb),
      );
      // Strip HTML tags to get plain text
      const tmp = document.createElement("div");
      tmp.innerHTML = html;
      body = tmp.textContent || tmp.innerText || "";
    } catch {
      // HTML coercion also failed
    }
  }

  // Last resort: use subject as body
  if (!body.trim()) {
    body = subject || "(empty email)";
  }

  // IDs
  const messageId: string = item.itemId ?? "";
  const conversationId: string = item.conversationId ?? "";

  // Existing categories (Mailbox 1.8+)
  let existingCategories: string[] = [];
  if (item.categories) {
    try {
      const cats = await asyncResult<any[]>((cb) => item.categories.getAsync(cb));
      existingCategories = cats.map((c: any) => c.displayName ?? c);
    } catch {
      // Categories API may not be available on all clients
      existingCategories = [];
    }
  }

  return {
    subject,
    sender,
    recipients,
    body,
    messageId,
    conversationId,
    existingCategories,
  };
}

/**
 * Apply (set) categories on the currently-selected message.
 * Uses the Mailbox 1.8+ categories API.
 */
export async function applyCategories(categories: string[]): Promise<void> {
  const item = Office.context.mailbox.item;
  if (!item) {
    throw new Error("No email is currently selected.");
  }

  if (!item.categories) {
    throw new Error("Categories API not available on this client.");
  }

  // categories.addAsync expects a plain string array, not objects
  return asyncResult<void>((cb) => item.categories.addAsync(categories, cb));
}
