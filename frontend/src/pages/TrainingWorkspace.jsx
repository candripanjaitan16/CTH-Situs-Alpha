import { useState } from "react";
import { useWorkspace } from "../context/WorkspaceContext";
import NeuralCanvas from "../components/NeuralCanvas";
import { Badge, Notice, PageTitle } from "../components/UI";
export default function TrainingWorkspace() {
  const { selectedProject, sources } = useWorkspace();
  const [preview, setPreview] = useState(false);
  return <>
    <PageTitle title="Training Workspace" description="Pantau proses belajar model melalui visual jaringan saraf." action={<Badge tone="neutral">Runtime belum terhubung</Badge>} />
    <div className="cth-grid training-layout"><section className="cth-card cth-visual-card"><div className="cth-card-heading"><h2>Neural Activity</h2><Badge tone={preview ? "info" : "neutral"}>{preview ? "Demo visual" : "Diam"}</Badge></div><NeuralCanvas active={preview} /><div className="cth-visual-footer"><p>{preview ? "Animasi demonstrasi saja. Tidak ada model yang sedang dilatih." : "Jalur saraf diam. Belum ada proses training."}</p><button className="cth-button" onClick={() => setPreview(!preview)}>{preview ? "Hentikan pratinjau" : "Pratinjau animasi"}</button></div></section>
    <section className="cth-card"><h2>Training Session</h2><dl className="cth-details"><dt>Proyek</dt><dd>{selectedProject?.name || "Belum dipilih"}</dd><dt>Model</dt><dd>{selectedProject?.model_name || "Belum ditentukan"}</dd><dt>Sumber lokal</dt><dd>{sources.length} · belum diunggah</dd><dt>Runtime Colab</dt><dd>Belum terintegrasi</dd><dt>Epoch / Loss</dt><dd>— / —</dd><dt>Status training</dt><dd>Belum tersedia</dd></dl><button className="cth-button primary" disabled>Mulai training</button><p className="cth-muted">Aktif setelah dataset tersimpan, runtime terverifikasi, dan endpoint training dibuat.</p></section></div>
    <Notice>Animasi ini ringan dan berhenti ketika pratinjau dimatikan. Nantinya status training sebenarnya yang mengatur animasi, bukan tombol demo.</Notice>
  </>;
}
