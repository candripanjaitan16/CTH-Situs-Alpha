import Icon from "./Icon";
export function Badge({ children, tone = "neutral" }) { return <span className={`cth-badge ${tone}`}>{children}</span>; }
export function PageTitle({ title, description, action }) { return <div className="cth-page-title"><div><h1>{title}</h1><p>{description}</p></div>{action}</div>; }
export function Notice({ children, tone = "info" }) { return <div className={`cth-notice ${tone}`} role={tone === "error" ? "alert" : "status"}>{children}</div>; }
export function Empty({ icon = "drive", title, children }) { return <div className="cth-empty"><div className="cth-empty-icon"><Icon name={icon} /></div><h3>{title}</h3><p>{children}</p></div>; }
export function ConnectionCard({ title, description, status = "unavailable", message }) {
  const states = {
    loading: ["Memeriksa koneksi...", "info", "clock"],
    connected: ["Terhubung", "success", "check"],
    disconnected: ["Belum terhubung", "neutral", "clock"],
    error: ["Gagal memeriksa koneksi", "warning", "clock"],
    unavailable: ["Integrasi belum dibuat", "neutral", "colab"],
  };
  const [label, tone, icon] = states[status] || states.error;
  return <section className="cth-card cth-connection"><div className={`cth-connection-icon ${tone}`}><Icon name={icon} /></div><div><h3>{title}</h3><p className={`cth-status-text ${tone}`} role="status">{message || label}</p><small>{description}</small></div></section>;
}
