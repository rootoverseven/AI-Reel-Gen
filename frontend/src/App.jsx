import { useState, useEffect } from 'react';
import axios from 'axios';
import { Wand2, Loader2, ChevronDown } from 'lucide-react';
import AssetPicker from './components/AssetPicker';
import ReelPreview from './components/ReelPreview';
import { LIBRARY, fetchLibrary, errorMessage, pickDefault } from './lib/api';

const BUSY_VIDEO_STATUS = 'Synthesizing audio and rendering video. This can take a few minutes.';

const FIELD =
  'w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-400 outline-none transition-colors hover:border-zinc-700 focus-visible:border-violet-500 focus-visible:ring-1 focus-visible:ring-violet-500';

function Section({ title, hint, children }) {
  return (
    <section className="py-6 first:pt-0 border-t border-zinc-800 first:border-t-0">
      <div className="flex items-baseline justify-between gap-4 mb-3">
        <h2 className="text-sm font-semibold text-zinc-100">{title}</h2>
        {hint && <p className="text-xs text-zinc-400 text-right">{hint}</p>}
      </div>
      {children}
    </section>
  );
}

function ErrorText({ children }) {
  return children ? <p role="alert" className="mt-2 text-sm text-red-400">{children}</p> : null;
}

function defaultVoiceId(voices, name) {
  return voices.find((v) => v.name === name)?.id ?? voices[0]?.id ?? '';
}

