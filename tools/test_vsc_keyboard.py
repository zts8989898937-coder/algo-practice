"""PTY regressions for the installed VS Code keyboard runner."""
import os
import pathlib
import pty
import select
import subprocess
import tempfile
import time
import unittest

RUNNER = os.environ.get('VSC_RUNNER', '/usr/local/bin/vsc-run')


class KeyboardRun(unittest.TestCase):
    def run_keyboard(self, code, chunks, expected, suffix='py'):
        with tempfile.TemporaryDirectory(prefix='vsc-keyboard-') as tmp:
            source = pathlib.Path(tmp) / ('probe.' + suffix)
            source.write_text(code)
            master, slave = pty.openpty()
            process = subprocess.Popen([RUNNER, 'kbd', str(source)], stdin=slave,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            os.close(slave)
            output = b''
            try:
                for data in chunks:
                    os.write(master, data)
                deadline = time.monotonic() + 4
                while time.monotonic() < deadline:
                    if select.select([process.stdout], [], [], .05)[0]:
                        chunk = os.read(process.stdout.fileno(), 8192)
                        if not chunk:
                            break
                        output += chunk
                        if expected in output:
                            break
                self.assertIn(expected, output, 'program did not receive keyboard input immediately')
                self.assertEqual(process.wait(timeout=3), 0)
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=3)
                process.stdout.close()
                os.close(master)

    def test_single_line_runs_on_enter_without_eof(self):
        self.run_keyboard('print("RESULT=" + input(), flush=True)\n',
                          [b'ABC349\n'], b'RESULT=ABC349')

    def test_multiple_lines_are_received_by_program(self):
        self.run_keyboard('a=input(); b=input(); print("SUM="+str(int(a)+int(b)),flush=True)\n',
                          [b'20\n', b'22\n'], b'SUM=42')

    def test_end_is_ordinary_input(self):
        self.run_keyboard('print("RESULT=" + input(), flush=True)\n',
                          [b'END\n'], b'RESULT=END')

    def test_eof_program_still_supports_ctrl_d(self):
        self.run_keyboard('import sys\nprint("LINES="+str(len(sys.stdin.readlines())),flush=True)\n',
                          [b'one\ntwo\n', b'\x04'], b'LINES=2')

    def test_cpp_single_line_runs_on_enter(self):
        self.run_keyboard('#include <iostream>\n#include <string>\nint main(){std::string s;std::cin>>s;std::cout<<"RESULT="<<s<<"\\n";}\n',
                          [b'ABC349\n'], b'RESULT=ABC349', 'cpp')

    def test_cpp_multiple_tokens_across_lines(self):
        self.run_keyboard('#include <iostream>\nint main(){int n,x,sum=0;std::cin>>n;while(n--){std::cin>>x;sum+=x;}std::cout<<"SUM="<<sum<<"\\n";}\n',
                          [b'3\n', b'10 20 12\n'], b'SUM=42', 'cpp')


if __name__ == '__main__':
    unittest.main()
