import { useState, useEffect } from 'react';
import axios from 'axios';
import { Play, Download, Wand2, Loader2, Mic } from 'lucide-react';

function App() {
  const [topic, setTopic] = useState('');
  const [script, setScript] = useState('');
  const [loading, setLoading] = useState(false);
  const [videoPath, setVideoPath] = useState('');
  const [voices, setVoices] = useState([]);
  const [savitaVoice, setSavitaVoice] = useState('');
  const [surajVoice, setSurajVoice] = useState('');
  const [status, setStatus] = useState('');

  useEffect(() => {
    // Fetch available voices on mount
    axios.get('/voices')
      .then(res => {
        setVoices(res.data);
        if (res.data.length > 0) {
          setSavitaVoice(res.data[0].id);
          setSurajVoice(res.data[0].id);
        }
      })
      .catch(err => console.error("Failed to load voices", err));
  }, []);

  const generateScript = async () => {
    if (!topic) return;
    setLoading(true);
    setStatus('Generating script...');
    try {
      const res = await axios.post('/generate-script', { topic });
      setScript(res.data.script);
    } catch (err) {
      alert("Error generating script");
      console.error(err);
    } finally {
      setLoading(false);
      setStatus('');
    }
  };

  const generateVideo = async () => {
    if (!script) return;
    setLoading(true);
    setStatus('Synthesizing Audio & Rendering Video (This may take a minute)...');
    try {
      const res = await axios.post('/generate-video', {
        script,
        savita_voice_id: savitaVoice,
        suraj_voice_id: surajVoice,
        savita_img: "savita.png",
        suraj_img: "suraj.png"
      });
      // The backend returns a local path. Since we are local, we can't easily serve it 
      // without the backend serving static files. 
      // For MVP, we just show the path.
      setVideoPath(res.data.video_path);
      alert(`Video Generated Successfully at: ${res.data.video_path}`);
    } catch (err) {
      alert("Error generating video");
      console.error(err);
    } finally {
      setLoading(false);
      setStatus('');
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white font-sans selection:bg-purple-500 selection:text-white">
      {/* Navbar */}
      <nav className="border-b border-gray-800 bg-gray-950/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-tr from-purple-500 to-pink-500 rounded-lg flex items-center justify-center">
              <Play className="w-4 h-4 text-white fill-current" />
            </div>
            <span className="font-bold text-xl tracking-tight">ReelGen.ai</span>
          </div>
          <div className="text-sm text-gray-400">v1.0.0 (SaaS MVP)</div>
        </div>
      </nav>

      <main className="max-w-5xl mx-auto px-6 py-12">
        {/* Hero */}
        <div className="text-center mb-12">
          <h1 className="text-5xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-purple-400 via-pink-400 to-purple-400 mb-4 animate-gradient-x">
            Create Viral Reels in Seconds
          </h1>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto">
            Turn any topic into an engaging 2-person dialogue video. AI-powered scripting, voice cloning, and editing.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">

          {/* Left Column: Controls */}
          <div className="space-y-8">

            {/* Step 1: Topic */}
            <div className="bg-gray-800/50 border border-gray-700 p-6 rounded-2xl shadow-xl backdrop-blur-sm">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-8 h-8 rounded-full bg-purple-500/20 text-purple-400 flex items-center justify-center font-bold">1</div>
                <h2 className="text-xl font-semibold">Topic to Script</h2>
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="E.g. Explain React Hooks vs Classes..."
                  className="flex-1 bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 focus:ring-2 focus:ring-purple-500 outline-none transition-all placeholder:text-gray-600"
                />
                <button
                  onClick={generateScript}
                  disabled={loading || !topic}
                  className="bg-purple-600 hover:bg-purple-500 text-white px-6 py-3 rounded-xl font-medium transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transform active:scale-95"
                >
                  {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Wand2 className="w-5 h-5" />}
                </button>
              </div>
            </div>

            {/* Step 2: Script Editor */}
            <div className="bg-gray-800/50 border border-gray-700 p-6 rounded-2xl shadow-xl backdrop-blur-sm">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-8 h-8 rounded-full bg-purple-500/20 text-purple-400 flex items-center justify-center font-bold">2</div>
                <h2 className="text-xl font-semibold">Review Script</h2>
              </div>
              <textarea
                value={script}
                onChange={(e) => setScript(e.target.value)}
                placeholder="Script will appear here..."
                className="w-full h-48 bg-gray-900 border border-gray-700 rounded-xl p-4 focus:ring-2 focus:ring-purple-500 outline-none transition-all font-mono text-sm leading-relaxed resize-none"
              ></textarea>
            </div>

            {/* Step 3: Configuration */}
            <div className="bg-gray-800/50 border border-gray-700 p-6 rounded-2xl shadow-xl backdrop-blur-sm">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-8 h-8 rounded-full bg-purple-500/20 text-purple-400 flex items-center justify-center font-bold">3</div>
                <h2 className="text-xl font-semibold">Voice Configuration</h2>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-2">Savita's Voice</label>
                  <div className="relative">
                    <Mic className="absolute left-3 top-3 w-4 h-4 text-gray-500" />
                    <select
                      value={savitaVoice}
                      onChange={(e) => setSavitaVoice(e.target.value)}
                      className="w-full bg-gray-900 border border-gray-700 rounded-xl py-2.5 pl-10 pr-4 appearance-none outline-none focus:border-purple-500 transition-colors"
                    >
                      {voices.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-2">Suraj's Voice</label>
                  <div className="relative">
                    <Mic className="absolute left-3 top-3 w-4 h-4 text-gray-500" />
                    <select
                      value={surajVoice}
                      onChange={(e) => setSurajVoice(e.target.value)}
                      className="w-full bg-gray-900 border border-gray-700 rounded-xl py-2.5 pl-10 pr-4 appearance-none outline-none focus:border-purple-500 transition-colors"
                    >
                      {voices.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}
                    </select>
                  </div>
                </div>
              </div>
            </div>

          </div>

          {/* Right Column: Preview / Generate */}
          <div className="space-y-8">
            <div className="sticky top-24">
              <div className="bg-gradient-to-br from-gray-800 to-gray-900 border border-gray-700 rounded-3xl p-2 shadow-2xl overflow-hidden aspect-[9/16] max-w-sm mx-auto flex flex-col relative">

                {/* Visualizer / Placeholder */}
                <div className="flex-1 bg-black rounded-2xl flex flex-col items-center justify-center relative overflow-hidden group">
                  {videoPath ? (
                    <div className="text-center p-8">
                      <div className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-4 animate-bounce">
                        <Play className="w-8 h-8 text-black ml-1" />
                      </div>
                      <h3 className="text-2xl font-bold text-white mb-2">Ready to Watch</h3>
                      <p className="text-gray-400 text-sm mb-6 break-all">{videoPath}</p>
                      <button className="bg-white text-black px-6 py-2 rounded-full font-bold hover:bg-gray-200 transition-colors flex items-center gap-2 mx-auto">
                        <Download className="w-4 h-4" /> Download
                      </button>
                    </div>
                  ) : (
                    <>
                      <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=2564&auto=format&fit=crop')] opacity-20 bg-cover bg-center"></div>
                      <Play className="w-16 h-16 text-white/10 group-hover:text-purple-500/50 transition-colors duration-500" />
                      <p className="mt-4 text-gray-500 text-sm">Preview will appear here</p>
                    </>
                  )}

                  {loading && (
                    <div className="absolute inset-0 bg-black/80 backdrop-blur-sm flex flex-col items-center justify-center z-20">
                      <Loader2 className="w-12 h-12 text-purple-500 animate-spin mb-4" />
                      <p className="text-purple-300 font-medium animate-pulse">{status}</p>
                    </div>
                  )}
                </div>

                {/* Generate Button */}
                <div className="p-4">
                  <button
                    onClick={generateVideo}
                    disabled={loading || !script}
                    className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white font-bold py-4 rounded-xl shadow-lg transition-all transform active:scale-95 disabled:opacity-50 disabled:grayscale flex items-center justify-center gap-3 text-lg"
                  >
                    {loading ? 'Processing...' : (
                      <>
                        <Wand2 className="w-6 h-6" /> Generate Reel
                      </>
                    )}
                  </button>
                </div>

              </div>
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}

export default App;
