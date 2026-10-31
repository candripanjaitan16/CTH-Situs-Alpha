function Icon({ name, className = "h-5 w-5" }) {
  const paths = {
    overview: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="1.5" />
        <rect x="14" y="3" width="7" height="7" rx="1.5" />
        <rect x="3" y="14" width="7" height="7" rx="1.5" />
        <rect x="14" y="14" width="7" height="7" rx="1.5" />
      </>
    ),
    datasets: (
      <>
        <ellipse cx="12" cy="5" rx="8" ry="3" />
        <path d="M4 5v7c0 1.7 3.6 3 8 3s8-1.3 8-3V5" />
        <path d="M4 12v7c0 1.7 3.6 3 8 3s8-1.3 8-3v-7" />
      </>
    ),
    training: (
      <>
        <rect x="3" y="4" width="18" height="13" rx="2" />
        <path d="M8 21h8M12 17v4m-2-13 5 3-5 3Z" />
      </>
    ),
    testing: (
      <>
        <path d="M9 3h6M10 3v6L4 19a1.3 1.3 0 0 0 1.2 2h13.6a1.3 1.3 0 0 0 1.2-2L14 9V3" />
        <path d="M8 14h8" />
      </>
    ),
    deployments: (
      <>
        <path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z" />
        <path d="m4 7.5 8 4.5 8-4.5M12 12v9m-4-16.5 8 4.5" />
      </>
    ),
    drive: (
      <path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-8l-2-3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z" />
    ),
    colab: <path d="m8 8-4 4 4 4m8-8 4 4-4 4m-3-11-2 14" />,
    model: (
      <>
        <rect x="6" y="6" width="12" height="12" rx="2" />
        <path d="M9 1v5m6-5v5M9 18v5m6-5v5M1 9h5m-5 6h5m12-6h5m-5 6h5" />
        <rect x="10" y="10" width="4" height="4" rx="0.5" />
      </>
    ),
    activity: <path d="M2 12h5l3-8 4 16 3-8h5" />,
    settings: (
      <>
        <path d="m9 3-.7 2.1-2 .9-2.1-.4-2 3.4 1.4 1.7v2.6L2.2 15l2 3.4 2.1-.4 2 .9L9 21h4l.7-2.1 2-.9 2.1.4 2-3.4-1.4-1.7v-2.6L19.8 9l-2-3.4-2.1.4-2-.9L13 3Z" />
        <circle cx="11" cy="12" r="3" />
      </>
    ),
    search: (
      <>
        <circle cx="10.5" cy="10.5" r="6.5" />
        <path d="m16 16 4 4" />
      </>
    ),
    check: <path d="m5 12 4 4L19 6" />,
    clock: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" />
      </>
    ),
  };

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {paths[name] ?? paths.overview}
    </svg>
  );
}


export default Icon;
