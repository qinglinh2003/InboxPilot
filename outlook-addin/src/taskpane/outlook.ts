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
  const item = Office.context.mailbox.item;
  if (!item) {
    throw new Error("No email is currently selected.");
  }

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

  // Body — async
  const body: string = await asyncResult<string>((cb) =>
    item.body.getAsync(Office.CoercionType?.Text ?? "text", cb),
  );

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

  // Build category objects expected by the API
  const categoryObjects = categories.map((name) => ({ displayName: name }));

  return asyncResult<void>((cb) => item.categories.addAsync(categoryObjects, cb));
}
