import http.server
import socketserver
import webbrowser
import json
import sys
import os
from pathlib import Path
from urllib.parse import urlparse
import threading
import time
from queue import Queue
from collections import OrderedDict

# 导入配置管理器
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))
try:
    from config_manager import ConfigManager
    from sync_metadata import sync_single_kb
except ImportError:
    # 如果单独运行，可能需要调整路径
    sys.path.append(str(script_dir.parent))
    from scripts.config_manager import ConfigManager
    from scripts.sync_metadata import sync_single_kb

# 全局任务队列管理器
class DescriptionTaskQueue:
    """管理自动生成描述的并发任务队列"""

    def __init__(self, max_concurrent=2, task_timeout=15):
        self.max_concurrent = max_concurrent
        self.task_timeout = task_timeout
        self.task_queue = Queue()
        self.active_tasks = {}  # {kb_name: {'status': 'generating', 'start_time': ...}}
        self.task_results = {}  # {kb_name: {'status': 'success|failed', 'description': ...}}
        self.lock = threading.Lock()
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def queue_task(self, kb_data):
        """将自动生成描述任务加入队列"""
        kb_name = kb_data['name']
        with self.lock:
            # 检查是否已有同名任务
            if kb_name in self.active_tasks or kb_name in self.task_results:
                return {'status': 'duplicate', 'kb_name': kb_name}

            # 添加到队列
            self.task_queue.put(kb_data)
            self.task_results[kb_name] = {'status': 'pending', 'description': '-auto'}
            return {'status': 'queued', 'kb_name': kb_name}

    def get_task_status(self, kb_name):
        """获取任务状态"""
        with self.lock:
            if kb_name in self.active_tasks:
                return {
                    'status': 'generating',
                    'description': self.active_tasks[kb_name].get('description', '-auto'),
                    'elapsed': time.time() - self.active_tasks[kb_name]['start_time']
                }
            elif kb_name in self.task_results:
                return {
                    'status': self.task_results[kb_name]['status'],
                    'description': self.task_results[kb_name].get('description', '-auto')
                }
            else:
                return {'status': 'unknown', 'description': ''}

    def _worker_loop(self):
        """后台工作线程处理任务队列"""
        while True:
            # 检查是否可以启动新任务（并发数限制）
            with self.lock:
                if len(self.active_tasks) < self.max_concurrent and not self.task_queue.empty():
                    kb_data = self.task_queue.get()
                    kb_name = kb_data['name']
                    self.active_tasks[kb_name] = {
                        'start_time': time.time(),
                        'description': '-auto'
                    }

            # 处理活跃任务
            with self.lock:
                expired_tasks = []
                for kb_name, task_info in list(self.active_tasks.items()):
                    elapsed = time.time() - task_info['start_time']

                    # 检查超时
                    if elapsed > self.task_timeout:
                        expired_tasks.append(kb_name)
                        self.task_results[kb_name] = {
                            'status': 'failed',
                            'description': '-auto-timeout',
                            'reason': 'generation_timeout'
                        }

                # 移除超时任务
                for kb_name in expired_tasks:
                    del self.active_tasks[kb_name]

            # 如果有可用的处理槽，处理下一个任务
            with self.lock:
                if len(self.active_tasks) < self.max_concurrent and not self.task_queue.empty():
                    kb_data = self.task_queue.get()
                    kb_name = kb_data['name']
                    self.active_tasks[kb_name] = {
                        'start_time': time.time(),
                        'description': '-auto'
                    }

                    # 执行生成任务（在锁外进行以避免阻塞）
                    def execute_generation():
                        try:
                            cm = ConfigManager()
                            result = sync_single_kb(
                                cm,
                                kb_name,
                                use_recall=False,
                                query_rounds=3,
                                dry_run=False,
                                verbose=False
                            )

                            with self.lock:
                                if kb_name in self.active_tasks:
                                    del self.active_tasks[kb_name]

                                if result.get('success') and result.get('description'):
                                    self.task_results[kb_name] = {
                                        'status': 'success',
                                        'description': result['description']
                                    }
                                else:
                                    self.task_results[kb_name] = {
                                        'status': 'failed',
                                        'description': '-auto-failed',
                                        'reason': 'generation_error'
                                    }
                        except Exception as e:
                            with self.lock:
                                if kb_name in self.active_tasks:
                                    del self.active_tasks[kb_name]
                                self.task_results[kb_name] = {
                                    'status': 'failed',
                                    'description': '-auto-error',
                                    'reason': str(e)
                                }

                    # 在新线程中执行生成任务
                    gen_thread = threading.Thread(target=execute_generation, daemon=True)
                    gen_thread.start()

            # 延迟避免忙轮询
            time.sleep(0.1)


