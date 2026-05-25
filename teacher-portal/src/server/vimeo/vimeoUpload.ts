const VIMEO_API = "https://api.vimeo.com";
const CHUNK_SIZE = 5 * 1024 * 1024;

function vimeoHeaders(token: string): HeadersInit {
  return {
    Authorization: `Bearer ${token}`,
    Accept: "application/vnd.vimeo.*+json;version=3.4",
  };
}

export function vimeoPublicLink(uri: string | undefined | null): string | null {
  if (!uri) return null;
  const id = uri.replace(/\/$/, "").split("/").pop();
  return id ? `https://vimeo.com/${id}` : null;
}

export async function createVimeoTusUpload(input: {
  token: string;
  title: string;
  size: number;
}): Promise<{ uploadLink: string; uri: string; link: string | null }> {
  const res = await fetch(`${VIMEO_API}/me/videos`, {
    method: "POST",
    headers: {
      ...vimeoHeaders(input.token),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      name: input.title,
      privacy: { view: "anybody" },
      upload: {
        approach: "tus",
        size: String(input.size),
      },
    }),
  });

  const json = (await res.json()) as {
    uri?: string;
    link?: string;
    upload?: { upload_link?: string };
    error?: string;
    developer_message?: string;
  };

  if (!res.ok) {
    throw new Error(
      json.developer_message || json.error || `Vimeo create failed (${res.status})`
    );
  }

  const uploadLink = json.upload?.upload_link;
  if (!uploadLink || !json.uri) {
    throw new Error("Vimeo did not return upload link");
  }

  return {
    uploadLink,
    uri: json.uri,
    link: json.link ?? vimeoPublicLink(json.uri),
  };
}

/** Stream bytes to Vimeo TUS endpoint (PATCH with Upload-Offset). */
export async function tusUploadBuffer(
  uploadLink: string,
  data: Buffer,
  totalSize: number
): Promise<void> {
  let offset = 0;

  while (offset < data.length) {
    const end = Math.min(offset + CHUNK_SIZE, data.length);
    const chunk = data.subarray(offset, end);
    const body = chunk.buffer.slice(
      chunk.byteOffset,
      chunk.byteOffset + chunk.byteLength
    ) as ArrayBuffer;

    const res = await fetch(uploadLink, {
      method: "PATCH",
      headers: {
        "Tus-Resumable": "1.0.0",
        "Upload-Offset": String(offset),
        "Content-Type": "application/offset+octet-stream",
        "Content-Length": String(chunk.length),
      },
      body,
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Vimeo TUS upload failed (${res.status}): ${text}`);
    }

    const newOffset = res.headers.get("Upload-Offset");
    offset = newOffset ? Number(newOffset) : end;

    if (offset >= totalSize) break;
  }
}
