import { useWorkspace } from "../context/WorkspaceContext";
export default function Header({ title, onMenu }) {
  const { projects, selectedProject, selectProject, projectsLoading } = useWorkspace();
  return <header className="cth-header">
    <div className="cth-breadcrumb"><button className="cth-menu-toggle" onClick={onMenu} aria-label="Buka navigasi">☰</button><span>Dashboard</span><span>/</span><strong>{title}</strong></div>
    <label className="cth-project-selector"><span>Proyek aktif</span>
      <select aria-label="Pilih proyek aktif" value={selectedProject?.id ?? ""}
        onChange={event => selectProject(event.target.value)} disabled={projectsLoading}>
        <option value="">{projectsLoading ? "Memuat proyek..." : "Pilih proyek"}</option>
        {projects.map(project => <option value={project.id} key={project.id}>{project.name}</option>)}
      </select>
    </label>
  </header>;
}
