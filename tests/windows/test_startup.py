"""Windows launcher regressions using real Python, Node and Vite processes.

Run after npm ci in frontend: python -m unittest discover -s tests/windows -v
"""
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(os.name == 'nt', 'Windows PowerShell startup script')
class TestWindowsStartup(unittest.TestCase):
    def setUp(self):
        for port in (8000, 3000):
            with socket.socket() as probe:
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                try:
                    probe.bind(('127.0.0.1', port))
                except OSError:
                    self.skipTest(f'Port {port} is in use by another application')
        self.assertTrue((ROOT / 'frontend/node_modules/vite/bin/vite.js').is_file(),
                        'Run npm ci in frontend before Windows startup tests')
        self.temp = tempfile.TemporaryDirectory(prefix='lms startup space ')
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        shutil.copy2(ROOT / 'start.ps1', self.project / 'start.ps1')
        for directory in ('backend', 'database', 'frontend'):
            shutil.copytree(ROOT / directory, self.project / directory,
                            ignore=shutil.ignore_patterns('node_modules', '__pycache__',
                                                          '*.db*', 'dist', 'backups', '.env*'))
        # Junctions need no developer-mode/symlink privilege. Remove the junction
        # itself before cleaning the fixture, never the real dependency directory.
        self.modules = self.project / 'frontend/node_modules'
        subprocess.run(['cmd.exe', '/c', 'mklink', '/J', str(self.modules),
                        str(ROOT / 'frontend/node_modules')], check=True, capture_output=True)
        self.addCleanup(lambda: os.rmdir(self.modules) if self.modules.exists() else None)
        self.process = None
        self.log_path = self.project / 'launcher.log'
        self.log = self.log_path.open('wb')
        self.addCleanup(self.log.close)
        self.addCleanup(self.stop_launcher)
        self.env = os.environ.copy()
        self.env['PYTHON'] = sys.executable
        self.env['LMS_DB_PATH'] = str(self.project / 'test.db')
        # The local-pair launcher must not inherit unrelated endpoint overrides.
        self.env['LMS_HOST'] = '192.0.2.1'
        self.env['VITE_API_BASE_URL'] = 'http://192.0.2.1/api'

    def launch(self, skip_install=True):
        command = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                   '-File', str(self.project / 'start.ps1'), '-NoBrowser']
        if skip_install:
            command.append('-SkipInstall')
        self.process = subprocess.Popen(command, cwd=self.temp.name, env=self.env,
                                        stdin=subprocess.PIPE, stdout=self.log,
                                        stderr=subprocess.STDOUT, text=True)
        return self.process

    def output(self):
        return self.log_path.read_text(encoding='utf-8', errors='replace')

    def stop_launcher(self):
        if self.process is None:
            return
        if self.process.poll() is None:
            try:
                self.process.communicate('\n', timeout=12)
            except subprocess.TimeoutExpired:
                subprocess.run(['taskkill.exe', '/PID', str(self.process.pid), '/T', '/F'],
                               capture_output=True)
                self.process.wait(timeout=10)
        if self.process.stdin and not self.process.stdin.closed:
            self.process.stdin.close()

    def wait_ready(self):
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            output = self.output()
            if 'Startup successful!' in output:
                return
            if self.process.poll() is not None:
                self.fail(f'Launcher exited before readiness:\n{output}')
            time.sleep(0.1)
        self.fail(f'Launcher never became ready:\n{self.output()}')

    def assert_ports_free(self):
        for port in (8000, 3000):
            with socket.socket() as probe:
                self.assertNotEqual(probe.connect_ex(('127.0.0.1', port)), 0,
                                    f'Launcher left port {port} listening')

    def assert_owned_processes_stopped(self):
        for pid in re.findall(r'(?:Backend|Frontend) PID: (\d+)', self.output()):
            result = subprocess.run(['tasklist.exe', '/FI', f'PID eq {pid}', '/FO', 'CSV', '/NH'],
                                    capture_output=True, text=True, check=True)
            self.assertNotIn(f'"{pid}"', result.stdout, f'Owned process {pid} survived cleanup')

    def test_real_stack_starts_from_path_with_spaces_and_stops_on_enter(self):
        self.launch()
        self.wait_ready()
        with urlopen('http://127.0.0.1:3000/api/health', timeout=3) as response:
            self.assertEqual(json.load(response), {'status': 'ok', 'service': 'lms-backend'})
        with urlopen('http://127.0.0.1:3000', timeout=3) as response:
            self.assertIn(b'/src/main.tsx', response.read())
        self.assertTrue((self.project / 'test.db').is_file())
        self.process.communicate('\n', timeout=15)
        self.assertEqual(self.process.returncode, 0, self.output())
        self.assert_owned_processes_stopped()
        self.assert_ports_free()

    def assert_occupied_port_rejected(self, port):
        with socket.socket() as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            listener.bind(('127.0.0.1', port))
            listener.listen()
            self.launch()
            self.process.communicate('\n', timeout=12)
            self.assertNotEqual(self.process.returncode, 0, self.output())
            self.assertIn(f'Port {port} is already in use', self.output())
            self.assertNotIn('Startup successful!', self.output())
            self.assertNotIn('Backend PID:', self.output())
            self.assertFalse((self.project / 'test.db').exists())
            # The unrelated listener must still be running.
            with socket.create_connection(('127.0.0.1', port), timeout=2):
                pass

    def test_occupied_backend_port_is_rejected_without_starting_servers(self):
        self.assert_occupied_port_rejected(8000)

    def test_occupied_frontend_port_is_rejected_without_starting_servers(self):
        self.assert_occupied_port_rejected(3000)

    def test_backend_failure_is_reported_and_cleaned_up(self):
        self.env['LMS_DB_PATH'] = str(self.project / 'missing-parent/test.db')
        self.launch()
        self.process.communicate('\n', timeout=15)
        self.assertNotEqual(self.process.returncode, 0, self.output())
        self.assertIn('Backend exited during startup', self.output())
        self.assertNotIn('Frontend PID:', self.output())
        self.assert_owned_processes_stopped()
        self.assert_ports_free()

    def test_frontend_failure_also_stops_backend(self):
        (self.project / 'frontend/vite.config.ts').write_text(
            "throw new Error('Deliberate startup failure');\nexport default {};\n",
            encoding='utf-8')
        self.launch()
        self.process.communicate('\n', timeout=15)
        self.assertNotEqual(self.process.returncode, 0, self.output())
        self.assertIn('Frontend exited during startup', self.output())
        self.assertNotIn('Startup successful!', self.output())
        self.assert_owned_processes_stopped()
        self.assert_ports_free()

    def test_http_200_with_wrong_health_payload_is_not_ready(self):
        (self.project / 'backend/server.py').write_text(
            'from http.server import BaseHTTPRequestHandler, HTTPServer\n'
            'class Handler(BaseHTTPRequestHandler):\n'
            '    def do_GET(self):\n'
            '        self.send_response(200)\n'
            '        self.end_headers()\n'
            '        self.wfile.write(b\'{"status":"ok","service":"another-app"}\')\n'
            'HTTPServer(("127.0.0.1", 8000), Handler).serve_forever()\n',
            encoding='utf-8')
        self.launch()
        self.process.communicate('\n', timeout=40)
        self.assertNotEqual(self.process.returncode, 0, self.output())
        self.assertIn('Backend did not become ready', self.output())
        self.assertNotIn('Frontend PID:', self.output())
        self.assertNotIn('Startup successful!', self.output())
        self.assert_owned_processes_stopped()
        self.assert_ports_free()

    def test_dependency_install_failure_starts_no_servers(self):
        fake_bin = self.project / 'fake tools'
        fake_bin.mkdir()
        (fake_bin / 'npm.cmd').write_text('@echo off\r\nexit /b 7\r\n', encoding='ascii')
        self.env['PATH'] = str(fake_bin) + os.pathsep + self.env['PATH']
        self.launch(skip_install=False)
        self.process.communicate('\n', timeout=12)
        self.assertNotEqual(self.process.returncode, 0, self.output())
        self.assertIn('npm ci failed', self.output())
        self.assertNotIn('Backend PID:', self.output())
        self.assertFalse((self.project / 'test.db').exists())
        self.assert_ports_free()


if __name__ == '__main__':
    unittest.main()
