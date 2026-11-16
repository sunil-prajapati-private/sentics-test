import { StrictMode, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type Robot = { robot_id: string; cell_id: string; stations: string; enrollment_state: string; state: string; online?: boolean; state_reason?: string | null; last_seen?: string | null };
type Job = { job_id: string; robot_id: string; source_station: string; destination_station: string; status: string; reason?: string | null };

const api = (path: string, options?: RequestInit) => fetch(path, { ...options, credentials: "same-origin" }).then(async (response) => {
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`);
  return body;
});

function App() {
  const [authenticated, setAuthenticated] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [robots, setRobots] = useState<Robot[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [robotId, setRobotId] = useState("robot-1");
  const [source, setSource] = useState("A");
  const [destination, setDestination] = useState("B");
  const [failureMode, setFailureMode] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => { api("/auth/me").then(() => setAuthenticated(true)).catch(() => setAuthenticated(false)); }, []);

  const refresh = () => Promise.all([api("/api/robots"), api("/api/jobs")]).then(([robotData, jobData]) => {
    setRobots(Array.isArray(robotData) ? robotData : []);
    setJobs(Array.isArray(jobData) ? jobData : []);
  }).catch((error: Error) => setMessage(error.message));

  useEffect(() => {
    if (!authenticated) return;
    refresh();
    const stream = new EventSource("/api/events");
    stream.onmessage = () => refresh();
    stream.onerror = () => stream.close();
    return () => stream.close();
  }, [authenticated]);

  const login = (event: FormEvent) => {
    event.preventDefault();
    setLoginError("");
    api("/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username, password }) })
      .then(() => setAuthenticated(true)).catch((error: Error) => setLoginError(error.message));
  };

  if (!authenticated) return <main><section className="panel login"><p className="eyebrow">REMOTE ROBOT CELL</p><h1>Operator login</h1><p className="muted">Use an active seeded operator account.</p><form onSubmit={login}><label>Username<input value={username} onChange={(event) => setUsername(event.target.value)} /></label><label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label><button className="primary" type="submit">Sign in</button></form>{loginError && <p className="notice">{loginError}</p>}</section></main>;

  const selectedRobot = robots.find((robot) => robot.robot_id === robotId);
  const stations = selectedRobot?.stations.split(",") ?? (robotId === "robot-1" ? ["A", "B", "C"] : ["C", "D", "E"]);

  const submitJob = (event: FormEvent) => {
    event.preventDefault();
    setMessage("Submitting job…");
    api("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ robot_id: robotId, source_station: source, destination_station: destination, ...(failureMode ? { failure_mode: failureMode } : {}) }),
    }).then((job: Job) => {
      setMessage(`Created ${job.job_id}`);
      return refresh();
    }).catch((error: Error) => setMessage(error.message));
  };

  const safety = (cellId: string, event: string) => {
    api("/api/safety/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cell_id: cellId, event }),
    }).then(() => setMessage(`${cellId}: ${event} requested`)).catch((error: Error) => setMessage(error.message));
  };

  const cancel = (jobId: string) => api(`/api/jobs/${jobId}`, { method: "DELETE" }).then(() => refresh()).catch((error: Error) => setMessage(error.message));

  return <main>
    <header><div><p className="eyebrow">REMOTE ROBOT CELL</p><h1>Operations console</h1><p className="muted">Cloud projections with on-prem safety authority.</p></div><span><button onClick={refresh}>Refresh</button><button onClick={() => api("/auth/logout", { method: "POST" }).then(() => setAuthenticated(false))}>Sign out</button></span></header>
    <section className="grid">
      <article className="panel"><h2>Submit a job</h2><form onSubmit={submitJob}>
        <label>Robot<select value={robotId} onChange={(event) => { setRobotId(event.target.value); setSource(event.target.value === "robot-1" ? "A" : "C"); setDestination(event.target.value === "robot-1" ? "B" : "D"); }}>{robots.length ? robots.map((robot) => <option key={robot.robot_id} value={robot.robot_id}>{robot.robot_id} · {robot.cell_id}</option>) : <><option>robot-1</option><option>robot-2</option></>}</select></label>
        <div className="row"><label>From<select value={source} onChange={(event) => setSource(event.target.value)}>{stations.map((station) => <option key={station}>{station}</option>)}</select></label><label>To<select value={destination} onChange={(event) => setDestination(event.target.value)}>{stations.map((station) => <option key={station}>{station}</option>)}</select></label></div>
        <label>Failure simulation<select value={failureMode} onChange={(event) => setFailureMode(event.target.value)}><option value="">None</option><option value="always_fail">Always fail</option><option value="timeout">Timeout then retry</option></select></label>
        <button className="primary" type="submit">Submit job</button>
      </form>{message && <p className="notice">{message}</p>}</article>
      <article className="panel"><h2>Cell safety</h2>{["cell-1", "cell-2"].map((cell) => <div className="safety" key={cell}><strong>{cell}</strong><span><button onClick={() => safety(cell, "person_entered")}>Person entered</button><button onClick={() => safety(cell, "person_left")}>Person left</button></span></div>)}<p className="muted small">Safety actions are sent to the on-prem service; cloud status is a projection.</p></article>
    </section>
    <section className="panel"><div className="section-title"><h2>Jobs</h2><span className="badge">{jobs.length}</span></div><div className="jobs">{jobs.length === 0 ? <p className="muted">No jobs submitted.</p> : jobs.map((job) => <div className="job" key={job.job_id}><div><strong>{job.robot_id}</strong><span>{job.source_station} → {job.destination_station}</span></div><div><div className={`status ${job.status}`}>{job.status}</div>{job.status === "queued" && <button onClick={() => cancel(job.job_id)}>Cancel</button>}</div>{job.reason && <small>{job.reason}</small>}</div>)}</div></section>
    <section className="panel"><h2>Robots</h2><div className="robot-grid">{robots.length === 0 ? <p className="muted">Waiting for enrollment events…</p> : robots.map((robot) => <div className="robot" key={robot.robot_id}><strong>{robot.robot_id}</strong><span>{robot.cell_id} · {robot.online ? "online" : "offline"}</span><small>State: {robot.state}{robot.state_reason ? ` · ${robot.state_reason}` : ""}</small><small>Stations: {robot.stations}</small><small>Enrollment: {robot.enrollment_state}</small></div>)}</div></section>
  </main>;
}

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
