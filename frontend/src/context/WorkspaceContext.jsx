import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { getDriveStatus, getProjects, createProject } from "../services/api";

const WorkspaceContext = createContext(null);
function savedProject() {
  try { return localStorage.getItem("cth-selected-project") || ""; } catch { return ""; }
}
function readableError(error) {
  return error.name === "AbortError" ? "Pemeriksaan melewati batas waktu. Coba lagi." : error.message;
}
export function WorkspaceProvider({ children }) {
  const [projects, setProjects] = useState([]);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [projectsError, setProjectsError] = useState("");
  const [selectedId, setSelectedId] = useState(savedProject);
  const [drive, setDrive] = useState({ status: "loading", message: "Memeriksa koneksi..." });
  const [drafts, setDrafts] = useState({});
  const projectsRequest = useRef(null);
  const driveRequest = useRef(null);
  const creating = useRef(false);
  const [isCreating, setIsCreating] = useState(false);

  const selectProject = useCallback((id) => {
    const value = String(id || "");
    setSelectedId(value);
    try {
      if (value) localStorage.setItem("cth-selected-project", value);
      else localStorage.removeItem("cth-selected-project");
    } catch { /* Pemilihan tetap bekerja jika storage browser diblokir. */ }
  }, []);

  const refreshProjects = useCallback(async () => {
    projectsRequest.current?.abort();
    const controller = new AbortController();
    projectsRequest.current = controller;
    setProjectsLoading(true);
    setProjectsError("");
    try {
      const data = await getProjects(controller.signal);
      if (!controller.signal.aborted) setProjects(data);
      return data;
    } catch (error) {
      if (!controller.signal.aborted) setProjectsError(readableError(error));
      return null;
    } finally {
      if (!controller.signal.aborted) setProjectsLoading(false);
    }
  }, []);

  const refreshDrive = useCallback(async () => {
    driveRequest.current?.abort();
    const controller = new AbortController();
    driveRequest.current = controller;
    setDrive({ status: "loading", message: "Memeriksa koneksi..." });
    try {
      const data = await getDriveStatus(controller.signal);
      if (!controller.signal.aborted) setDrive(data);
    } catch (error) {
      if (!controller.signal.aborted) setDrive({ status: "error", message: readableError(error) });
    }
  }, []);

  useEffect(() => {
    refreshProjects();
    refreshDrive();
    return () => { projectsRequest.current?.abort(); driveRequest.current?.abort(); };
  }, [refreshProjects, refreshDrive]);

  useEffect(() => {
    if (!Object.values(drafts).some(items => items.length > 0)) return;
    const warnUnsaved = event => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warnUnsaved);
    return () => window.removeEventListener("beforeunload", warnUnsaved);
  }, [drafts]);

  const addProject = useCallback(async (values) => {
    if (creating.current) throw new Error("Pembuatan proyek masih berjalan.");
    creating.current = true;
    setIsCreating(true);
    try {
      const result = await createProject(values);
      if (result.status !== "success" || result.project_id == null) throw new Error("Respons pembuatan proyek belum dapat dipastikan. Muat ulang daftar sebelum mencoba lagi.");
      selectProject(result.project_id);
      const data = await refreshProjects();
      return { result, listUpdated: data !== null };
    } catch (error) {
      throw new Error(`${readableError(error)} Periksa daftar proyek sebelum mengirim ulang; folder mungkin sudah dibuat oleh backend.`);
    } finally { creating.current = false; setIsCreating(false); }
  }, [refreshProjects, selectProject]);

  const selectedProject = projects.find(p => String(p.id) === selectedId) || null;
  const sources = selectedProject ? drafts[String(selectedProject.id)] || [] : [];
  const addSource = (projectId, source) => setDrafts(previous => ({
    ...previous, [projectId]: [...(previous[projectId] || []), source],
  }));
  const removeSource = (projectId, sourceId) => setDrafts(previous => ({
    ...previous, [projectId]: (previous[projectId] || []).filter(s => s.id !== sourceId),
  }));

  return <WorkspaceContext.Provider value={{ projects, projectsLoading, projectsError,
    selectedProject, selectProject, refreshProjects, drive, refreshDrive, addProject,
    isCreating, sources, drafts, addSource, removeSource }}>{children}</WorkspaceContext.Provider>;
}
export function useWorkspace() {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("WorkspaceProvider belum dipasang.");
  return value;
}
