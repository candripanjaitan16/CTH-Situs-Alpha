import { useWorkspace } from "../context/WorkspaceContext";
import Icon from "../components/Icon";
import { Badge, ConnectionCard, Empty, Notice, PageTitle } from "../components/UI";
export default function Beranda({ onNavigate }) {
  const { drive, projects, projectsLoading, projectsError, selectedProject, selectProject } = useWorkspace();
  return <>
    <PageTitle title={<>Welcome to<br />ChanThecno Training Hub</>} description="Manage your datasets, organize training projects, and monitor your AI workspace." action={<button className="cth-button primary" onClick={() => onNavigate("drive")}>Buka proyek <span>↗</span></button>} />
    <div className="cth-grid two"><ConnectionCard title="Google Drive" description="Project storage" {...drive} /><ConnectionCard title="Google Colab" description="Training runtime" /></div>
    <div className="cth-grid three cth-section-gap">{[
      ["drive", projectsLoading || projectsError ? "—" : projects.length, "Total Projects", "Data dari backend"],
      ["datasets", "—", "Total Datasets", "Integrasi dataset belum dibuat"],
      ["model", "—", "Trained Models", "Integrasi training belum dibuat"],
    ].map(([icon, count, label, note]) => <section className="cth-card cth-stat" key={label}><div className="cth-stat-icon"><Icon name={icon} /></div><div><strong>{count}</strong><p>{label}</p><small>{note}</small></div></section>)}</div>
    <div className="cth-grid two cth-section-gap">
      <section className="cth-card"><div className="cth-card-heading"><h2>Training Performance</h2><Badge>Belum tersedia</Badge></div><Empty icon="activity" title="Belum ada data pelatihan">Grafik akan mengikuti hasil training yang dikirim runtime Colab.</Empty></section>
      <section className="cth-card"><div className="cth-card-heading"><h2>Recent Projects</h2><button className="cth-text-button" onClick={() => onNavigate("drive")}>View All →</button></div>
        {projectsLoading ? <Empty title="Memuat proyek..." /> : projectsError ? <Notice tone="error">{projectsError}</Notice> : projects.length === 0 ? <Empty title="Belum ada proyek">Buat proyek pertama melalui Google Drive.</Empty> : <div className="cth-project-list">{projects.slice(0, 4).map(project => <button key={project.id} onClick={() => { selectProject(project.id); onNavigate("drive"); }}><span className="cth-folder-icon"><Icon name="drive" /></span><span><strong>{project.name}</strong><small>{project.model_name || "Model belum ditentukan"}</small></span><span>{selectedProject?.id === project.id ? "Aktif" : "→"}</span></button>)}</div>}
      </section>
    </div>
  </>;
}
