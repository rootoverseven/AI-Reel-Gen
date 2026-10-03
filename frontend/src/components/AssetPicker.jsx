import { useState } from 'react';
import { Check, Film, Loader2, Plus } from 'lucide-react';
import { LIBRARY, uploadAsset, errorMessage } from '../lib/api';

function VideoThumb({ url, name }) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return (
      <div className="w-full h-full flex items-center justify-center">
        <Film className="w-5 h-5 text-zinc-500" aria-hidden="true" />
      </div>
    );
  }
  return (
    <video
      src={`${url}#t=0.1`}
      muted
      preload="metadata"
      playsInline
      aria-label={name}
      onError={() => setFailed(true)}
      className="w-full h-full object-cover pointer-events-none"
    />
  );
}

function AssetPicker({ kind, title, items, selected, onSelect, onUploaded, media }) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const cfg = LIBRARY[kind];

  const handleFile = async (e) => {
    const input = e.target;
    const file = input.files?.[0];
    input.value = ''; // allow choosing the same file again
    if (!file) return;
    setError('');
    if (file.size > cfg.maxBytes) {
      setError(`File too large (max ${Math.round(cfg.maxBytes / (1024 * 1024))} MB)`);
      return;
    }
    setUploading(true);
    try {
      const res = await uploadAsset(kind, file);
      onUploaded(res.data.name);
    } catch (err) {
      setError(errorMessage(err, 'Upload failed. Please try again.'));
    } finally {
      setUploading(false);
    }
  };

  const aspect = media === 'video' ? 'aspect-[9/16]' : 'aspect-square';

  return (
    <div>
      {title && <h3 className="mb-2 text-xs text-zinc-400">{title}</h3>}
      <div className="grid grid-cols-[repeat(auto-fill,minmax(5rem,1fr))] gap-2">
        {items.map((item) => {
          const isSelected = selected === item.name;
          return (
            <button
              key={item.name}
              type="button"
              aria-pressed={isSelected}
              onClick={() => onSelect(item.name)}
              title={item.name}
              className={`relative text-left rounded-lg border bg-zinc-900 overflow-hidden transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 ${
                isSelected ? 'border-violet-500 ring-1 ring-violet-500' : 'border-zinc-800 hover:border-zinc-600'
              }`}
            >
              <div className={`${aspect} bg-black/60 flex items-center justify-center`}>
                {media === 'video' ? (
                  <VideoThumb url={item.url} name={item.name} />
                ) : (
                  <img src={item.url} alt={item.name} loading="lazy" className="w-full h-full object-contain" />
                )}
              </div>
              {isSelected && (
                <span className="absolute right-1 top-1 flex h-4 w-4 items-center justify-center rounded-full bg-violet-500 text-white">
                  <Check className="h-3 w-3" aria-hidden="true" />
                </span>
              )}
              <div className="px-2 py-1 text-xs text-zinc-300 truncate">{item.name}</div>
            </button>
          );
        })}

        {uploading ? (
          <div
            className={`${aspect} rounded-lg border border-dashed border-violet-500 flex flex-col items-center justify-center gap-1 text-xs text-zinc-200`}
            role="status"
          >
            <Loader2 className="w-5 h-5 animate-spin text-violet-400" aria-hidden="true" />
            Uploading
          </div>
        ) : (
          <label
            title={cfg.hint}
            className={`${aspect} rounded-lg border border-dashed border-zinc-700 text-zinc-400 flex flex-col items-center justify-center gap-1 text-xs cursor-pointer transition-colors hover:border-zinc-500 hover:text-zinc-100 focus-within:ring-2 focus-within:ring-violet-500`}
          >
            <Plus className="w-5 h-5" aria-hidden="true" />
            Upload
            <input type="file" accept={cfg.accept} onChange={handleFile} className="sr-only" />
          </label>
        )}
      </div>

      {items.length === 0 && <p className="mt-2 text-sm text-zinc-400">Nothing here yet. Upload a file to get started.</p>}
      {error && (
        <p role="alert" className="mt-2 text-sm text-red-400">
          {error}
        </p>
      )}
    </div>
  );
}

export default AssetPicker;
