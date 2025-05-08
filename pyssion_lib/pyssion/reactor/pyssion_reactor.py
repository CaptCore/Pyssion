#!/usr/bin/env python3
# app.py

from flask import Flask, request, send_file, jsonify
import torch
import io
from collections import OrderedDict
import os

app = Flask(__name__)

# Global variables to store the sum of state_dicts and total sample count
_sum_state = None       # OrderedDict of tensors × sample count
_total_samples = 0      # int

@app.route('/health', methods=['GET'])
def health():
    """
    For Health Check 
    API : status / totlal_samples
    """
    return jsonify({
        'status': 'ok',
        'total_samples': _total_samples
    })

@app.route('/update', methods=['POST'])
def update():
    """
    Worker send state_dict to this server for aggregation.
    API : /update
    - multipart/form-data:
      - files['state']: torch.save()'s model.state_dict() binary data
      - form['n_samples']: (select) this worker's compute sample count, default=1
    """
    global _sum_state, _total_samples

    # 1) Request Check
    if 'state' not in request.files:
        return jsonify({'error': "Missing file field 'state'"}), 400

    # 2) static_dict Load
    buf = io.BytesIO(request.files['state'].read())
    worker_sd = torch.load(buf, map_location='cpu')

    # 3) Worker Sample Count
    n = int(request.form.get('n_samples', 1))

    # 4) Patameter Counter (weighted sum)
    if _sum_state is None:
        _sum_state = OrderedDict((k, v.float() * n) for k, v in worker_sd.items())
    else:
        for k, v in worker_sd.items():
            _sum_state[k] += v.float() * n

    _total_samples += n

    # 5) AVG compute
    avg_state = OrderedDict((k, _sum_state[k] / _total_samples) for k in _sum_state)

    # 6) AVG compute result serialize
    out = io.BytesIO()
    torch.save(avg_state, out)
    out.seek(0)
    return send_file(out, mimetype='application/octet-stream')

if __name__ == '__main__':
    # HOST, PORT can adjust environment variables
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    app.run(host=host, port=port)
