import { Download, Loader2 } from 'lucide-react';

function ReelPreview({ videoUrl, loading, status }) {
  const filename = videoUrl ? videoUrl.split('/').pop() || 'reel.mp4' : 'reel.mp4';

  return (
    <div>
      <div className="relative aspect-[9/16] w-full overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900">
        {videoUrl ? (
          <video
            key={videoUrl}
            src={videoUrl}
            controls
            playsInline
            className="h-full w-full bg-black object-contain"
          />
        ) : (
          <div className="flex h-full items-center justify-center p-6 text-center text-sm text-zinc-400">
            Your reel will appear here
          </div>
        )}

        {loading && (
          <div
            className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-zinc-950/90 p-6 text-center"
            role="status"
            aria-live="polite"
          >
            <Loader2 className="h-6 w-6 animate-spin text-violet-400" aria-hidden="true" />
            <p className="text-sm text-zinc-200">{status}</p>
          </div>
        )}
      </div>

      {videoUrl && (
        <a
          href={videoUrl}
          download={filename}
          className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-zinc-700 px-4 py-2 text-sm font-medium text-zinc-100 transition-colors hover:bg-zinc-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500"
        >
          <Download className="h-4 w-4" aria-hidden="true" /> Download
        </a>
      )}
    </div>
  );
}

export default ReelPreview;