# 创建全局队列管理器实例
task_queue_manager = DescriptionTaskQueue(max_concurrent=2, task_timeout=15)


# 心跳监控管理器
class HeartbeatMonitor:
    """监控客户端心跳，如果无心跳则自动退出"""

    def __init__(self, grace_period=12, timeout=5):
        """
        Args:
            grace_period: 启动宽限期（秒），给予浏览器打开时间
            timeout: 无心跳超时时间（秒），超过则自动退出
        """
        self.grace_period = grace_period
        self.timeout = timeout
        self.last_heartbeat = time.time()
        self.startup_time = time.time()
        self.lock = threading.Lock()

    def record_heartbeat(self):
        """记录心跳"""
        with self.lock:
            self.last_heartbeat = time.time()

    def check_and_exit(self):
        """检查是否应该退出"""
        with self.lock:
            elapsed_startup = time.time() - self.startup_time
            # 如果还在启动宽限期内，不检查心跳
            if elapsed_startup < self.grace_period:
                return False

            # 检查心跳超时
            elapsed_since_heartbeat = time.time() - self.last_heartbeat
            if elapsed_since_heartbeat > self.timeout:
                print(f"\n⏱️ 检测到客户端断开连接（{elapsed_since_heartbeat:.1f}s无心跳），正在停止服务...")
                return True
        return False


# 创建全局心跳监控器实例
heartbeat_monitor = HeartbeatMonitor(grace_period=12, timeout=5)