function App() {
  const [topic, setTopic] = useState('');
  const [script, setScript] = useState('');
  const [scriptBusy, setScriptBusy] = useState(false);
  const [scriptError, setScriptError] = useState('');
  const [videoBusy, setVideoBusy] = useState(false);
  const [videoUrl, setVideoUrl] = useState('');
  const [videoError, setVideoError] = useState('');

  const [voices, setVoices] = useState([]);
  const [savitaVoice, setSavitaVoice] = useState('');
  const [surajVoice, setSurajVoice] = useState('');
  const [voicesError, setVoicesError] = useState('');

  const [backgrounds, setBackgrounds] = useState([]);
  const [characters, setCharacters] = useState([]);
  const [background, setBackground] = useState('');
  const [savitaImg, setSavitaImg] = useState('');
  const [surajImg, setSurajImg] = useState('');
  const [libraryError, setLibraryError] = useState('');

  // Voices: fetch once on mount.
  useEffect(() => {
    const controller = new AbortController();
    axios.get('/voices', { signal: controller.signal })
      .then((res) => {
        const list = res.data;
        setVoices(list);
        setVoicesError('');
        setSavitaVoice((prev) => prev || defaultVoiceId(list, 'Savita'));
        setSurajVoice((prev) => prev || defaultVoiceId(list, 'Suraj'));
      })
      .catch((err) => {
        if (axios.isCancel(err)) return;
        setVoicesError(errorMessage(err, 'Could not load voices.'));
      });
    return () => controller.abort();
  }, []);

  // Library: fetch once on mount. Defaults only apply when the selection is empty or gone.
  useEffect(() => {
    const controller = new AbortController();
    const keepOr = (preferred, list) => (prev) =>
      prev && list.some((i) => i.name === prev) ? prev : pickDefault(list, preferred);

    Promise.all([
      fetchLibrary('backgrounds', controller.signal),
      fetchLibrary('characters', controller.signal),
    ])
      .then(([bgRes, chRes]) => {
        setBackgrounds(bgRes.data);
        setCharacters(chRes.data);
        setLibraryError('');
        setBackground(keepOr('tech_bg.mp4', bgRes.data));
        setSavitaImg(keepOr('savita.png', chRes.data));
        setSurajImg(keepOr('suraj.png', chRes.data));
      })
      .catch((err) => {
        if (axios.isCancel(err)) return;
        setLibraryError(errorMessage(err, 'Could not load the asset library.'));
      });
    return () => controller.abort();
  }, []);

  // After an upload: refetch the list, then select the stored (possibly renamed) file.
  const handleUploaded = (kind, name, select) => {
    fetchLibrary(kind)
      .then((res) => {
        if (kind === 'backgrounds') setBackgrounds(res.data);
        else setCharacters(res.data);
        select(name);
        setLibraryError('');
      })
      .catch((err) => setLibraryError(errorMessage(err, 'Uploaded, but could not refresh the library.')));
  };

  const generateScript = async () => {
    if (!topic.trim() || scriptBusy) return;
    setScriptBusy(true);
    setScriptError('');
    try {
      const res = await axios.post('/generate-script', { topic });
      setScript(res.data.script);
    } catch (err) {
      setScriptError(errorMessage(err, 'Could not generate a script. Please try again.'));
    } finally {
      setScriptBusy(false);
    }
  };

  const canGenerate =
    script.trim() !== '' &&
    savitaVoice !== '' &&
    surajVoice !== '' &&
    background !== '' &&
    savitaImg !== '' &&
    surajImg !== '' &&
    !scriptBusy &&
    !videoBusy;

  const generateVideo = async () => {
    if (!canGenerate) return;
    setVideoBusy(true);
    setVideoUrl('');
    setVideoError('');
    try {
      // No axios timeout: generation can take several minutes.
      const res = await axios.post('/generate-video', {
        script,
        savita_voice_id: savitaVoice,
        suraj_voice_id: surajVoice,
        background,
        savita_img: savitaImg,
        suraj_img: surajImg,
      });
      setVideoUrl(res.data.video_url);
    } catch (err) {
      if (err?.response?.status === 409) {
        setVideoError('Another reel is already being generated. Please try again when it finishes.');
      } else {
        setVideoError(errorMessage(err, 'Could not generate the video. Please try again.'));
      }
    } finally {
      setVideoBusy(false);
    }
  };

  const voiceSelect = (label, value, onChange) => (
    <div>
      <label className="block text-xs text-zinc-400 mb-1.5">{label}</label>
      <div className="relative">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={`${FIELD} appearance-none pr-9 cursor-pointer`}
        >
          {voices.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
        </select>
        <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" aria-hidden="true" />
      </div>
    </div>
  );

  const hintWhenDisabled = !script.trim() ? 'Add a script to continue.' : '';

  return (
    <div className="min-h-screen font-sans selection:bg-violet-500 selection:text-white">
      <header className="border-b border-zinc-800">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 h-12 flex items-center">
          <h1 className="text-base font-semibold tracking-tight">ReelGen</h1>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-8 grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_18rem] gap-10 items-start">
        <div>
          <Section title="Script" hint="One line per speaker: Savita: ... / Suraj: ...">
            <div className="flex gap-2 mb-3">
              <input
                type="text"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') generateScript(); }}
                placeholder="Or describe a topic and let AI draft it"
                aria-label="Topic"
                className={`${FIELD} flex-1 min-w-0`}
              />
              <button
                type="button"
                onClick={generateScript}
                disabled={scriptBusy || !topic.trim()}
                className="shrink-0 inline-flex items-center gap-2 rounded-lg border border-zinc-700 px-3 py-2 text-sm font-medium text-zinc-100 transition-colors hover:bg-zinc-800 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-transparent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500"
              >
                {scriptBusy ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> : <Wand2 className="w-4 h-4" aria-hidden="true" />}
                Draft script
              </button>
            </div>
            <textarea
              value={script}
              onChange={(e) => setScript(e.target.value)}
              placeholder={'Suraj: ...\nSavita: ...'}
              aria-label="Script"
              rows={9}
              className={`${FIELD} leading-relaxed resize-y min-h-40`}
            ></textarea>
            <ErrorText>{scriptError}</ErrorText>
          </Section>

          <Section title="Voices">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {voiceSelect('Savita', savitaVoice, setSavitaVoice)}
              {voiceSelect('Suraj', surajVoice, setSurajVoice)}
            </div>
            <ErrorText>{voicesError}</ErrorText>
          </Section>

          <Section title="Background" hint={LIBRARY.backgrounds.hint}>
            <AssetPicker
              kind="backgrounds"
              media="video"
              items={backgrounds}
              selected={background}
              onSelect={setBackground}
              onUploaded={(name) => handleUploaded('backgrounds', name, setBackground)}
            />
            <ErrorText>{libraryError}</ErrorText>
          </Section>

          <Section title="Characters" hint={LIBRARY.characters.hint}>
            <div className="space-y-5">
              <AssetPicker
                kind="characters"
                media="image"
                title="Savita"
                items={characters}
                selected={savitaImg}
                onSelect={setSavitaImg}
                onUploaded={(name) => handleUploaded('characters', name, setSavitaImg)}
              />
              <AssetPicker
                kind="characters"
                media="image"
                title="Suraj"
                items={characters}
                selected={surajImg}
                onSelect={setSurajImg}
                onUploaded={(name) => handleUploaded('characters', name, setSurajImg)}
              />
            </div>
          </Section>
        </div>

        <aside className="lg:sticky lg:top-8 space-y-3">
          <ReelPreview videoUrl={videoUrl} loading={videoBusy} status={BUSY_VIDEO_STATUS} />
          <button
            type="button"
            onClick={generateVideo}
            disabled={!canGenerate}
            className={`w-full inline-flex items-center justify-center gap-2 rounded-lg px-4 py-3 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-400 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950 ${
              canGenerate || videoBusy
                ? 'bg-violet-600 text-white hover:bg-violet-500'
                : 'bg-zinc-800 text-zinc-400 cursor-not-allowed'
            }`}
          >
            {videoBusy ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> : <Wand2 className="w-4 h-4" aria-hidden="true" />}
            {videoBusy ? 'Generating...' : 'Generate reel'}
          </button>
          <div className="min-h-5 text-sm">
            {!videoBusy && !videoError && hintWhenDisabled && <p className="text-zinc-400">{hintWhenDisabled}</p>}
            <ErrorText>{videoError}</ErrorText>
          </div>
        </aside>
      </main>
    </div>
  );
}

export default App;
