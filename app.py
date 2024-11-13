import os
import signal
import subprocess

from flask import Flask, request, send_file, render_template, jsonify
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# 全局變量來保存爬蟲程式的物件
crawler_process = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    global crawler_process
    data = request.get_json()
    symbol_no = data.get('symbol_no')

    # 啟動爬蟲腳本作為副程式
    try:
        crawler_process = subprocess.Popen(['python', 'crawler.py', str(symbol_no)])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/stop', methods=['POST'])
def stop():
    global crawler_process
    if crawler_process and crawler_process.poll() is None:
        try:
            # 使用 SIGTERM 訊號中止爬蟲程式
            os.kill(crawler_process.pid, signal.SIGTERM)
            crawler_process = None
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    else:
        return jsonify({'success': False, 'error': '沒有運行中的爬蟲進程'})

# 重置系統，刪除 output.xlsx
@app.route('/download', methods=['GET'])
def download():
    try:
        return send_file('output.xlsx', as_attachment=True)
    except FileNotFoundError:
        return jsonify({'success': False, 'message': '資料檔案不存在'}), 404

@app.route('/reset', methods=['POST'])
def reset():
    output_path = 'output.xlsx'
    try:
        if os.path.exists(output_path):
            os.remove(output_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# WebSocket 事件：處理爬蟲狀態更新
@socketio.on('scrape_update')
@socketio.on('scrape_complete')
def handle_scrape_message(data):
    emit(request.event['message'], data, broadcast=True)

# 主程式入口
if __name__ == '__main__':
    # 啟動 Flask 伺服器，允許外部訪問，監聽 5000 埠
    # host='0.0.0.0' 允許從所有 IP 存取
    socketio.run(app, host='0.0.0.0', port=5000)