HTML_CONTENT = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Get笔记配置管理</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f5f5f7; }
        .container { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h1 { margin-top: 0; color: #1d1d1f; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; font-weight: 500; color: #1d1d1f; }
        input[type="text"], textarea { width: 100%; padding: 10px; border: 1px solid #d2d2d7; border-radius: 6px; font-size: 16px; box-sizing: border-box; }
        textarea { height: 80px; resize: vertical; }
        .checkbox-group { display: flex; align-items: center; }
        .checkbox-group input { margin-right: 10px; width: 18px; height: 18px; }
        button { background-color: #0071e3; color: white; border: none; padding: 10px 20px; border-radius: 6px; font-size: 16px; cursor: pointer; transition: background 0.2s; }
        button:hover { background-color: #0077ed; }
        .kb-list { margin-top: 40px; border-top: 1px solid #e5e5e5; padding-top: 20px; }
        .kb-item { background: #fbfbfd; border: 1px solid #e5e5e5; padding: 15px; border-radius: 8px; margin-bottom: 10px; display: flex; flex-direction: column; }
        .kb-info { width: 100%; margin-bottom: 12px; }
        .kb-name { font-weight: 600; font-size: 18px; color: #1d1d1f; }
        .kb-desc { color: #86868b; font-size: 14px; margin-top: 4px; }
        .kb-actions { display: flex; gap: 10px; align-self: flex-end; }
        .tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }
        .tag-default { background: #e8f2ff; color: #0071e3; }
        .btn-small { padding: 6px 12px; font-size: 14px; background-color: #f5f5f7; color: #1d1d1f; border: 1px solid #d2d2d7; }
        .btn-small:hover { background-color: #e5e5e5; }
        #message { margin-top: 20px; padding: 10px; border-radius: 6px; display: none; }
        .success { background-color: #e8fcf1; color: #0f6b36; }
        .error { background-color: #fce8e8; color: #c92a2a; }
    </style>
</head>
<body>
    <div class="container">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h1 style="margin: 0;">配置知识库</h1>
            <button type="button" id="stopBtn" style="background-color: #ef4444; padding: 8px 16px; font-size: 14px;">停止服务</button>
        </div>
        <form id="configForm">
            <div class="form-group">
                <label for="name">知识库名称 (唯一标识)</label>
                <input type="text" id="name" name="name" required placeholder="例如: my-notes">
            </div>
            <div class="form-group">
                <label for="api_key">API Key</label>
                <input type="text" id="api_key" name="api_key" required placeholder="Get笔记 API Key">
            </div>
            <div class="form-group">
                <label for="topic_id">Topic ID</label>
                <input type="text" id="topic_id" name="topic_id" required placeholder="知识库 ID">
            </div>
            <div class="form-group">
                <label for="description">描述 (用于语义路由)</label>
                <textarea id="description" name="description" placeholder="该库主要涵盖...，核心关键词包括...，适用于...&#10;auto: Skill 帮你根据知识库内容自动生成全面的描述&#10;不填写就是忽略，后面可以增加"></textarea>
            </div>
            <div class="form-group checkbox-group">
                <input type="checkbox" id="set_default" name="set_default">
                <label for="set_default" style="margin-bottom: 0;">设为默认知识库</label>
            </div>
            <button type="submit">保存配置</button>
        </form>
        <div id="message"></div>

        <div class="kb-list">
            <h2>现有知识库</h2>
            <div id="kbList">加载中...</div>
        </div>
    </div>

    <script>
        const form = document.getElementById('configForm');
        const messageDiv = document.getElementById('message');
        const kbListDiv = document.getElementById('kbList');
        const stopBtn = document.getElementById('stopBtn');

        // 启动心跳（每2秒发送一次）
        setInterval(async () => {
            try {
                await fetch('/api/heartbeat', {method: 'GET'});
            } catch (e) {
                console.error('Heartbeat error:', e);
            }
        }, 2000);

        // 停止服务按钮
        stopBtn.addEventListener('click', async () => {
            if (confirm('确定要停止服务吗？')) {
                try {
                    await fetch('/api/shutdown', {method: 'POST'});
                    messageDiv.textContent = '服务已停止，请关闭此页面';
                    messageDiv.className = 'success';
                    messageDiv.style.display = 'block';
                    stopBtn.disabled = true;
                } catch (e) {
                    console.error('Shutdown error:', e);
                }
            }
        });

        function showMessage(text, type) {
            messageDiv.textContent = text;
            messageDiv.className = type;
            messageDiv.style.display = 'block';
            setTimeout(() => { messageDiv.style.display = 'none'; }, 3000);
        }

        async function loadKBs() {
            try {
                const response = await fetch('/api/list');
                const data = await response.json();
                renderKBs(data);
            } catch (e) {
                console.error(e);
            }
        }

        function renderKBs(data) {
            kbListDiv.innerHTML = '';
            if (data.kbs.length === 0) {
                kbListDiv.innerHTML = '<p style="color: #86868b;">暂无配置</p>';
                return;
            }

            data.kbs.forEach(kb => {
                const div = document.createElement('div');
                div.className = 'kb-item';
                div.id = `kb-${kb.name}`;
                const isDefault = kb.name === data.default_kb;

                // 检查描述状态
                let descStatus = '';
                let descClass = '';
                if (kb.description === '-auto' || kb.description === '-auto-generating') {
                    descStatus = ' <span style="color: #f59e0b;">⏳ 生成中...</span>';
                    descClass = ' style="color: #f59e0b;"';
                } else if (kb.description === '-auto-timeout' || kb.description === '-auto-failed' || kb.description === '-auto-error') {
                    descStatus = ' <span style="color: #ef4444;">⚠️ 生成失败</span>';
                    descClass = ' style="color: #ef4444;"';
                } else if (kb.description && !kb.description.startsWith('-auto')) {
                    descStatus = ' <span style="color: #10b981;">✅</span>';
                }

                let html = `
                    <div class="kb-info">
                        <div class="kb-name">
                            ${kb.name}
                            ${isDefault ? '<span class="tag tag-default">默认</span>' : ''}
                        </div>
                        <div class="kb-desc"${descClass}>${kb.description || '无描述'}${descStatus}</div>
                        <div style="font-size: 12px; color: #86868b; margin-top: 2px;">ID: ${kb.topic_id}</div>
                    </div>
                    <div class="kb-actions">
                        <button type="button" class="btn-small" onclick="editKB('${kb.name}')">编辑</button>
                        <button type="button" class="btn-small" onclick="updateDesc('${kb.name}')">更新描述</button>
                        ${!isDefault ? `<button type="button" class="btn-small" onclick="setDefault('${kb.name}')">设为默认</button>` : ''}
                    </div>
                `;
                div.innerHTML = html;
                kbListDiv.appendChild(div);
            });

            // Store data for editing
            window.kbsData = data.kbs;
        }

        async function updateDesc(name) {
            try {
                const response = await fetch('/api/update-desc', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name})
                });

                if (response.ok) {
                    const result = await response.json();
                    if (result.status === 'queued') {
                        showMessage('已加入生成队列，请稍候...', 'success');
                        // 轮询检查状态
                        let checkCount = 0;
                        const interval = setInterval(async () => {
                            const statusRes = await fetch(`/api/task-status?name=${name}`);
                            const statusData = await statusRes.json();

                            if (statusData.status === 'success' || statusData.status === 'failed') {
                                clearInterval(interval);
                                loadKBs();
                                if (statusData.status === 'success') {
                                    showMessage('描述已更新', 'success');
                                } else {
                                    showMessage('生成失败，请重试', 'error');
                                }
                            }

                            checkCount++;
                            if (checkCount > 150) { // 15秒超时
                                clearInterval(interval);
                            }
                        }, 100);
                    } else if (result.status === 'duplicate') {
                        showMessage('此知识库正在生成中，请稍候', 'error');
                    }
                } else {
                    showMessage('操作失败', 'error');
                }
            } catch (e) {
                showMessage('网络错误', 'error');
            }
        }

        function editKB(name) {
            const kb = window.kbsData.find(k => k.name === name);
            if (kb) {
                document.getElementById('name').value = kb.name;
                document.getElementById('api_key').value = kb.api_key;
                document.getElementById('topic_id').value = kb.topic_id;
                document.getElementById('description').value = kb.description;
                document.getElementById('set_default').checked = false;
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        }

        async function setDefault(name) {
            try {
                const response = await fetch('/api/set_default', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name})
                });
                if (response.ok) {
                    showMessage('已设为默认', 'success');
                    loadKBs();
                }
            } catch (e) {
                showMessage('操作失败', 'error');
            }
        }

        form.onsubmit = async (e) => {
            e.preventDefault();
            const formData = {
                name: document.getElementById('name').value,
                api_key: document.getElementById('api_key').value,
                topic_id: document.getElementById('topic_id').value,
                description: document.getElementById('description').value,
                set_default: document.getElementById('set_default').checked
            };

            try {
                const response = await fetch('/api/save', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(formData)
                });

                if (response.ok) {
                    showMessage('保存成功', 'success');
                    form.reset();
                    loadKBs();
                } else {
                    showMessage('保存失败', 'error');
                }
            } catch (e) {
                showMessage('网络错误', 'error');
            }
        };

        loadKBs();
    </script>
</body>
</html>
"""

class ConfigHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/api/save':
            self.handle_save()
        elif self.path == '/api/set_default':
            self.handle_set_default()
        elif self.path == '/api/update-desc':
            self.handle_update_desc()
        elif self.path == '/api/shutdown':
            self.handle_shutdown()
        else:
            self.send_error(404)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode('utf-8'))
        elif parsed.path == '/api/list':
            self.handle_list()
        elif parsed.path == '/api/task-status':
            self.handle_task_status(parsed)
        elif parsed.path == '/api/heartbeat':
            self.handle_heartbeat()
        else:
            self.send_error(404)

    def handle_list(self):
        cm = ConfigManager()
        data = {
            "kbs": cm.get_all_kbs(),
            "default_kb": cm.get_default()
        }
        self.send_json(data)

    def handle_save(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))

        cm = ConfigManager()

        # 检查描述字段是否为 "auto"
        description = data.get('description', '').strip().lower()
        if description == 'auto':
            # 保存为待生成状态，并加入任务队列
            final_description = '-auto'
            cm.add_knowledge_base(
                name=data['name'],
                api_key=data['api_key'],
                topic_id=data['topic_id'],
                description=final_description,
                set_default=data.get('set_default', False)
            )
            # 加入异步生成队列
            task_result = task_queue_manager.queue_task(data)
            self.send_json({
                "status": "ok",
                "description": final_description,
                "auto_generated": True,
                "queue_status": task_result
            })
        else:
            final_description = data.get('description', '')
            cm.add_knowledge_base(
                name=data['name'],
                api_key=data['api_key'],
                topic_id=data['topic_id'],
                description=final_description,
                set_default=data.get('set_default', False)
            )
            self.send_json({
                "status": "ok",
                "description": final_description,
                "auto_generated": False
            })

    def handle_set_default(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))

        cm = ConfigManager()
        success = cm.set_default(data['name'])
        if success:
            self.send_json({"status": "ok"})
        else:
            self.send_error(400, "KB not found")

    def handle_update_desc(self):
        """处理手动更新描述请求"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))

        kb_name = data.get('name')
        cm = ConfigManager()

        # 验证知识库是否存在
        kbs = cm.get_all_kbs()
        kb_exists = any(kb['name'] == kb_name for kb in kbs)
        if not kb_exists:
            self.send_json({"status": "error", "message": "KB not found"})
            return

        # 加入任务队列
        # 获取知识库的完整信息以便传递给任务队列
        kb_info = next((kb for kb in kbs if kb['name'] == kb_name), None)
        if kb_info:
            task_result = task_queue_manager.queue_task({
                'name': kb_name,
                'api_key': kb_info.get('api_key', ''),
                'topic_id': kb_info.get('topic_id', '')
            })
            self.send_json(task_result)
        else:
            self.send_json({"status": "error", "message": "KB data not found"})

    def handle_task_status(self, parsed):
        """处理任务状态查询"""
        from urllib.parse import parse_qs
        query_params = parse_qs(parsed.query)
        kb_name = query_params.get('name', [''])[0]

        if not kb_name:
            self.send_json({"status": "error", "message": "name parameter required"})
            return

        status = task_queue_manager.get_task_status(kb_name)

        # 如果生成成功，从配置中读取更新后的描述
        if status['status'] == 'success':
            cm = ConfigManager()
            kbs = cm.get_all_kbs()
            kb_info = next((kb for kb in kbs if kb['name'] == kb_name), None)
            if kb_info and kb_info.get('description'):
                status['description'] = kb_info['description']

        self.send_json(status)

    def handle_heartbeat(self):
        """处理心跳请求"""
        heartbeat_monitor.record_heartbeat()
        self.send_json({"status": "ok"})

    def handle_shutdown(self):
        """处理服务关闭请求"""
        self.send_json({"status": "shutdown"})
        # 延迟一小段时间确保响应被发送
        threading.Timer(0.1, lambda: sys.exit(0)).start()

    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

def run_server():
    # 查找可用端口
    with socketserver.TCPServer(("localhost", 0), ConfigHandler) as httpd:
        port = httpd.server_address[1]
        url = f"http://localhost:{port}"
        print(f"✅ Web 配置服务已启动: {url}")
        print("🌍 正在打开浏览器...")
        print("ℹ️  关闭浏览器标签页后，服务将在 5 秒内自动停止")
        print("   或点击页面右上角的'停止服务'按钮手动停止")

        webbrowser.open(url)

        # 启动心跳监控线程
        def heartbeat_monitor_thread():
            while True:
                time.sleep(1)
                if heartbeat_monitor.check_and_exit():
                    sys.exit(0)

        monitor_thread = threading.Thread(target=heartbeat_monitor_thread, daemon=True)
        monitor_thread.start()

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 服务已停止")

if __name__ == "__main__":
    run_server()