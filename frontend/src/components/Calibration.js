import React, { useState } from 'react';

function Calibration() {
  const [focal, setFocal] = useState('600');
  const [status, setStatus] = useState(null);

  async function submit(e) {
    e.preventDefault();
    setStatus('Saving...');
    try {
      const res = await fetch('/api/calibrate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ focal_length: Number(focal) })
      });
      const data = await res.json();
      if (res.ok) setStatus(`Saved focal length: ${data.focal_length}`);
      else setStatus(`Error: ${data.error}`);
    } catch (err) {
      setStatus(`Network error: ${err.message}`);
    }
  }

  return (
    <div style={{padding:20}}>
      <h2>Camera Calibration</h2>
      <p>Enter approximate focal length (in pixels). Typical phones: 400–800.</p>
      <form onSubmit={submit}>
        <label>
          Focal length:
          <input type="number" value={focal} onChange={e => setFocal(e.target.value)} style={{marginLeft:8}} />
        </label>
        <button style={{marginLeft:12}}>Save</button>
      </form>
      {status && <p>{status}</p>}
    </div>
  );
}

export default Calibration;
