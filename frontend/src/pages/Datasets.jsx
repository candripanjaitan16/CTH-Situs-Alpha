import { useRef, useState } from "react";
import { useWorkspace } from "../context/WorkspaceContext";
import { Badge, Empty, Notice, PageTitle } from "../components/UI";

function sourceId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function formatSize(bytes) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function Datasets({ onNavigate }) {
  const { selectedProject, sources, addSource, removeSource } = useWorkspace();

  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const [reading, setReading] = useState(false);
  const [preview, setPreview] = useState("");

  const busy = useRef(false);

  const previewSource = sources.find(
    (source) => source.id === preview && source.type === "txt",
  );

  async function readFile(event) {
    const input = event.target;
    const file = input.files?.[0];

    input.value = "";

    if (!file || !selectedProject || busy.current) {
      return;
    }

    const projectId = String(selectedProject.id);

    setError("");

    if (!/\.txt$/i.test(file.name)) {
      setError("Pilih berkas dengan ekstensi .txt.");
      return;
    }

    if (!file.size) {
      setError("Berkas TXT tidak boleh kosong.");
      return;
    }

    const alreadyAdded = sources.some(
      (source) =>
        source.type === "txt" &&
        source.name === file.name &&
        source.size === file.size,
    );

    if (alreadyAdded) {
      setError("Berkas dengan nama dan ukuran yang sama sudah ditambahkan.");
      return;
    }

    busy.current = true;
    setReading(true);

    try {
      const buffer = await file.arrayBuffer();

      const content = new TextDecoder("utf-8", {
        fatal: true,
      }).decode(buffer);

      if (content.includes("\u0000")) {
        throw new Error(
          "Berkas mengandung data biner. Gunakan TXT dengan encoding UTF-8.",
        );
      }

      if (!content.trim()) {
        throw new Error("Berkas TXT tidak berisi teks.");
      }

      const id = sourceId();

      addSource(projectId, {
        id,
        type: "txt",
        name: file.name,
        size: file.size,
        content,
      });

      setPreview(id);
    } catch (err) {
      setError(
        err instanceof TypeError
          ? "Berkas harus berupa teks UTF-8 yang valid."
          : err.message || "Berkas tidak berhasil dibaca.",
      );
    } finally {
      busy.current = false;
      setReading(false);
    }
  }

  function addUrl(event) {
    event.preventDefault();
    setError("");

    if (!selectedProject) {
      return;
    }

    const input = url.trim();

    if (!input) {
      setError("Masukkan domain atau alamat halaman.");
      return;
    }

    try {
      const address = /^https?:\/\//i.test(input) ? input : `https://${input}`;

      const parsed = new URL(address);

      if (
        !["https:", "http:"].includes(parsed.protocol) ||
        parsed.username ||
        parsed.password ||
        !parsed.hostname.includes(".")
      ) {
        throw new Error("URL tidak valid.");
      }

      const alreadyAdded = sources.some(
        (source) => source.type === "url" && source.name === parsed.href,
      );

      if (alreadyAdded) {
        setError("URL ini sudah ada di daftar.");
        return;
      }

      const urlCount = sources.filter((source) => source.type === "url").length;

      if (urlCount >= 50) {
        setError("Maksimal 50 URL pratinjau per proyek.");
        return;
      }

      addSource(String(selectedProject.id), {
        id: sourceId(),
        type: "url",
        name: parsed.href,
        size: 0,
      });

      setUrl("");
    } catch {
      setError(
        "Masukkan domain atau URL HTTP/HTTPS yang valid tanpa username/password.",
      );
    }
  }

  function deleteSource(sourceIdToDelete) {
    if (!selectedProject) {
      return;
    }

    removeSource(String(selectedProject.id), sourceIdToDelete);

    if (preview === sourceIdToDelete) {
      setPreview("");
    }
  }

  return (
    <>
      <PageTitle
        title="Datasets"
        description="Siapkan sumber teks dan URL untuk proyek yang dipilih."
        action={<Badge tone="warning">Pratinjau lokal</Badge>}
      />

      <Notice>
        TXT dibaca di memori tab ini; URL hanya dicatat, belum diambil isinya.
        Data belum diunggah ke Drive dan hilang saat halaman dimuat ulang.
        Simpan berkas aslinya sebagai cadangan.
      </Notice>

      {!selectedProject ? (
        <section className="cth-card">
          <Empty icon="datasets" title="Pilih proyek terlebih dahulu">
            Buat atau pilih proyek melalui Google Drive.
          </Empty>

          <button
            type="button"
            className="cth-button primary"
            onClick={() => onNavigate("drive")}
          >
            Buka Google Drive
          </button>
        </section>
      ) : (
        <>
          <div className="cth-grid two cth-section-gap">
            <section className="cth-card">
              <h2>Masukkan TXT</h2>

              <p className="cth-muted">Proyek: {selectedProject.name}</p>

              <label className="cth-upload">
                <strong>
                  {reading ? "Membaca berkas..." : "Pilih berkas TXT"}
                </strong>

                <span>Berkas TXT dengan encoding UTF-8</span>

                <input
                  type="file"
                  accept=".txt,text/plain"
                  disabled={reading}
                  onChange={readFile}
                />
              </label>

              <p className="cth-muted">
                Tidak ada batas ukuran dari halaman ini. Berkas besar
                membutuhkan lebih banyak RAM.
              </p>
            </section>

            <section className="cth-card">
              <h2>Tambahkan URL</h2>

              <p className="cth-muted">
                Daftarkan sumber untuk integrasi pengambilan data berikutnya.
              </p>

              <form className="cth-form" onSubmit={addUrl}>
                <label>
                  Domain atau alamat halaman
                  <input
                    type="text"
                    value={url}
                    onChange={(event) => setUrl(event.target.value)}
                    maxLength={2048}
                    placeholder="example.com atau https://example.id/artikel"
                    required
                  />
                </label>

                <button className="cth-button" type="submit">
                  Tambahkan ke daftar
                </button>
              </form>
            </section>
          </div>

          {error && <Notice tone="error">{error}</Notice>}

          <div className="cth-grid two cth-section-gap">
            <section className="cth-card">
              <div className="cth-card-heading">
                <h2>Sumber proyek</h2>

                <Badge>{sources.length} sumber lokal</Badge>
              </div>

              {!sources.length ? (
                <Empty icon="datasets" title="Belum ada sumber" />
              ) : (
                <div className="cth-source-list">
                  {sources.map((source) => (
                    <article key={source.id}>
                      <div>
                        <Badge>{source.type.toUpperCase()}</Badge>

                        <strong>{source.name}</strong>

                        <small>
                          {source.type === "txt"
                            ? `${formatSize(source.size)} · hanya memori tab`
                            : "Isi URL belum diambil"}
                        </small>
                      </div>

                      <div className="cth-actions">
                        {source.type === "txt" && (
                          <button
                            type="button"
                            className="cth-text-button"
                            onClick={() => setPreview(source.id)}
                          >
                            Lihat
                          </button>
                        )}

                        <button
                          type="button"
                          className="cth-text-button danger"
                          onClick={() => deleteSource(source.id)}
                        >
                          Hapus
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>

            <section className="cth-card">
              <h2>Pratinjau teks</h2>

              {previewSource ? (
                <>
                  <p className="cth-muted">
                    {previewSource.name} · maksimal 12.000 karakter ditampilkan
                  </p>

                  <pre className="cth-text-preview">
                    {previewSource.content.slice(0, 12000)}
                  </pre>
                </>
              ) : (
                <Empty icon="datasets" title="Pilih TXT untuk dibaca" />
              )}
            </section>
          </div>
        </>
      )}
    </>
  );
}
