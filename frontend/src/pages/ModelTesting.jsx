import { useEffect, useRef, useState } from "react";
import { useWorkspace } from "../context/WorkspaceContext";
import { Badge, Empty, Notice, PageTitle } from "../components/UI";
const DEMO_REPLY = "Ini contoh efek balasan bertahap di CTH. Belum ada model atau runtime Colab yang menjalankan inferensi. Setelah integrasi tersedia, jawaban asli akan diterima dari backend.";
export default function ModelTesting() {
  const { selectedProject } = useWorkspace();
  const [reply, setReply] = useState("");
  const [typing, setTyping] = useState(false);
  const [notice, setNotice] = useState("");
  const timer = useRef(null);
  useEffect(() => () => window.clearInterval(timer.current), []);
  function previewReply() {
    window.clearInterval(timer.current); setReply(""); setTyping(true);
    let length = 0;
    timer.current = window.setInterval(() => {
      length += 4; setReply(DEMO_REPLY.slice(0, length));
      if (length >= DEMO_REPLY.length) { window.clearInterval(timer.current); setTyping(false); }
    }, 35);
  }
  return <>
    <PageTitle title="Model Testing" description="Ruang percakapan dan ekspor model hasil pelatihan." action={<Badge tone="warning">Antarmuka · belum ada inferensi</Badge>} />
    <div className="cth-grid testing-layout"><section className="cth-card cth-chat"><div className="cth-card-heading"><div><h2>{selectedProject?.model_name || "Pilih model proyek"}</h2><small>{selectedProject?.name || "Belum ada proyek aktif"}</small></div><Badge>Colab belum terhubung</Badge></div>
      <div className="cth-chat-body" aria-live="polite">{reply ? <div className="cth-chat-message"><span className="cth-chat-avatar">CT</span><div><strong>Demo antarmuka</strong><p>{reply}{typing && <span className="cth-typing-cursor">▍</span>}</p></div></div> : <Empty icon="testing" title="Workspace percakapan siap">Belum ada model aktif. Pratinjau efek balasan tersedia tanpa mengirim data.</Empty>}</div>
      <div className="cth-chat-compose"><textarea aria-label="Pesan untuk model" placeholder="Chat aktif setelah model dan runtime Colab terhubung." disabled rows={2} /><button className="cth-button primary" disabled>Kirim ↑</button></div>
    </section><section className="cth-card"><h2>Kontrol model</h2><dl className="cth-details"><dt>Runtime</dt><dd>Belum diverifikasi</dd><dt>Model aktif</dt><dd>Belum dimuat</dd><dt>Format ekspor</dt><dd>GGUF</dd></dl><div className="cth-stack"><button className="cth-button" disabled>Jalankan model di Colab</button><button className="cth-button" onClick={previewReply} disabled={typing}>Pratinjau efek balasan</button><button className="cth-button primary" onClick={() => setNotice("Ekspor belum tersedia: integrasi runtime Colab dan endpoint konversi GGUF belum dibuat. Belum ada berkas yang diproses.")}>Buat model untuk diunduh</button></div><p className="cth-muted">Tombol ekspor saat ini hanya menjelaskan prasyarat. Tidak membuat unduhan palsu.</p></section></div>
    {notice && <Notice tone="warning">{notice}</Notice>}
    <Notice>Konfirmasi ekspor nanti menampilkan proyek, model, dan dataset yang dipakai. Fine-tuning memakai data pilihanmu; model dasar tetap membawa pengetahuan pelatihan sebelumnya.</Notice>
  </>;
}
