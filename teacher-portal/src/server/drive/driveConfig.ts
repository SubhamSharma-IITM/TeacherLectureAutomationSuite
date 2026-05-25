function getEnv(name: string): string | undefined {
  const value = process.env[name];
  return value && value.trim().length > 0 ? value : undefined;
}

export function getDriveFolderId(): string {
  const folderId = getEnv("GOOGLE_DRIVE_FOLDER_ID");
  if (!folderId) {
    throw new Error("Missing required env var: GOOGLE_DRIVE_FOLDER_ID");
  }
  return folderId;
}
