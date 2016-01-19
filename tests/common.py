import contextlib
from subprocess import list2cmdline
from StringIO import StringIO
from rrmngmnt.executor import Executor


class FakeFile(StringIO):
    def __init__(self, *args, **kwargs):
        StringIO.__init__(self, *args, **kwargs)
        self.data = None

    def __exit__(self, *args):
        self.close()

    def __enter__(self):
        return self

    def close(self):
        self.seek(0)
        self.data = self.read()
        StringIO.close(self)


class FakeExecutor(Executor):
    cmd_to_data = None
    files_content = {}

    class Session(Executor.Session):
        def __init__(self, executor, timeout=None, use_pkey=False):
            super(FakeExecutor.Session, self).__init__(executor)
            self._timeout = timeout

        def open(self):
            pass

        def get_data(self, cmd):
            cmd = list2cmdline(cmd)
            try:
                return self._executor.cmd_to_data[cmd]
            except KeyError:
                raise Exception("There are no data for '%s'" % cmd)

        def get_file_data(self, name):
            try:
                data = self._executor.files_content[name]
            except KeyError:
                raise Exception("There is not such file %s" % name)
            if isinstance(data, FakeFile):
                data = data.data
            return data

        def command(self, cmd):
            return FakeExecutor.Command(cmd, self)

        def run_cmd(self, cmd, input_=None, timeout=None):
            cmd = self.command(cmd)
            return cmd.run(input_, timeout)

        def open_file(self, name, mode):
            try:
                data = self.get_file_data(name)
            except Exception:
                if mode[0] not in ('w', 'a'):
                    raise
                else:
                    data = ''
            data = FakeFile(data)
            if mode[0] == 'w':
                data.seek(0)
            self._executor.files_content[name] = data
            return data

    class Command(Executor.Command):

        def get_rc(self):
            return self._rc

        def run(self, input_, timeout=None):
            with self.execute() as (in_, out, err):
                if input_:
                    in_.write(input_)
                self.out = out.read()
                self.err = err.read()
            return self.rc, self.out, self.err

        @contextlib.contextmanager
        def execute(self, bufsize=-1, timeout=None):
            rc, out, err = self._ss.get_data(self.cmd)
            yield StringIO(), StringIO(out), StringIO(err)
            self._rc = rc

    def session(self, timeout=None):
        return FakeExecutor.Session(self, timeout)

    def run_cmd(self, cmd, input_=None, tcp_timeout=None, io_timeout=None):
        with self.session(tcp_timeout) as session:
            return session.run_cmd(cmd, input_, io_timeout)


if __name__ == "__main__":
    from rrmngmnt import RootUser
    u = RootUser('password')
    e = FakeExecutor(u)
    e.cmd_to_data = {'echo ahoj': (0, 'ahoj', '')}
    print e.run_cmd(['echo', 'ahoj'])
    with e.session() as ss:
        with ss.open_file('/tmp/a', 'w') as fh:
            fh.write("ahoj")
    print e.files_content['/tmp/a'], e.files_content['/tmp/a'].data
