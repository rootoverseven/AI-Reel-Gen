import axios from 'axios';

export const LIBRARY = {
  backgrounds: {
    accept: '.mp4,.mov,.webm,video/mp4,video/quicktime,video/webm',
    maxBytes: 200 * 1024 * 1024,
    hint: 'MP4 / MOV / WebM, up to 200 MB',
  },
  characters: {
    accept: '.png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp',
    maxBytes: 15 * 1024 * 1024,
    hint: 'PNG / JPG / WebP, up to 15 MB (transparent PNG recommended)',
  },
};

export function fetchLibrary(kind, signal) {
  return axios.get(`/library/${kind}`, { signal });
}

// Do not set Content-Type by hand: the browser adds the multipart boundary.
export function uploadAsset(kind, file, onUploadProgress) {
  const form = new FormData();
  form.append('file', file);
  return axios.post(`/library/${kind}`, form, { onUploadProgress });
}

export function errorMessage(err, fallback) {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string' && detail) return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const msgs = detail.map((d) => d?.msg).filter(Boolean);
    if (msgs.length > 0) return msgs.join('; ');
  }
  if (err?.response?.status === 413) return 'File too large';
  return fallback;
}

export function pickDefault(items, preferredName) {
  if (items.some((i) => i.name === preferredName)) return preferredName;
  return items[0]?.name ?? '';
}
